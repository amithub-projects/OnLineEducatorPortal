from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/live/(?P<room_code>[a-zA-Z0-9]+)/$', consumers.LiveClassConsumer.as_asgi()),
]
