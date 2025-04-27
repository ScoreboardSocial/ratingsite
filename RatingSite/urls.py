from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from profiles.views import signup
from profiles.admin import admin_site  # ✅ use custom admin

urlpatterns = [
    path('admin/', admin_site.urls),  # ✅ use your custom admin site
    path('', include('profiles.urls')),  # profiles.urls will handle home, list, rate, detail
    path('accounts/login/', auth_views.LoginView.as_view(), name='login'),
    path('accounts/signup/', signup, name='signup'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('accounts/', include('django.contrib.auth.urls')),  # 👈 this enables password_reset and others
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
