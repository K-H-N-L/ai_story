"""
剧本管理序列化器
职责: 数据序列化与验证
遵循单一职责原则(SRP)
"""

from rest_framework import serializers
from .models import Screenplay, ScreenplayEpisode


class ScreenplayEpisodeSerializer(serializers.ModelSerializer):
    """分集剧本序列化器"""

    content_word_count = serializers.SerializerMethodField()

    class Meta:
        model = ScreenplayEpisode
        fields = [
            'id', 'screenplay', 'episode_number', 'episode_title',
            'content', 'sort_order', 'content_word_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_content_word_count(self, obj):
        """获取文案字数"""
        return len(obj.content) if obj.content else 0


class ScreenplayListSerializer(serializers.ModelSerializer):
    """剧本列表序列化器 - 轻量级"""

    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    episodes_count = serializers.SerializerMethodField()

    class Meta:
        model = Screenplay
        fields = [
            'id', 'title', 'description', 'status', 'status_display',
            'episodes_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_episodes_count(self, obj):
        """获取分集数量"""
        return obj.episodes.count()


class ScreenplayDetailSerializer(serializers.ModelSerializer):
    """剧本详情序列化器 - 完整信息,嵌套分集"""

    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    episodes = ScreenplayEpisodeSerializer(many=True, read_only=True)
    episodes_count = serializers.SerializerMethodField()

    class Meta:
        model = Screenplay
        fields = [
            'id', 'title', 'description', 'status', 'status_display',
            'episodes', 'episodes_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_episodes_count(self, obj):
        return obj.episodes.count()


class ScreenplayCreateSerializer(serializers.ModelSerializer):
    """剧本创建序列化器"""

    class Meta:
        model = Screenplay
        fields = ['id', 'title', 'description', 'status']
        read_only_fields = ['id']

    def create(self, validated_data):
        """创建剧本,自动设置当前用户"""
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['user'] = request.user
        return super().create(validated_data)
