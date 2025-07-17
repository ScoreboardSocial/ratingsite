from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponseForbidden
from django.core.paginator import Paginator
from django.db.models import Avg, Count
from django.contrib.auth import login, get_user_model
from django.contrib import messages
from django.views.decorators.http import require_POST

from .models import Profile, Tag, Rating, Comment, FanFavoriteVote
from .forms import CustomUserCreationForm, CommentForm
from django.utils import timezone
from datetime import timedelta

import json
import random

User = get_user_model()


@require_POST
@csrf_exempt
def vote_fan_favorite(request, profile_id):
    profile = get_object_or_404(Profile, id=profile_id)

    session_key = request.session.session_key or request.session.save()
    already_voted = profile.fan_votes.filter(session_key=request.session.session_key).exists()
    if not already_voted:
        FanFavoriteVote.objects.create(session_key=request.session.session_key, profile=profile)

    return redirect('profile_detail', profile_id=profile.id)


def comment_edit(request, pk):
    return HttpResponseForbidden("Comment editing restricted to logged-in users.")


def comment_delete(request, pk):
    return HttpResponseForbidden("Comment deletion restricted to logged-in users.")


def signup(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Welcome, {user.username}! Your account was created successfully.")
            return redirect('profile_list')
    else:
        form = CustomUserCreationForm()
    return render(request, 'registration/signup.html', {'form': form})


def profile_list(request):
    sort = request.GET.get('sort', 'default')
    tag_id = request.GET.get('tag')
    query = request.GET.get('q', '')
    shuffle = request.GET.get('shuffle') == '1'

    profiles = Profile.objects.annotate(
        avg_rating=Avg('ratings__rating'),
        total_ratings=Count('ratings')
    )

    if tag_id:
        profiles = profiles.filter(tags__id=tag_id)
    if query:
        profiles = profiles.filter(name__icontains=query)

    if sort == 'rating':
        profiles = profiles.order_by('-avg_rating')
    elif sort == 'lowest':
        profiles = profiles.order_by('avg_rating')
    elif sort == 'new':
        profiles = profiles.order_by('-created_at')
    else:
        profiles = profiles.order_by('?') if shuffle else profiles.order_by('id')

    paginator = Paginator(profiles, 12)
    page_number = int(request.GET.get('page', 1))
    page_obj = paginator.get_page(page_number)

    # 🔹 Chunked Pagination Logic
    total_pages = paginator.num_pages
    pages_per_group = 20
    current_group = (page_number - 1) // pages_per_group
    start_page = current_group * pages_per_group + 1
    end_page = min(start_page + pages_per_group - 1, total_pages)
    page_range = range(start_page, end_page + 1)

    # Precompute Prev/Next Chunk Start Pages
    prev_chunk_page = (current_group - 1) * pages_per_group + 1 if current_group > 0 else None
    next_chunk_page = (current_group + 1) * pages_per_group + 1 if end_page < total_pages else None

    # Top 3 Rated Profiles for Leaderboard Snapshot
    top_rated = Profile.objects.annotate(avg_rating=Avg('ratings__rating')).order_by('-avg_rating')[:3]

    tags = Tag.objects.all()
    all_profiles = list(Profile.objects.annotate(avg_rating=Avg('ratings__rating')))
    featured_profile = random.choice(all_profiles) if all_profiles else None
    newest_profiles = Profile.objects.order_by('-created_at')[:10]

    dashboard_stats = {}
    if request.user.is_staff:
        dashboard_stats = {
            'total_users': User.objects.count(),
            'total_profiles': Profile.objects.count(),
            'total_ratings': Rating.objects.count(),
            'total_comments': Comment.objects.count(),
        }

    return render(request, 'profiles/profile_list.html', {
        'profiles': page_obj,
        'page_obj': page_obj,
        'page_range': page_range,
        'prev_chunk_page': prev_chunk_page,
        'next_chunk_page': next_chunk_page,
        'total_pages': total_pages,
        'current_group': current_group,
        'pages_per_group': pages_per_group,
        'tags': tags,
        'sort': sort,
        'active_tag': int(tag_id) if tag_id else None,
        'query': query,
        'featured_profile': featured_profile,
        'newest_profiles': newest_profiles,
        'top_rated': top_rated,
        'dashboard_stats': dashboard_stats,
    })


@csrf_exempt
def rate_profile(request, profile_id):
    if request.method == 'POST':
        data = json.loads(request.body)
        profile = get_object_or_404(Profile, id=profile_id)
        rating_value = data.get('rating')

        session_key = request.session.session_key or request.session.save()

        Rating.objects.update_or_create(
            profile=profile,
            session_key=request.session.session_key,
            defaults={'rating': rating_value}
        )

        avg_rating = profile.ratings.aggregate(avg=Avg('rating'))['avg']
        total = profile.ratings.aggregate(count=Count('rating'))['count']

        return JsonResponse({
            'new_rating': round(avg_rating or 0, 2),
            'total_votes': total
        })


def profile_detail(request, profile_id):
    profile = get_object_or_404(Profile, id=profile_id)
    user_rating = Rating.objects.filter(profile=profile, session_key=request.session.session_key).first()
    comments = profile.comments.all().order_by('-created_at')
    images = profile.images.all()[:6]
    profile.views += 1
    profile.save(update_fields=["views"])

    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.profile = profile
            comment.session_key = request.session.session_key
            if request.user.is_authenticated:
                comment.user = request.user
            comment.save()
            return redirect('profile_detail', profile_id=profile.id)
    else:
        form = CommentForm()

    context = {
        'profile': profile,
        'user_rating': user_rating.rating if user_rating else 0,
        'avg_rating': profile.ratings.aggregate(avg=Avg('rating'))['avg'] or 0,
        'total_ratings': profile.ratings.count(),
        'comments': comments,
        'form': form,
        'images': images
    }

    return render(request, 'profiles/profile_detail.html', context)


def leaderboard(request):
    top_rated = Profile.objects.annotate(avg_rating=Avg('ratings__rating')).order_by('-avg_rating')[:10]
    most_commented = Profile.objects.annotate(comment_count=Count('comments')).order_by('-comment_count')[:10]
    most_influential = sorted(Profile.objects.all(), key=lambda p: p.influence_score, reverse=True)[:10]
    most_viewed = Profile.objects.order_by('-views')[:10]
    fan_favorites = Profile.objects.annotate(fan_votes_count=Count('fan_votes')).order_by('-fan_votes_count')[:10]
    recently_trending = Profile.objects.order_by('-created_at')[:10]
    rising_stars = Profile.objects.annotate(total_ratings=Count('ratings')).order_by('total_ratings', '-created_at')[:10]
    most_feedback_given = User.objects.annotate(comment_count=Count('comment')).order_by('-comment_count')[:10]

    leaderboard_sections = [
        ("Top Rated", top_rated, "avg_rating", "primary", "/5"),
        ("Most Commented", most_commented, "comment_count", "success", ""),
        ("Most Viewed", most_viewed, "views", "info", ""),
        ("Fan Favorites", fan_favorites, "fan_votes_count", "danger", ""),
        ("Influence Score", most_influential, "influence_score", "warning", ""),
        ("Recently Trending", recently_trending, "avg_rating", "secondary", "/5"),
        ("Rising Stars", rising_stars, "avg_rating", "info", "/5"),
        ("Most Feedback Given", most_feedback_given, None, "warning-subtle", " comments")
    ]

    return render(request, 'profiles/leaderboard.html', {
        'leaderboard_sections': leaderboard_sections
    })


