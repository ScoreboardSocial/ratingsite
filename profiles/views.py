from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponseForbidden
from django.core.paginator import Paginator
from django.db.models import Avg, Count
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, get_user_model
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.contrib.auth.models import User

from .models import Profile, Tag, Rating, Comment, FanFavoriteVote
from .forms import CustomUserCreationForm, CommentForm
from django.utils import timezone
from datetime import timedelta

import json
import random

User = get_user_model()

@require_POST
@login_required
def vote_fan_favorite(request, profile_id):
    profile = get_object_or_404(Profile, id=profile_id)

    # Prevent duplicate votes
    already_voted = profile.fan_votes.filter(user=request.user).exists()
    if not already_voted:
        FanFavoriteVote.objects.create(user=request.user, profile=profile)

    return redirect('profile_detail', profile_id=profile.id)

@login_required
def comment_edit(request, pk):
    comment = get_object_or_404(Comment, pk=pk)
    if request.user != comment.user and not request.user.is_staff:
        return HttpResponseForbidden()

    if request.method == 'POST':
        form = CommentForm(request.POST, instance=comment)
        if form.is_valid():
            form.save()
            return redirect('profile_detail', profile_id=comment.profile.pk)
    else:
        form = CommentForm(instance=comment)

    return render(request, 'profiles/comment_edit.html', {'form': form, 'comment': comment})

@login_required
def comment_delete(request, pk):
    comment = get_object_or_404(Comment, pk=pk)
    if request.user != comment.user and not request.user.is_staff:
        return HttpResponseForbidden()

    if request.method == 'POST':
        profile_id = comment.profile.pk
        comment.delete()
        return redirect('profile_detail', profile_id=profile_id)

    return render(request, 'profiles/comment_delete_confirm.html', {'comment': comment})

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
        profiles = profiles.order_by('?')

    paginator = Paginator(profiles, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    tags = Tag.objects.all()
    all_profiles = list(Profile.objects.annotate(avg_rating=Avg('ratings__rating')))
    featured_profile = random.choice(all_profiles) if all_profiles else None

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
        'tags': tags,
        'sort': sort,
        'active_tag': int(tag_id) if tag_id else None,
        'featured_profile': featured_profile,
        'query': query,
        'dashboard_stats': dashboard_stats
    })

@csrf_exempt
@login_required
def rate_profile(request, profile_id):
    if request.method == 'POST':
        print(f"⭐ Rating received for profile {profile_id} by {request.user}")
        data = json.loads(request.body)
        profile = get_object_or_404(Profile, id=profile_id)
        rating_value = data.get('rating')

        Rating.objects.update_or_create(
            profile=profile,
            user=request.user,
            defaults={'rating': rating_value}
        )

        avg_rating = profile.ratings.aggregate(avg=Avg('rating'))['avg']
        total = profile.ratings.aggregate(count=Count('rating'))['count']

        return JsonResponse({
            'new_rating': round(avg_rating or 0, 2),
            'total_votes': total
        })

@login_required
def profile_detail(request, profile_id):
    profile = get_object_or_404(Profile, id=profile_id)
    user_rating = Rating.objects.filter(profile=profile, user=request.user).first()
    comments = profile.comments.all().order_by('-created_at')
    images = profile.images.all()[:6]
    profile.views += 1
    profile.save(update_fields=["views"])

    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.user = request.user
            comment.profile = profile
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
    fan_favorites = Profile.objects.annotate(fan_vote_count=Count('fan_votes')).order_by('-fan_vote_count')[:10]

    recently_trending = Profile.objects.order_by('-created_at')[:10]
    rising_stars = Profile.objects.annotate(total_ratings=Count('ratings')).order_by('total_ratings', '-created_at')[:10]
    most_feedback_given = User.objects.annotate(comment_count=Count('comment')).order_by('-comment_count')[:10]

    return render(request, 'profiles/leaderboard.html', {
        'top_rated': top_rated,
        'most_commented': most_commented,
        'most_influential': most_influential,
        'most_viewed': most_viewed,
        'fan_favorites': fan_favorites,
        'recently_trending': recently_trending,
        'rising_stars': rising_stars,
        'most_feedback_given': most_feedback_given,
    })
