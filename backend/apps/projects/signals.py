"""项目应用信号"""

import os
import uuid
from pathlib import Path

from django.apps import apps
from django.db import connection, transaction
from django.db.models.signals import post_migrate
from django.conf import settings
from jinja2 import Environment, meta


DEFAULT_PROMPT_DIR = Path(__file__).resolve().parent / 'default_promot'


def create_providers():
    """根据环境变量创建模型提供商配置。
    
    如果设置了环境变量，则创建真实提供商；否则创建 Mock 提供商。
    
    支持的环境变量:
    - LLM_API_URL: LLM API 地址
    - LLM_API_KEY: LLM API 密钥
    - LLM_MODEL_NAME: LLM 模型名称
    - TEXT2IMAGE_API_URL: 文生图 API 地址
    - TEXT2IMAGE_API_KEY: 文生图 API 密钥
    - TEXT2IMAGE_MODEL_NAME: 文生图模型名称
    - IMAGE2VIDEO_API_URL: 图生视频 API 地址
    - IMAGE2VIDEO_API_KEY: 图生视频 API 密钥
    - IMAGE2VIDEO_MODEL_NAME: 图生视频模型名称
    """
    ModelProvider = apps.get_model('models', 'ModelProvider')

    llm_api_url = getattr(settings, 'LLM_API_URL', '')
    llm_api_key = getattr(settings, 'LLM_API_KEY', '')
    llm_model_name = getattr(settings, 'LLM_MODEL_NAME', '')
    
    text2image_api_url = getattr(settings, 'TEXT2IMAGE_API_URL', '')
    text2image_api_key = getattr(settings, 'TEXT2IMAGE_API_KEY', '')
    text2image_model_name = getattr(settings, 'TEXT2IMAGE_MODEL_NAME', '')
    
    image2video_api_url = getattr(settings, 'IMAGE2VIDEO_API_URL', '')
    image2video_api_key = getattr(settings, 'IMAGE2VIDEO_API_KEY', '')
    image2video_model_name = getattr(settings, 'IMAGE2VIDEO_MODEL_NAME', '')

    if llm_api_url and llm_api_key and llm_model_name:
        create_real_llm_provider(ModelProvider, llm_api_url, llm_api_key, llm_model_name)
    else:
        create_mock_llm_provider(ModelProvider)

    if text2image_api_url and text2image_api_key and text2image_model_name:
        create_real_text2image_provider(ModelProvider, text2image_api_url, text2image_api_key, text2image_model_name)
    else:
        create_mock_text2image_provider(ModelProvider)

    if image2video_api_url and image2video_api_key and image2video_model_name:
        create_real_image2video_provider(ModelProvider, image2video_api_url, image2video_api_key, image2video_model_name)
    else:
        create_mock_image2video_provider(ModelProvider)


def create_real_llm_provider(ModelProvider, api_url, api_key, model_name):
    """创建真实 LLM 提供商。"""
    llm, created = ModelProvider.objects.get_or_create(
        name='Production LLM API',
        defaults={
            'id': uuid.uuid4(),
            'provider_type': 'llm',
            'executor_class': 'core.ai_client.openai_client.OpenAIClient',
            'api_url': api_url,
            'api_key': api_key,
            'model_name': model_name,
            'max_tokens': 4096,
            'temperature': 0.7,
            'top_p': 1.0,
            'timeout': 60,
            'is_active': True,
            'priority': 1,
            'rate_limit_rpm': 60,
            'rate_limit_rpd': 1000,
            'extra_config': {
                'description': '真实 LLM API，用于生产环境文案改写、分镜生成、运镜生成',
                'is_mock': False,
            }
        }
    )
    if created:
        print(f"✓ 已创建真实 LLM 提供商: {llm.name}")


def create_mock_llm_provider(ModelProvider):
    """创建 Mock LLM 提供商。"""
    mock_llm, created = ModelProvider.objects.get_or_create(
        name='Mock LLM API',
        defaults={
            'id': uuid.uuid4(),
            'provider_type': 'llm',
            'executor_class': 'core.ai_client.mock_llm_client.MockLLMClient',
            'api_url': 'http://localhost:8010/api/mock/llm/',
            'api_key': 'mock-api-key-not-required',
            'model_name': 'mock-llm-v1',
            'max_tokens': 4096,
            'temperature': 0.7,
            'top_p': 1.0,
            'timeout': 30,
            'is_active': True,
            'priority': 100,
            'rate_limit_rpm': 1000,
            'rate_limit_rpd': 100000,
            'extra_config': {
                'description': 'Mock LLM API，用于测试文案改写、分镜生成、运镜生成',
                'is_mock': True,
            }
        }
    )
    if created:
        print(f"✓ 已创建 Mock LLM 提供商: {mock_llm.name}")


def create_real_text2image_provider(ModelProvider, api_url, api_key, model_name):
    """创建真实文生图提供商。"""
    text2image, created = ModelProvider.objects.get_or_create(
        name='Production Text2Image API',
        defaults={
            'id': uuid.uuid4(),
            'provider_type': 'text2image',
            'executor_class': 'core.ai_client.executors.openai_images_generation_executor.OpenAIImagesGenerationExecutor',
            'api_url': api_url,
            'api_key': api_key,
            'model_name': model_name,
            'timeout': 120,
            'is_active': True,
            'priority': 1,
            'rate_limit_rpm': 30,
            'rate_limit_rpd': 500,
            'extra_config': {
                'description': '真实文生图 API，用于生产环境图片生成',
                'is_mock': False,
            }
        }
    )
    if created:
        print(f"✓ 已创建真实文生图提供商: {text2image.name}")


def create_mock_text2image_provider(ModelProvider):
    """创建 Mock 文生图提供商。"""
    mock_text2image, created = ModelProvider.objects.get_or_create(
        name='Mock Text2Image API',
        defaults={
            'id': uuid.uuid4(),
            'provider_type': 'text2image',
            'executor_class': 'core.ai_client.mock_text2image_client.MockText2ImageClient',
            'api_url': 'http://localhost:8010/api/mock',
            'api_key': 'mock-api-key-not-required',
            'model_name': 'mock-text2image-v1',
            'timeout': 60,
            'is_active': True,
            'priority': 100,
            'rate_limit_rpm': 500,
            'rate_limit_rpd': 50000,
            'extra_config': {
                'description': 'Mock 文生图 API，返回占位图片用于测试',
                'is_mock': True,
                'default_ratio': '1:1',
                'default_resolution': '2k',
            }
        }
    )
    if created:
        print(f"✓ 已创建 Mock 文生图提供商: {mock_text2image.name}")


def create_real_image2video_provider(ModelProvider, api_url, api_key, model_name):
    """创建真实图生视频提供商。"""
    image2video, created = ModelProvider.objects.get_or_create(
        name='Production Image2Video API',
        defaults={
            'id': uuid.uuid4(),
            'provider_type': 'image2video',
            'executor_class': 'core.ai_client.image2video_client.VideoGeneratorClient',
            'api_url': api_url,
            'api_key': api_key,
            'model_name': model_name,
            'timeout': 180,
            'is_active': True,
            'priority': 1,
            'rate_limit_rpm': 10,
            'rate_limit_rpd': 100,
            'extra_config': {
                'description': '真实图生视频 API，用于生产环境视频生成',
                'is_mock': False,
            }
        }
    )
    if created:
        print(f"✓ 已创建真实图生视频提供商: {image2video.name}")


def create_mock_image2video_provider(ModelProvider):
    """创建 Mock 图生视频提供商。"""
    mock_image2video, created = ModelProvider.objects.get_or_create(
        name='Mock Image2Video API',
        defaults={
            'id': uuid.uuid4(),
            'provider_type': 'image2video',
            'executor_class': 'core.ai_client.mock_image2video_client.MockImage2VideoClient',
            'api_url': 'http://localhost:8010/api/mock',
            'api_key': 'mock-api-key-not-required',
            'model_name': 'mock-image2video-v1',
            'timeout': 120,
            'is_active': True,
            'priority': 100,
            'rate_limit_rpm': 100,
            'rate_limit_rpd': 10000,
            'extra_config': {
                'description': 'Mock 图生视频 API，返回示例视频用于测试',
                'is_mock': True,
                'default_duration': 3.0,
                'default_fps': 24,
            }
        }
    )
    if created:
        print(f"✓ 已创建 Mock 图生视频提供商: {mock_image2video.name}")


def _ensure_default_prompt_template_set():
    """确保存在默认提示词集及其基础模板。"""
    User = apps.get_model('auth', 'User')
    ModelProvider = apps.get_model('models', 'ModelProvider')
    PromptTemplateSet = apps.get_model('prompts', 'PromptTemplateSet')
    PromptTemplate = apps.get_model('prompts', 'PromptTemplate')

    system_user, _ = User.objects.get_or_create(
        username='system',
        defaults={
            'email': 'system@example.com',
            'is_staff': True,
            'is_superuser': False,
        }
    )

    stage_types = [
        'rewrite',
        'asset_extraction',
        'storyboard',
        'image_generation',
        'camera_movement',
        'video_generation',
    ]
    default_template_contents = {
        stage_type: _load_default_prompt_template_content(stage_type)
        for stage_type in stage_types
    }
    default_template_variables = {
        stage_type: _extract_template_variables(default_template_contents[stage_type])
        for stage_type in stage_types
    }
    stage_to_provider_name = {
        'rewrite': 'Production LLM API',
        'asset_extraction': 'Production LLM API',
        'storyboard': 'Production LLM API',
        'image_generation': 'Production Text2Image API',
        'camera_movement': 'Production LLM API',
        'video_generation': 'Production Image2Video API',
    }
    fallback_provider_name = {
        'rewrite': 'Mock LLM API',
        'asset_extraction': 'Mock LLM API',
        'storyboard': 'Mock LLM API',
        'image_generation': 'Mock Text2Image API',
        'camera_movement': 'Mock LLM API',
        'video_generation': 'Mock Image2Video API',
    }
    provider_names = set(stage_to_provider_name.values()) | set(fallback_provider_name.values())
    providers = {
        provider.name: provider
        for provider in ModelProvider.objects.filter(name__in=provider_names, is_active=True)
    }

    with transaction.atomic():
        template_set, _ = PromptTemplateSet.objects.get_or_create(
            name='默认提示词模板集',
            defaults={
                'description': '系统初始化生成的默认提示词模板集,可以参考提示词的写法，可以克隆一份使用，但不要直接应用这份，因为重新部署后会重置里面的配置。',
                'is_active': True,
                'is_default': True,
                'created_by': system_user,
            }
        )

        updated_fields = []
        if not template_set.is_active:
            template_set.is_active = True
            updated_fields.append('is_active')
        if not template_set.is_default:
            template_set.is_default = True
            updated_fields.append('is_default')
        if updated_fields:
            template_set.save(update_fields=updated_fields)

        for stage_type in stage_types:
            model_provider = providers.get(stage_to_provider_name[stage_type])
            if not model_provider:
                model_provider = providers.get(fallback_provider_name[stage_type])
            template, _ = PromptTemplate.objects.get_or_create(
                template_set=template_set,
                stage_type=stage_type,
                defaults={
                    'model_provider': model_provider,
                    'template_content': default_template_contents[stage_type],
                    'variables': default_template_variables[stage_type],
                    'version': 1,
                    'is_active': True,
                }
            )

            template_updated_fields = []
            if model_provider and template.model_provider_id != model_provider.id:
                template.model_provider = model_provider
                template_updated_fields.append('model_provider')
            if not template.template_content and default_template_contents[stage_type]:
                template.template_content = default_template_contents[stage_type]
                template_updated_fields.append('template_content')
            if not template.variables and default_template_variables[stage_type]:
                template.variables = default_template_variables[stage_type]
                template_updated_fields.append('variables')
            if not template.is_active:
                template.is_active = True
                template_updated_fields.append('is_active')
            if template_updated_fields:
                template.save(update_fields=template_updated_fields)


def _load_default_prompt_template_content(stage_type):
    """读取阶段对应的默认提示词模板内容。"""
    template_path = DEFAULT_PROMPT_DIR / f'{stage_type}.md'
    if not template_path.exists():
        return ''
    return template_path.read_text(encoding='utf-8').strip()


def _extract_template_variables(template_content):
    """从 Jinja 模板中提取变量定义。"""
    if not template_content:
        return {}

    env = Environment()
    parsed_content = env.parse(template_content)
    variable_names = sorted(meta.find_undeclared_variables(parsed_content))
    return {variable_name: _infer_variable_type(variable_name) for variable_name in variable_names}


def _infer_variable_type(variable_name):
    """根据变量名推断变量类型。"""
    if variable_name.startswith('is_') or variable_name.startswith('has_'):
        return 'bool'
    if variable_name.endswith('_count') or variable_name.endswith('_index'):
        return 'int'
    if variable_name.endswith('_duration') or variable_name.endswith('_ratio'):
        return 'float'
    if variable_name.endswith('_list') or variable_name.endswith('_items'):
        return 'list'
    if variable_name.endswith('_map') or variable_name.endswith('_dict') or variable_name.endswith('_config'):
        return 'dict'
    return 'string'


def run_post_migrate_initialization(sender, **kwargs):
    """在 migrate 执行完成后触发初始化逻辑。"""
    User = apps.get_model('auth', 'User')
    ModelProvider = apps.get_model('models', 'ModelProvider')
    PromptTemplateSet = apps.get_model('prompts', 'PromptTemplateSet')
    PromptTemplate = apps.get_model('prompts', 'PromptTemplate')

    existing_tables = set(connection.introspection.table_names())

    if ModelProvider._meta.db_table in existing_tables:
        create_providers()

    required_tables = {
        User._meta.db_table,
        ModelProvider._meta.db_table,
        PromptTemplateSet._meta.db_table,
        PromptTemplate._meta.db_table,
    }
    if required_tables.issubset(existing_tables):
        _ensure_default_prompt_template_set()


def _connect_post_migrate_signal():
    post_migrate.connect(
        run_post_migrate_initialization,
        dispatch_uid='apps.projects.post_migrate_initialization',
    )


_connect_post_migrate_signal()
