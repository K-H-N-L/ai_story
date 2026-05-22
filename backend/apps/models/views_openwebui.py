"""
Open WebUI 兼容层视图
提供 OpenAI 兼容的 API 接口,将请求路由到对应的 ModelProvider
"""

import json
import time
import logging
import uuid
from django.http import StreamingHttpResponse, JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status
from .models import ModelProvider, ProviderType, ModelUsageLog
from .load_balancer import ModelLoadBalancer

logger = logging.getLogger(__name__)


class OpenWebUIModelsView(APIView):
    """
    Open WebUI 模型列表接口
    GET /api/models - 返回可用模型列表,格式兼容 OpenAI
    """
    permission_classes = [AllowAny]

    def get(self, request):
        providers = ModelProvider.objects.filter(
            is_active=True,
            provider_type='openwebui',
        ).order_by('priority', 'name')

        models = []
        for provider in providers:
            models.append({
                'id': provider.openwebui_model_id or provider.model_name,
                'name': provider.display_name or provider.name,
                'object': 'model',
                'created': int(provider.created_at.timestamp()),
                'owned_by': 'openwebui',
            })

        return Response({
            'object': 'list',
            'data': models,
        })


@method_decorator(csrf_exempt, name='dispatch')
class OpenWebUIChatView(APIView):
    """
    Open WebUI 聊天补全接口
    POST /api/chat/completions - 兼容 OpenAI Chat Completions API

    请求流程:
    1. 解析请求体,获取 model 字段
    2. 通过 ModelResolver 解析到本地 ModelProvider
    3. 调用对应 provider 的 execute 方法
    4. 返回 OpenAI 格式的响应(支持流式/非流式)
    """
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            body = request.data if hasattr(request, 'data') else json.loads(request.body)
        except (json.JSONDecodeError, Exception) as e:
            return Response(
                {'error': {'message': f'Invalid JSON: {str(e)}', 'type': 'invalid_request_error'}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        model_id = body.get('model', '')
        messages = body.get('messages', [])
        stream = body.get('stream', False)
        temperature = body.get('temperature', 0.7)
        max_tokens = body.get('max_tokens')

        if not model_id:
            return Response(
                {'error': {'message': 'model is required', 'type': 'invalid_request_error'}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not messages:
            return Response(
                {'error': {'message': 'messages is required', 'type': 'invalid_request_error'}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 解析模型
        provider = self._resolve_provider(model_id)
        if not provider:
            return Response(
                {'error': {'message': f'Model {model_id} not found', 'type': 'invalid_request_error'}},
                status=status.HTTP_404_NOT_FOUND,
            )

        # 构建下游请求
        request_id = f"chatcmpl-{uuid.uuid4().hex[:24]}"
        start_time = time.time()

        try:
            if stream:
                return self._handle_stream(
                    provider, messages, temperature, max_tokens, request_id, model_id, start_time
                )
            else:
                return self._handle_non_stream(
                    provider, messages, temperature, max_tokens, request_id, model_id, start_time
                )
        except Exception as e:
            logger.error(f'Chat completion error: {e}', exc_info=True)
            return Response(
                {'error': {'message': str(e), 'type': 'server_error'}},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _resolve_provider(self, model_id):
        """
        解析模型名称到 ModelProvider
        优先级:
        1. openwebui 类型 + openwebui_model_id 精确匹配
        2. openwebui 类型 + model_name 匹配
        3. 其他类型 + model_name 匹配
        """
        # 优先匹配 openwebui 类型
        provider = ModelProvider.objects.filter(
            is_active=True,
            provider_type='openwebui',
            openwebui_model_id=model_id,
        ).first()

        if provider:
            return provider

        # 匹配 model_name
        provider = ModelProvider.objects.filter(
            is_active=True,
            model_name=model_id,
        ).first()

        return provider

    def _build_payload(self, provider, messages, temperature, max_tokens, stream=False):
        """构建发送给下游 API 的请求体"""
        # 通用 OpenAI 兼容格式
        payload = {
            'model': provider.model_name,
            'messages': messages,
            'temperature': temperature,
            'stream': stream,
        }

        if max_tokens:
            payload['max_tokens'] = max_tokens

        return payload

    def _get_headers(self, provider):
        """构建下游 API 请求头"""
        headers = {
            'Content-Type': 'application/json',
        }

        if provider.api_key:
            headers['Authorization'] = f'Bearer {provider.api_key}'

        return headers

    def _handle_non_stream(self, provider, messages, temperature, max_tokens, request_id, model_id, start_time):
        """处理非流式请求"""
        import requests as http_requests

        url = f"{provider.api_url.rstrip('/')}/chat/completions"
        headers = self._get_headers(provider)
        payload = self._build_payload(provider, messages, temperature, max_tokens, stream=False)

        try:
            response = http_requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=120,
            )
            response.raise_for_status()
            result = response.json()
        except http_requests.RequestException as e:
            logger.error(f'Downstream API error: {e}')
            raise Exception(f'下游 API 调用失败: {str(e)}')

        # 记录使用日志
        latency_ms = int((time.time() - start_time) * 1000)
        usage = result.get('usage', {})
        self._log_usage(provider, model_id, usage, latency_ms)

        # 确保响应格式正确
        result['id'] = request_id
        result['model'] = model_id

        return Response(result)

    def _handle_stream(self, provider, messages, temperature, max_tokens, request_id, model_id, start_time):
        """处理流式请求 - 使用 SSE 格式转发"""
        import requests as http_requests

        url = f"{provider.api_url.rstrip('/')}/chat/completions"
        headers = self._get_headers(provider)
        payload = self._build_payload(provider, messages, temperature, max_tokens, stream=True)

        try:
            response = http_requests.post(
                url,
                headers=headers,
                json=payload,
                stream=True,
                timeout=300,
            )
            response.raise_for_status()
        except http_requests.RequestException as e:
            logger.error(f'Downstream streaming API error: {e}')
            raise Exception(f'下游流式 API 调用失败: {str(e)}')

        def event_stream():
            """SSE 事件生成器"""
            # 发送开始事件
            start_chunk = {
                'id': request_id,
                'object': 'chat.completion.chunk',
                'created': int(time.time()),
                'model': model_id,
                'choices': [{
                    'index': 0,
                    'delta': {'role': 'assistant', 'content': ''},
                    'finish_reason': None,
                }],
            }
            yield f"data: {json.dumps(start_chunk, ensure_ascii=False)}\n\n"

            total_tokens = 0
            try:
                for line in response.iter_lines():
                    if not line:
                        continue

                    line_str = line.decode('utf-8') if isinstance(line, bytes) else line

                    if line_str.startswith('data: '):
                        data_str = line_str[6:]

                        if data_str.strip() == '[DONE]':
                            yield f"data: [DONE]\n\n"
                            break

                        try:
                            chunk_data = json.loads(data_str)
                            # 统计 token (粗略估计)
                            choices = chunk_data.get('choices', [])
                            for choice in choices:
                                delta = choice.get('delta', {})
                                content = delta.get('content', '')
                                if content:
                                    total_tokens += 1

                            # 转发 chunk, 确保 model 字段一致
                            chunk_data['id'] = request_id
                            chunk_data['model'] = model_id
                            yield f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"

                        except json.JSONDecodeError:
                            # 转发原始行
                            yield f"{line_str}\n\n"

            except Exception as e:
                logger.error(f'Stream error: {e}')
                error_chunk = {
                    'id': request_id,
                    'object': 'chat.completion.chunk',
                    'created': int(time.time()),
                    'model': model_id,
                    'choices': [{
                        'index': 0,
                        'delta': {},
                        'finish_reason': 'stop',
                    }],
                }
                yield f"data: {json.dumps(error_chunk, ensure_ascii=False)}\n\n"
                yield f"data: [DONE]\n\n"
            finally:
                # 记录使用日志
                latency_ms = int((time.time() - start_time) * 1000)
                self._log_usage(provider, model_id, {'total_tokens': total_tokens}, latency_ms)

        response_obj = StreamingHttpResponse(
            event_stream(),
            content_type='text/event-stream',
        )
        response_obj['Cache-Control'] = 'no-cache'
        response_obj['X-Accel-Buffering'] = 'no'
        return response_obj

    def _log_usage(self, provider, model_id, usage, latency_ms):
        """记录模型使用日志"""
        try:
            ModelUsageLog.objects.create(
                provider=provider,
                model_name=model_id,
                request_type='chat',
                prompt_tokens=usage.get('prompt_tokens', 0),
                completion_tokens=usage.get('completion_tokens', 0),
                total_tokens=usage.get('total_tokens', 0),
                latency_ms=latency_ms,
            )
        except Exception as e:
            logger.warning(f'Failed to log usage: {e}')


@method_decorator(csrf_exempt, name='dispatch')
class OpenWebUIGenerateView(APIView):
    """
    Open WebUI 文本生成接口
    POST /api/generate - 兼容旧版 OpenAI completions API
    """
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            body = request.data if hasattr(request, 'data') else json.loads(request.body)
        except (json.JSONDecodeError, Exception) as e:
            return Response(
                {'error': {'message': f'Invalid JSON: {str(e)}', 'type': 'invalid_request_error'}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        model_id = body.get('model', '')
        prompt = body.get('prompt', '')
        stream = body.get('stream', False)

        if not model_id or not prompt:
            return Response(
                {'error': {'message': 'model and prompt are required', 'type': 'invalid_request_error'}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 将 prompt 转换为 messages 格式,复用 chat 逻辑
        messages = [{'role': 'user', 'content': prompt}]
        chat_body = {
            'model': model_id,
            'messages': messages,
            'stream': stream,
            'temperature': body.get('temperature', 0.7),
            'max_tokens': body.get('max_tokens'),
        }

        # 创建新的 request 对象并转发到 ChatView
        chat_view = OpenWebUIChatView()
        chat_view.request = request
        request._full_data = chat_body
        return chat_view.post(request)
