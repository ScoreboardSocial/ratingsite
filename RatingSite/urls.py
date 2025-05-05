from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from profiles.views import signup
from profiles.admin import admin_site  # Custom admin site

urlpatterns = [
    # ---------- Admin ----------
    path('admin/', admin_site.urls),

    # ---------- Main app URLs ----------
    path('', include('profiles.urls')),

    # ---------- Authentication ----------
    path('accounts/login/', auth_views.LoginView.as_view(), name='login'),
    path('accounts/signup/', signup, name='signup'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('accounts/', include('django.contrib.auth.urls')),  # includes password reset, change, etc.
]

# ---------- Serve media files in development ----------
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
