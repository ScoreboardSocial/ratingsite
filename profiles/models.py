from django.db import models
from django.db.models import Avg, Count
from django.contrib.auth.models import User
from django.conf import settings

class Tag(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name

class Profile(models.Model):
    name = models.CharField(max_length=100)
    image = models.ImageField(upload_to='profile_images/', default='profile_images/default.jpg')
    rating = models.FloatField(default=0)
    instagram = models.URLField(blank=True)
    twitter = models.URLField(blank=True)
    other = models.URLField(blank=True)
    tags = models.ManyToManyField(Tag, blank=True)
    views = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def influence_score(self):
        avg_rating = self.ratings.aggregate(avg=Avg('rating'))['avg'] or 0
        total_votes = self.ratings.count()
        total_comments = self.comments.count()
        return round((avg_rating * 50) + (total_votes * 2) + (total_comments * 3), 2)

    def average_rating(self):
        return self.ratings.aggregate(average=Avg('rating'))['average'] or 0

    def total_votes(self):
        return self.ratings.aggregate(count=Count('rating'))['count'] or 0

    def fan_favorite_votes(self):
        return self.fan_votes.count()

    def __str__(self):
        return self.name

class FanFavoriteVote(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    profile = models.ForeignKey('Profile', on_delete=models.CASCADE, related_name='fan_votes')
    voted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'profile')  # one vote per user per profile
        ordering = ['-voted_at']

    def __str__(self):
        return f"{self.user.username} voted for {self.profile.name}"

class Rating(models.Model):
    profile = models.ForeignKey(Profile, related_name='ratings', on_delete=models.CASCADE)
    rating = models.DecimalField(max_digits=3, decimal_places=2, null=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)

    def __str__(self):
        return f"{self.profile.name} - {self.rating}"

class Comment(models.Model):
    profile = models.ForeignKey(Profile, related_name='comments', on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Comment by {self.user.username} on {self.profile.name}'

class ProfileImage(models.Model):
    profile = models.ForeignKey(Profile, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='profile_images/')

    def __str__(self):
        return f"Image for {self.profile.name}"
