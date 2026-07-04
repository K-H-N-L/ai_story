#!/usr/bin/env python
import os
import sys

# 设置 Django 环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')

import django
django.setup()

from apps.models.models import ModelProvider

def create_mock_models():
    # 创建 Mock LLM 模型
    llm_mock, created = ModelProvider.objects.get_or_create(
        name='Mock LLM',
        provider_type='llm',
        defaults={
            'executor_class': 'core.ai_client.mock_llm_client.MockLLMClient',
            'api_url': 'http://backend:8010/api/mock/llm/',
            'api_key': 'mock-key',
            'model_name': 'mock-llm',
            'max_tokens': 2000,
            'temperature': 0.7,
            'is_active': True,
            'priority': 100
        }
    )
    print(f'Mock LLM模型: {"已创建" if created else "已存在"}')

    # 创建 Mock 文生图模型
    text2image_mock, created = ModelProvider.objects.get_or_create(
        name='Mock 文生图',
        provider_type='text2image',
        defaults={
            'executor_class': 'core.ai_client.mock_text2image_client.MockText2ImageClient',
            'api_url': 'http://backend:8010/api/mock/text2image/',
            'api_key': 'mock-key',
            'model_name': 'mock-text2image',
            'is_active': True,
            'priority': 100
        }
    )
    print(f'Mock 文生图模型: {"已创建" if created else "已存在"}')

    # 创建 Mock 图生视频模型
    image2video_mock, created = ModelProvider.objects.get_or_create(
        name='Mock 图生视频',
        provider_type='image2video',
        defaults={
            'executor_class': 'core.ai_client.mock_image2video_client.MockImage2VideoClient',
            'api_url': 'http://backend:8010/api/mock/image2video/',
            'api_key': 'mock-key',
            'model_name': 'mock-image2video',
            'is_active': True,
            'priority': 100
        }
    )
    print(f'Mock 图生视频模型: {"已创建" if created else "已存在"}')

    print('\nMock模型配置完成!')

if __name__ == '__main__':
    create_mock_models()
