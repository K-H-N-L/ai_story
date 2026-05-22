"""
AI 代理视图
职责: 代理 LLM 请求和文件上传，复用 ModelProvider 配置
"""

import uuid
import time
import logging

import requests
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.models.models import ModelProvider
from core.utils.file_storage import image_storage, video_storage

logger = logging.getLogger(__name__)


class ChatCompletionsProxyView(APIView):
    """
    LLM 代理接口
    POST /api/v1/ai/chat/completions

    透传请求到 ModelProvider 配置的上游 API，返回 OpenAI 兼容格式。
    第一阶段只支持非流式（stream: false）。
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        model = request.data.get('model', '')
        messages = request.data.get('messages', [])
        temperature = request.data.get('temperature', 0.7)
        max_tokens = request.data.get('max_tokens', 2000)

        if not messages:
            return Response(
                {'error': 'messages 不能为空'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 按 model_name 精确匹配，找不到则取优先级最高的活跃 LLM provider
        provider = None
        if model:
            provider = ModelProvider.objects.filter(
                provider_type='llm',
                is_active=True,
                model_name=model
            ).order_by('-priority').first()

        if not provider:
            provider = ModelProvider.objects.filter(
                provider_type='llm',
                is_active=True
            ).order_by('-priority').first()

        if not provider:
            return Response(
                {'error': '没有可用的 LLM 模型提供商，请在后台配置 ModelProvider'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        headers = {
            'Authorization': f'Bearer {provider.api_key}',
            'Content-Type': 'application/json',
        }
        payload = {
            'model': provider.model_name,
            'messages': messages,
            'temperature': temperature,
            'max_tokens': max_tokens,
            'stream': False,
        }

        try:
            start_time = time.time()
            upstream_response = requests.post(
                provider.api_url,
                headers=headers,
                json=payload,
                timeout=provider.timeout,
            )
            latency_ms = int((time.time() - start_time) * 1000)

            if upstream_response.status_code == 200:
                result = upstream_response.json()
                if 'id' not in result:
                    result['id'] = f'chatcmpl-{uuid.uuid4().hex[:8]}'
                logger.info(
                    f'LLM 代理成功: provider={provider.name}, '
                    f'model={provider.model_name}, latency={latency_ms}ms'
                )
                return Response(result)

            logger.error(
                f'上游 API 请求失败: status={upstream_response.status_code}, '
                f'provider={provider.name}, body={upstream_response.text[:300]}'
            )
            return Response(
                {'error': f'上游 API 请求失败: {upstream_response.status_code}'},
                status=status.HTTP_502_BAD_GATEWAY
            )

        except requests.Timeout:
            return Response(
                {'error': '上游 API 请求超时'},
                status=status.HTTP_504_GATEWAY_TIMEOUT
            )
        except Exception as e:
            logger.error(f'LLM 代理异常: {str(e)}', exc_info=True)
            return Response(
                {'error': f'代理请求失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class FileUploadView(APIView):
    """
    文件上传接口
    POST /api/v1/ai/files/upload

    接收 multipart/form-data 中的 file 字段，保存到 storage 目录，返回访问 URL。
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        file = request.FILES.get('file')
        if not file:
            return Response(
                {'error': '请上传文件（字段名: file）'},
                status=status.HTTP_400_BAD_REQUEST
            )

        content_type = file.content_type or ''
        filename = file.name

        try:
            file_content = file.read()

            if content_type.startswith('image/'):
                _, relative_path = image_storage.save_file(filename, file_content)
                url_path = f'storage/image/{relative_path}'
            else:
                _, relative_path = video_storage.save_file(filename, file_content)
                url_path = f'storage/video/{relative_path}'

            scheme = request.scheme
            host = request.get_host()
            file_url = f'{scheme}://{host}/{url_path}'

            return Response({
                'id': f'file-{uuid.uuid4().hex[:8]}',
                'filename': filename,
                'url': file_url,
                'size': len(file_content),
                'created_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f'文件上传失败: {str(e)}', exc_info=True)
            return Response(
                {'error': f'文件上传失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
