"""
剧本管理视图集
职责: 处理剧本和分集的CRUD请求
遵循单一职责原则(SRP)
"""

from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import Screenplay, ScreenplayEpisode
from .serializers import (
    ScreenplayListSerializer,
    ScreenplayDetailSerializer,
    ScreenplayCreateSerializer,
    ScreenplayEpisodeSerializer,
)


class ScreenplayViewSet(viewsets.ModelViewSet):
    """
    剧本视图集
    职责: 管理剧本的增删改查
    """

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'updated_at', 'title']
    filterset_fields = ['status']

    def get_queryset(self):
        """过滤当前用户的剧本"""
        return Screenplay.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        """根据动作选择序列化器"""
        if self.action == 'list':
            return ScreenplayListSerializer
        elif self.action in ('create', 'update', 'partial_update'):
            return ScreenplayCreateSerializer
        return ScreenplayDetailSerializer

    def perform_create(self, serializer):
        """创建时自动设置用户"""
        serializer.save(user=self.request.user)


class ScreenplayEpisodeViewSet(viewsets.ModelViewSet):
    """
    分集剧本视图集
    职责: 管理分集的增删改查
    """

    serializer_class = ScreenplayEpisodeSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['episode_number', 'sort_order', 'created_at']

    def get_queryset(self):
        """过滤当前用户所属剧本的分集"""
        return ScreenplayEpisode.objects.filter(
            screenplay__user=self.request.user
        )
