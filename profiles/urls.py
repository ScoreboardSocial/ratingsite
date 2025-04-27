from django.urls import path
from .import views
from .views import (
    profile_list,
    profile_detail,
    rate_profile,
    signup,
    comment_edit,
    comment_delete
)

urlpatterns = [
    path('', profile_list, name='profile_list'),
    path('<int:profile_id>/', profile_detail, name='profile_detail'),
    path('profiles/<int:profile_id>/rate/', views.rate_profile, name='rate_profile'),
    path('signup/', signup, name='signup'),
    path('comment/<int:pk>/edit/', comment_edit, name='comment_edit'),
    path('comment/<int:pk>/delete/', comment_delete, name='comment_delete'),
    path('leaderboard/', views.leaderboard, name='leaderboard'),
    path('<int:profile_id>/vote-fan-favorite/', views.vote_fan_favorite, name='vote_fan_favorite'),
]
