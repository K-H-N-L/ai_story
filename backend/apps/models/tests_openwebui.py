"""
Open WebUI 兼容层测试
"""

import json
from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from .models import ModelProvider, ProviderType, ModelUsageLog

User = get_user_model()


class ModelResolverTest(TestCase):
    """模型解析器测试"""

    def setUp(self):
        from .views_openwebui import ModelResolver
        self.resolver = ModelResolver('http://localhost:3000')

    def test_identify_provider_openai(self):
        """测试 OpenAI 模型识别"""
        provider_id, model_name = self.resolver._identify_provider('gpt-4o')
        self.assertEqual(provider_id, 'openai')
        self.assertEqual(model_name, 'gpt-4o')

    def test_identify_provider_anthropic(self):
        """测试 Anthropic 模型识别"""
        provider_id, model_name = self.resolver._identify_provider('claude-3-5-sonnet-20241022')
        self.assertEqual(provider_id, 'anthropic')

    def test_identify_provider_slash_format(self):
        """测试 provider/model 格式识别"""
        provider_id, model_name = self.resolver._identify_provider('openai/gpt-4o')
        self.assertEqual(provider_id, 'openai')
        self.assertEqual(model_name, 'gpt-4o')

    def test_identify_provider_unknown(self):
        """测试未知模型"""
        provider_id, model_name = self.resolver._identify_provider('my-custom-model')
        self.assertIsNone(provider_id)

    def test_identify_provider_deepseek(self):
        """测试 DeepSeek 模型识别"""
        provider_id, model_name = self.resolver._identify_provider('deepseek-chat')
        self.assertEqual(provider_id, 'deepseek')

    def test_identify_provider_qwen(self):
        """测试 Qwen 模型识别"""
        provider_id, model_name = self.resolver._identify_provider('qwen-max')
        self.assertEqual(provider_id, 'qwen')

    def test_identify_provider_gemini(self):
        """测试 Gemini 模型识别"""
        provider_id, model_name = self.resolver._identify_provider('gemini-1.5-pro')
        self.assertEqual(provider_id, 'gemini')


class ModelMappingAPITest(TestCase):
    """模型映射 API 测试"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)

    def test_list_model_mappings(self):
        """测试获取模型映射列表"""
        ModelProvider.objects.create(
            name='GPT-4',
            provider_type=ProviderType.OPENAI,
            model_name='gpt-4o',
            api_url='https://api.openai.com/v1',
        )

        url = reverse('models:model-mapping-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['model_name'], 'gpt-4o')

    def test_update_model_mapping(self):
        """测试更新模型映射"""
        provider = ModelProvider.objects.create(
            name='GPT-4',
            provider_type=ProviderType.OPENAI,
            model_name='gpt-4o',
            api_url='https://api.openai.com/v1',
        )

        url = reverse('models:model-mapping-detail', args=[provider.id])
        response = self.client.patch(url, {
            'display_name': 'GPT-4 Updated',
            'priority': 100,
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        provider.refresh_from_db()
        self.assertEqual(provider.display_name, 'GPT-4 Updated')
        self.assertEqual(provider.priority, 100)

    def test_toggle_active(self):
        """测试启用/禁用模型"""
        provider = ModelProvider.objects.create(
            name='GPT-4',
            provider_type=ProviderType.OPENAI,
            model_name='gpt-4o',
            api_url='https://api.openai.com/v1',
            is_active=True,
        )

        url = reverse('models:model-mapping-toggle-active', args=[provider.id])

        # 禁用
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        provider.refresh_from_db()
        self.assertFalse(provider.is_active)

        # 重新启用
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        provider.refresh_from_db()
        self.assertTrue(provider.is_active)

    def test_filter_by_provider_type(self):
        """测试按提供商类型过滤"""
        ModelProvider.objects.create(
            name='GPT-4',
            provider_type=ProviderType.OPENAI,
            model_name='gpt-4o',
            api_url='https://api.openai.com/v1',
        )
        ModelProvider.objects.create(
            name='Claude',
            provider_type=ProviderType.ANTHROPIC,
            model_name='claude-3-5-sonnet',
            api_url='https://api.anthropic.com/v1',
        )

        url = reverse('models:model-mapping-list')
        response = self.client.get(url, {'provider_type': 'openai'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['provider_type'], 'openai')


class SyncModelsAPITest(TestCase):
    """模型同步 API 测试"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)

    @patch('apps.models.views_openwebui.requests.get')
    def test_sync_models_success(self, mock_get):
        """测试成功同步模型"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': [
                {'id': 'gpt-4o', 'name': 'GPT-4o'},
                {'id': 'gpt-3.5-turbo', 'name': 'GPT-3.5 Turbo'},
                {'id': 'claude-3-5-sonnet-20241022', 'name': 'Claude 3.5 Sonnet'},
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        url = reverse('models:sync-models-list')
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('stats', response.data)
        self.assertEqual(response.data['stats']['created'], 3)
        self.assertEqual(response.data['stats']['skipped'], 0)

    @patch('apps.models.views_openwebui.requests.get')
    def test_sync_models_partial_skip(self, mock_get):
        """测试部分跳过已存在的模型"""
        # 先创建一个已存在的模型
        ModelProvider.objects.create(
            name='OpenAI GPT-4o',
            provider_type=ProviderType.OPENAI,
            model_name='gpt-4o',
            api_url='https://api.openai.com/v1',
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': [
                {'id': 'gpt-4o', 'name': 'GPT-4o'},
                {'id': 'gpt-3.5-turbo', 'name': 'GPT-3.5 Turbo'},
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        url = reverse('models:sync-models-list')
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['stats']['created'], 1)
        self.assertEqual(response.data['stats']['skipped'], 1)

    @patch('apps.models.views_openwebui.requests.get')
    def test_sync_models_dry_run(self, mock_get):
        """测试 dry-run 模式"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': [
                {'id': 'gpt-4o', 'name': 'GPT-4o'},
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        url = reverse('models:sync-models-list')
        response = self.client.post(url, {'dry_run': True})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['stats']['created'], 1)
        # 确认没有实际创建
        self.assertEqual(ModelProvider.objects.count(), 0)

    @patch('apps.models.views_openwebui.requests.get')
    def test_sync_models_connection_error(self, mock_get):
        """测试连接失败"""
        import requests as http_requests
        mock_get.side_effect = http_requests.ConnectionError('Connection refused')

        url = reverse('models:sync-models-list')
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)


class OpenWebUIModelsViewTest(TestCase):
    """Open WebUI 模型列表接口测试"""

    def setUp(self):
        self.client = APIClient()

    def test_list_models(self):
        """测试获取模型列表"""
        ModelProvider.objects.create(
            name='OpenWebUI/GPT-4o',
            provider_type='openwebui',
            model_name='gpt-4o',
            openwebui_model_id='gpt-4o',
            api_url='http://localhost:3000',
            is_active=True,
        )
        ModelProvider.objects.create(
            name='OpenAI GPT-4',
            provider_type=ProviderType.OPENAI,
            model_name='gpt-4',
            api_url='https://api.openai.com/v1',
            is_active=True,
        )

        url = reverse('models:openwebui-models')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('data', response.data)
        # 只返回 openwebui 类型
        self.assertEqual(len(response.data['data']), 1)
        self.assertEqual(response.data['data'][0]['id'], 'gpt-4o')

    def test_list_models_excludes_inactive(self):
        """测试不返回已禁用的模型"""
        ModelProvider.objects.create(
            name='OpenWebUI/GPT-4o',
            provider_type='openwebui',
            model_name='gpt-4o',
            openwebui_model_id='gpt-4o',
            api_url='http://localhost:3000',
            is_active=False,
        )

        url = reverse('models:openwebui-models')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['data']), 0)


class ModelMappingAPITest2(TestCase):
    """模型映射增强 API 测试"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)

    def test_filter_by_provider_type(self):
        """按提供商类型过滤"""
        ModelProvider.objects.create(
            name='GPT-4',
            provider_type=ProviderType.OPENAI,
            model_name='gpt-4o',
            api_url='https://api.openai.com/v1',
        )
        ModelProvider.objects.create(
            name='Claude',
            provider_type=ProviderType.ANTHROPIC,
            model_name='claude-3-5-sonnet',
            api_url='https://api.anthropic.com/v1',
        )

        url = reverse('models:model-mapping-list')
        response = self.client.get(url, {'provider_type': 'openai'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_filter_by_is_active(self):
        """按启用状态过滤"""
        ModelProvider.objects.create(
            name='GPT-4',
            provider_type=ProviderType.OPENAI,
            model_name='gpt-4o',
            api_url='https://api.openai.com/v1',
            is_active=True,
        )
        ModelProvider.objects.create(
            name='GPT-3.5',
            provider_type=ProviderType.OPENAI,
            model_name='gpt-3.5-turbo',
            api_url='https://api.openai.com/v1',
            is_active=False,
        )

        url = reverse('models:model-mapping-list')
        response = self.client.get(url, {'is_active': 'true'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['model_name'], 'gpt-4o')

    def test_search_models(self):
        """搜索模型"""
        ModelProvider.objects.create(
            name='GPT-4',
            provider_type=ProviderType.OPENAI,
            model_name='gpt-4o',
            api_url='https://api.openai.com/v1',
        )
        ModelProvider.objects.create(
            name='Claude',
            provider_type=ProviderType.ANTHROPIC,
            model_name='claude-3-5-sonnet',
            api_url='https://api.anthropic.com/v1',
        )

        url = reverse('models:model-mapping-list')
        response = self.client.get(url, {'search': 'gpt'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['model_name'], 'gpt-4o')

    def test_bulk_update_active(self):
        """批量更新启用状态"""
        p1 = ModelProvider.objects.create(
            name='GPT-4',
            provider_type=ProviderType.OPENAI,
            model_name='gpt-4o',
            api_url='https://api.openai.com/v1',
            is_active=True,
        )
        p2 = ModelProvider.objects.create(
            name='GPT-3.5',
            provider_type=ProviderType.OPENAI,
            model_name='gpt-3.5-turbo',
            api_url='https://api.openai.com/v1',
            is_active=True,
        )

        url = reverse('models:model-mapping-bulk-update-active')
        response = self.client.post(url, {
            'provider_ids': [str(p1.id), str(p2.id)],
            'is_active': False,
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['updated'], 2)

        p1.refresh_from_db()
        p2.refresh_from_db()
        self.assertFalse(p1.is_active)
        self.assertFalse(p2.is_active)

    def test_toggle_active(self):
        """测试切换启用状态"""
        provider = ModelProvider.objects.create(
            name='GPT-4',
            provider_type=ProviderType.OPENAI,
            model_name='gpt-4o',
            api_url='https://api.openai.com/v1',
            is_active=True,
        )

        url = reverse('models:model-mapping-toggle-active', args=[provider.id])
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        provider.refresh_from_db()
        self.assertFalse(provider.is_active)


class ModelMappingSerializerTest(TestCase):
    """模型映射序列化器测试"""

    def test_validate_openwebui_type(self):
        """验证 openwebui 类型需要 openwebui_model_id"""
        from .serializers import ModelMappingCreateSerializer

        serializer = ModelMappingCreateSerializer(data={
            'name': 'Test',
            'provider_type': 'openwebui',
            'model_name': 'test-model',
            'api_url': 'http://localhost:3000',
            # 缺少 openwebui_model_id
        })

        self.assertFalse(serializer.is_valid())
        self.assertIn('openwebui_model_id', serializer.errors)

    def test_validate_non_openwebui_type(self):
        """验证非 openwebui 类型不需要 openwebui_model_id"""
        from .serializers import ModelMappingCreateSerializer

        serializer = ModelMappingCreateSerializer(data={
            'name': 'GPT-4',
            'provider_type': 'openai',
            'model_name': 'gpt-4o',
            'api_url': 'https://api.openai.com/v1',
        })

        self.assertTrue(serializer.is_valid())


class LoadBalancerTest(TestCase):
    """负载均衡器测试"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.provider1 = ModelProvider.objects.create(
            name='GPT-4 #1',
            provider_type=ProviderType.OPENAI,
            model_name='gpt-4o',
            api_url='https://api.openai.com/v1',
            is_active=True,
            priority=50,
            success_count=100,
            failure_count=5,
        )
        self.provider2 = ModelProvider.objects.create(
            name='GPT-4 #2',
            provider_type=ProviderType.OPENAI,
            model_name='gpt-4o',
            api_url='https://api2.openai.com/v1',
            is_active=True,
            priority=80,
            success_count=50,
            failure_count=0,
        )

    def test_select_by_priority(self):
        """测试按优先级选择"""
        from .load_balancer import ModelLoadBalancer

        balancer = ModelLoadBalancer()
        provider = balancer.select_provider(
            model_name='gpt-4o',
            strategy='priority',
        )

        self.assertIsNotNone(provider)
        # priority 值越小越优先
        self.assertEqual(provider.id, self.provider1.id)

    def test_select_round_robin(self):
        """测试轮询选择"""
        from .load_balancer import ModelLoadBalancer

        balancer = ModelLoadBalancer()
        selections = set()

        for _ in range(4):
            provider = balancer.select_provider(
                model_name='gpt-4o',
                strategy='round_robin',
            )
            selections.add(provider.id)

        # 两次轮询应该两个都被选到
        self.assertEqual(len(selections), 2)

    def test_select_weighted(self):
        """测试加权选择"""
        from .load_balancer import ModelLoadBalancer

        balancer = ModelLoadBalancer()
        provider = balancer.select_provider(
            model_name='gpt-4o',
            strategy='weighted',
        )

        self.assertIsNotNone(provider)
        self.assertIn(provider.id, [self.provider1.id, self.provider2.id])

    def test_select_no_active_provider(self):
        """测试没有活跃 provider"""
        from .load_balancer import ModelLoadBalancer

        ModelProvider.objects.all().update(is_active=False)
        balancer = ModelLoadBalancer()
        provider = balancer.select_provider(model_name='gpt-4o')

        self.assertIsNone(provider)

    def test_report_success(self):
        """测试报告成功"""
        from .load_balancer import ModelLoadBalancer

        balancer = ModelLoadBalancer()
        balancer.report_success(self.provider1)

        self.provider1.refresh_from_db()
        self.assertEqual(self.provider1.success_count, 101)

    def test_report_failure(self):
        """测试报告失败"""
        from .load_balancer import ModelLoadBalancer

        balancer = ModelLoadBalancer()
        balancer.report_failure(self.provider1)

        self.provider1.refresh_from_db()
        self.assertEqual(self.provider1.failure_count, 6)


class AdminTest(TestCase):
    """Admin 测试"""

    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username='admin',
            password='admin123',
            email='admin@test.com'
        )
        self.client.login(username='admin', password='admin123')

    def test_admin_list_display(self):
        """测试 Admin 列表页"""
        ModelProvider.objects.create(
            name='GPT-4',
            provider_type=ProviderType.OPENAI,
            model_name='gpt-4o',
            api_url='https://api.openai.com/v1',
        )

        url = reverse('admin:models_modelprovider_changelist')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
