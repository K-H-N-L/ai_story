"""
剧本管理领域模型
遵循单一职责原则(SRP)
"""

import uuid
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Screenplay(models.Model):
    """
    剧本聚合根
    职责: 管理剧本基本信息和状态
    """

    STATUS_CHOICES = [
        ('draft', '草稿'),
        ('in_progress', '进行中'),
        ('completed', '已完成'),
        ('archived', '已归档'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField('剧本标题', max_length=255)
    description = models.TextField('剧本描述', blank=True, default='')
    status = models.CharField('状态', max_length=20, choices=STATUS_CHOICES, default='draft')

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='创建者',
        related_name='screenplays'
    )

    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'screenplays'
        verbose_name = '剧本'
        verbose_name_plural = '剧本'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at'], name='screenplays_user_created_idx'),
        ]

    def __str__(self):
        return self.title


class ScreenplayEpisode(models.Model):
    """
    分集剧本
    职责: 管理剧本中的单集文案内容
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    screenplay = models.ForeignKey(
        Screenplay,
        on_delete=models.CASCADE,
        related_name='episodes',
        verbose_name='所属剧本'
    )
    episode_number = models.IntegerField('分集序号')
    episode_title = models.CharField('分集标题', max_length=255, blank=True, default='')
    content = models.TextField('原始文案内容', blank=True, default='')
    sort_order = models.IntegerField('排序值', default=0)

    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'screenplay_episodes'
        verbose_name = '分集剧本'
        verbose_name_plural = '分集剧本'
        ordering = ['sort_order', 'episode_number']
        constraints = [
            models.UniqueConstraint(
                fields=['screenplay', 'episode_number'],
                name='uniq_screenplay_episode_number',
            ),
        ]
        indexes = [
            models.Index(fields=['screenplay', 'sort_order', 'episode_number'], name='episode_sort_idx'),
        ]

    def __str__(self):
        return f'{self.screenplay.title} - 第{self.episode_number}集'
