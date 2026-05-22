"""
Open WebUI 模型同步管理命令
从 Open WebUI 拉取模型列表，自动创建或更新 ModelProvider
"""

import json
import logging
import requests
from django.core.management.base import BaseCommand, CommandError
from apps.models.models import ModelProvider, ProviderType
from config.settings.base import OPENWEBUI_BASE_URL, OPENWEBUI_API_KEY

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '从 Open WebUI 同步模型列表到 ModelProvider'

    def add_arguments(self, parser):
        parser.add_argument(
            '--base-url',
            type=str,
            default=None,
            help='Open WebUI 基础 URL (默认使用环境变量 OPENWEBUI_BASE_URL)',
        )
        parser.add_argument(
            '--api-key',
            type=str,
            default=None,
            help='Open WebUI API Key (默认使用环境变量 OPENWEBUI_API_KEY)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='仅显示将要同步的模型，不实际创建',
        )
        parser.add_argument(
            '--output',
            type=str,
            default=None,
            help='将模型列表输出为 JSON 文件路径',
        )

    def handle(self, *args, **options):
        base_url = options['base_url'] or OPENWEBUI_BASE_URL
        api_key = options['api_key'] or OPENWEBUI_API_KEY

        if not base_url:
            raise CommandError(
                '未配置 Open WebUI URL。请设置 OPENWEBUI_BASE_URL 环境变量或使用 --base-url 参数。'
            )

        if not api_key:
            raise CommandError(
                '未配置 Open WebUI API Key。请设置 OPENWEBUI_API_KEY 环境变量或使用 --api-key 参数。'
            )

        # 拉取模型列表
        self.stdout.write(f'正在从 {base_url} 拉取模型列表...')
        models_data = self._fetch_models(base_url, api_key)

        if not models_data:
            self.stdout.write(self.style.WARNING('未获取到任何模型'))
            return

        self.stdout.write(f'获取到 {len(models_data)} 个模型')

        # 如果指定了输出文件，写入 JSON
        if options['output']:
            self._write_json(models_data, options['output'])

        # 同步到数据库
        resolver = ModelResolver(base_url)
        stats = {'created': 0, 'updated': 0, 'skipped': 0}

        for model_info in models_data:
            result = resolver.resolve(model_info, dry_run=options['dry_run'])

            if result['action'] == 'created':
                stats['created'] += 1
                self.stdout.write(
                    self.style.SUCCESS(f"  [新建] {result['display_name']} → {result['provider_name']}")
                )
            elif result['action'] == 'updated':
                stats['updated'] += 1
                self.stdout.write(
                    self.style.WARNING(f"  [更新] {result['display_name']} → {result['provider_name']}")
                )
            else:
                stats['skipped'] += 1
                if options['dry_run']:
                    self.stdout.write(f"  [跳过] {result['display_name']} (已存在)")

        # 输出统计
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f"同步完成: 新建 {stats['created']}, 更新 {stats['updated']}, 跳过 {stats['skipped']}"
        ))

    def _fetch_models(self, base_url, api_key):
        """从 Open WebUI API 获取模型列表"""
        url = f"{base_url.rstrip('/')}/api/models"
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        }

        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()

            # Open WebUI 返回格式: {"data": [...]} 或直接 [...]
            if isinstance(data, dict) and 'data' in data:
                return data['data']
            elif isinstance(data, list):
                return data
            else:
                logger.warning(f'未知的响应格式: {type(data)}')
                return []

        except requests.RequestException as e:
            raise CommandError(f'请求 Open WebUI 失败: {e}')
        except ValueError as e:
            raise CommandError(f'解析响应失败: {e}')

    def _write_json(self, models_data, filepath):
        """将模型列表写入 JSON 文件"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(models_data, f, ensure_ascii=False, indent=2)
        self.stdout.write(f'模型列表已写入: {filepath}')


class ModelResolver:
    """
    模型解析器
    将 Open WebUI 的模型条目映射为本地 ModelProvider 记录
    """

    # Open WebUI 模型名称中的已知提供商前缀
    KNOWN_PROVIDER_PREFIXES = {
        'openai': 'openai',
        'gpt': 'openai',
        'o1': 'openai',
        'o3': 'openai',
        'claude': 'anthropic',
        'anthropic': 'anthropic',
        'gemini': 'gemini',
        'google': 'gemini',
        'deepseek': 'deepseek',
        'qwen': 'qwen',
        'doubao': 'doubao',
        'glm': 'glm',
        'moonshot': 'moonshot',
        'yi': 'yi',
        'minimax': 'minimax',
        'hunyuan': 'hunyuan',
        'baichuan': 'baichuan',
        'mistral': 'mistral',
        'llama': 'ollama',
        'mixtral': 'mistral',
    }

    # provider_id 到 ProviderType 的映射
    PROVIDER_TYPE_MAP = {
        'openai': ProviderType.OPENAI,
        'anthropic': ProviderType.ANTHROPIC,
        'gemini': ProviderType.GEMINI,
        'deepseek': ProviderType.DEEPSEEK,
        'qwen': ProviderType.QWEN,
        'doubao': ProviderType.DOUBAO,
        'glm': ProviderType.GLM,
        'moonshot': ProviderType.MOONSHOT,
        'yi': ProviderType.YI,
        'minimax': ProviderType.MINIMAX,
        'hunyuan': ProviderType.HUNYUAN,
        'baichuan': ProviderType.BAICHUAN,
        'mistral': ProviderType.MISTRAL,
        'ollama': ProviderType.OLLAMA,
        'lmstudio': ProviderType.LMSTUDIO,
        'vllm': ProviderType.VLLM,
        'openrouter': ProviderType.OPENROUTER,
        'siliconflow': ProviderType.SILICONFLOW,
    }

    def __init__(self, openwebui_base_url):
        self.openwebui_base_url = openwebui_base_url

    def resolve(self, model_info, dry_run=False):
        """
        解析单个模型条目，返回 {action, display_name, provider_name}

        分辨逻辑:
        1. 已有 provider_type='openwebui' + openwebui_model_id 匹配 → 更新
        2. 如果模型名称匹配已知提供商前缀 → 使用该提供商
        3. 尝试解析为 provider_id/model_name 格式
        4. 降级为 openwebui 直连
        """
        model_id = model_info.get('id', model_info.get('name', ''))
        model_name = model_info.get('name', model_id)
        display_name = model_info.get('name', model_id)

        # 先检查是否已存在 openwebui 类型的同名模型
        existing = ModelProvider.objects.filter(
            provider_type='openwebui',
            openwebui_model_id=model_id,
        ).first()

        if existing:
            if not dry_run:
                existing.display_name = display_name
                existing.save(update_fields=['display_name', 'updated_at'])
            return {
                'action': 'skipped' if not existing else 'updated',
                'display_name': display_name,
                'provider_name': existing.name,
            }

        # 尝试识别提供商
        provider_id, resolved_model_name = self._identify_provider(model_id)

        if provider_id:
            return self._resolve_known_provider(
                provider_id, resolved_model_name, display_name, model_info, dry_run
            )
        else:
            return self._resolve_openwebui_direct(model_id, display_name, model_info, dry_run)

    def _identify_provider(self, model_id):
        """
        识别模型所属的提供商
        返回 (provider_id, model_name) 或 (None, None)
        """
        # 尝试 provider_id/model_name 格式
        if '/' in model_id:
            parts = model_id.split('/', 1)
            candidate_provider = parts[0].lower()
            candidate_model = parts[1]

            if candidate_provider in self.PROVIDER_TYPE_MAP:
                return candidate_provider, candidate_model

        # 尝试前缀匹配
        model_lower = model_id.lower()
        for prefix, provider_id in self.KNOWN_PROVIDER_PREFIXES.items():
            if model_lower.startswith(prefix):
                return provider_id, model_id

        return None, None

    def _resolve_known_provider(self, provider_id, model_name, display_name, model_info, dry_run):
        """处理已知提供商的模型"""
        provider_type = self.PROVIDER_TYPE_MAP[provider_id]

        # 查找该提供商下是否有匹配的现有记录
        existing = ModelProvider.objects.filter(
            provider_type=provider_type,
            model_name=model_name,
        ).first()

        if existing:
            return {
                'action': 'skipped',
                'display_name': display_name,
                'provider_name': existing.name,
            }

        # 创建新记录
        provider_name = f"{self._get_provider_display(provider_type)} {model_name}"

        if not dry_run:
            ModelProvider.objects.create(
                name=provider_name,
                provider_type=provider_type,
                model_name=model_name,
                display_name=display_name,
                api_url=self._get_default_api_url(provider_type),
                is_active=True,
                priority=50,
            )

        return {
            'action': 'created',
            'display_name': display_name,
            'provider_name': provider_name,
        }

    def _resolve_openwebui_direct(self, model_id, display_name, model_info, dry_run):
        """降级处理: 通过 Open WebUI 直连"""
        # 检查是否已存在
        existing = ModelProvider.objects.filter(
            provider_type='openwebui',
            openwebui_model_id=model_id,
        ).first()

        if existing:
            return {
                'action': 'skipped',
                'display_name': display_name,
                'provider_name': existing.name,
            }

        provider_name = f"OpenWebUI/{display_name}"

        if not dry_run:
            ModelProvider.objects.create(
                name=provider_name,
                provider_type='openwebui',
                model_name=model_id,
                display_name=display_name,
                api_url=self.openwebui_base_url,
                openwebui_model_id=model_id,
                is_active=True,
                priority=50,
            )

        return {
            'action': 'created',
            'display_name': display_name,
            'provider_name': provider_name,
        }

    def _get_provider_display(self, provider_type):
        """获取提供商的显示名称"""
        for value, label in ProviderType.choices:
            if value == provider_type:
                return label
        return provider_type

    def _get_default_api_url(self, provider_type):
        """获取提供商的默认 API URL"""
        url_map = {
            ProviderType.OPENAI: 'https://api.openai.com/v1',
            ProviderType.ANTHROPIC: 'https://api.anthropic.com/v1',
            ProviderType.GEMINI: 'https://generativelanguage.googleapis.com/v1beta',
            ProviderType.DEEPSEEK: 'https://api.deepseek.com/v1',
            ProviderType.QWEN: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
            ProviderType.DOUBAO: 'https://ark.cn-beijing.volces.com/api/v3',
            ProviderType.GLM: 'https://open.bigmodel.cn/api/paas/v4',
            ProviderType.MOONSHOT: 'https://api.moonshot.cn/v1',
            ProviderType.YI: 'https://api.lingyiwanwu.com/v1',
            ProviderType.MINIMAX: 'https://api.minimax.chat/v1',
            ProviderType.HUNYUAN: 'https://api.hunyuan.cloud.tencent.com/v1',
            ProviderType.BAICHUAN: 'https://api.baichuan-ai.com/v1',
            ProviderType.MISTRAL: 'https://api.mistral.ai/v1',
            ProviderType.OLLAMA: 'http://localhost:11434/v1',
            ProviderType.LMSTUDIO: 'http://localhost:1234/v1',
            ProviderType.VLLM: 'http://localhost:8000/v1',
        }
        return url_map.get(provider_type, '')
