from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),

    # Public pages
    path('', include('apps.core.urls')),

    # Authentication
    path('auth/', include('apps.authentication.urls')),

    # Educator panel
    path('educator/', include('apps.courses.urls')),
    path('educator/content/', include('apps.content.urls')),
    path('educator/schedule/', include('apps.scheduling.urls')),
    path('educator/live/', include('apps.live_classes.urls')),
    path('educator/chat/', include('apps.chat.urls')),

    # Payments
    path('payments/', include('apps.payments.urls')),

    # REST API
    path('api/', include('apps.api.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
