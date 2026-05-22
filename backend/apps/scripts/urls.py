"""剧本管理URL路由"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ScreenplayViewSet, ScreenplayEpisodeViewSet

router = DefaultRouter()
router.register(r'screenplays', ScreenplayViewSet, basename='screenplay')
router.register(r'episodes', ScreenplayEpisodeViewSet, basename='episode')

urlpatterns = [
    path('', include(router.urls)),
]
