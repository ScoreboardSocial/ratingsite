from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME
from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.urls import path
from django.template.response import TemplateResponse
from django.db.models import Avg, Count
from django.http import HttpResponse
from django import forms
from django.shortcuts import render, redirect
import csv

from .models import Profile, Rating, Tag, Comment, ProfileImage, FanFavoriteVote

# ---------- CSV Export Action ----------
def export_profiles_csv(modeladmin, request, queryset):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="profiles.csv"'

    writer = csv.writer(response)
    writer.writerow(['ID', 'Name', 'Instagram', 'Twitter', 'Average Rating'])

    for profile in queryset:
        avg_rating = profile.ratings.aggregate(avg=Avg('rating'))['avg'] or 0
        writer.writerow([
            profile.id,
            profile.name,
            profile.instagram,
            profile.twitter,
            round(avg_rating, 2),
        ])

    return response

export_profiles_csv.short_description = "Export selected profiles to CSV"

# ---------- Bulk Tag Form ----------
class TagForm(forms.Form):
    _selected_action = forms.CharField(widget=forms.MultipleHiddenInput)
    tag_name = forms.CharField(label="Tag to apply", max_length=50)

# ---------- Profile Image Inline ----------
class ProfileImageInline(admin.TabularInline):
    model = ProfileImage
    extra = 1
    max_num = 6

# ---------- Profile Admin ----------
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['name', 'instagram', 'average_rating']
    search_fields = ['name', 'instagram', 'twitter']
    list_filter = ['tags']
    actions = [export_profiles_csv, 'bulk_add_tag']
    inlines = [ProfileImageInline]

    def average_rating(self, obj):
        result = obj.ratings.aggregate(avg=Avg('rating'))
        return round(result['avg'] or 0, 2)
    average_rating.short_description = 'Avg Rating'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('bulk-add-tag/', self.admin_site.admin_view(self.bulk_add_tag_view), name='bulk-add-tag'),
        ]
        return custom_urls + urls

    def bulk_add_tag(self, request, queryset):
        selected = request.POST.getlist(ACTION_CHECKBOX_NAME)
        return redirect(f'bulk-add-tag/?ids={",".join(selected)}')

    bulk_add_tag.short_description = "Add a tag to selected profiles"

    def bulk_add_tag_view(self, request):
        ids = request.GET.get('ids', '')
        profile_ids = ids.split(',')
        if request.method == 'POST':
            form = TagForm(request.POST)
            if form.is_valid():
                tag = form.cleaned_data['tag_name']
                profiles = Profile.objects.filter(id__in=profile_ids)
                for profile in profiles:
                    profile.tags.add(tag)
                self.message_user(request, f"Added tag '{tag}' to {profiles.count()} profiles.")
                return redirect('..')
        else:
            form = TagForm(initial={'_selected_action': profile_ids})
        return render(request, 'admin/bulk_add_tag.html', {'form': form, 'profile_ids': profile_ids})

# ---------- Custom Admin Site ----------
class CustomAdminSite(admin.AdminSite):
    site_header = 'Scoreboard Social Admin'
    site_title = 'Scoreboard Social Admin Portal'
    index_title = 'Welcome to the Scoreboard Social Dashboard'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('dashboard/', self.admin_view(self.dashboard_view)),
        ]
        return custom_urls + urls

    def dashboard_view(self, request):
        total_profiles = Profile.objects.count()
        total_ratings = Rating.objects.count()
        avg_rating = Rating.objects.aggregate(avg=Avg('rating'))['avg'] or 0

        context = dict(
            self.each_context(request),
            total_profiles=total_profiles,
            total_ratings=total_ratings,
            avg_rating=round(avg_rating, 2),
        )
        return TemplateResponse(request, "admin/dashboard.html", context)

# ---------- Custom User Admin ----------
class CustomUserAdmin(BaseUserAdmin):
    list_display = (
        'username',
        'email',
        'date_joined',
        'last_login',
        'comment_count',
        'rating_count',
        'fan_vote_count',
    )
    ordering = ('-date_joined',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(
            comment_count=Count('comment', distinct=True),
            rating_count=Count('rating', distinct=True),
            fan_vote_count=Count('fanfavoritevote', distinct=True),
        )

    def comment_count(self, obj):
        return obj.comment_count
    comment_count.short_description = "Comments"

    def rating_count(self, obj):
        return obj.rating_count
    rating_count.short_description = "Ratings"

    def fan_vote_count(self, obj):
        return obj.fan_vote_count
    fan_vote_count.short_description = "Fan Votes"

# ---------- Register Models ----------
admin_site = CustomAdminSite(name='scoreboard_admin')
admin_site.register(Profile, ProfileAdmin)
admin_site.register(Rating)
admin_site.register(Tag)
admin_site.register(Comment)
admin_site.register(ProfileImage)
admin_site.register(FanFavoriteVote)
admin_site.register(User, CustomUserAdmin)
