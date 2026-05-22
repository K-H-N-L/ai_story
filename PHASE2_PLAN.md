# 第二阶段：LinkNow 完整接入 AI 能力 + 画布持久化

> 基于第一阶段（认证 + LLM 代理）已完成，继续推进。

---

## 总体目标

| 方向 | 目标 |
|------|------|
| 文生图接入 | ImageGenNode 调用 AI Story 后端，展示真实生成图片 |
| 图生视频接入 | VideoGenNode 提交任务 + 轮询状态，展示生成视频 |
| 画布持久化 | 节点/连接数据保存到后端，刷新后可恢复 |
| 登录 UI | 前端添加登录/注册页面，未登录时拦截进入画布 |

---

## 架构概览

```
后端 (ai_story/backend)                    前端 (linknow/tapnow-studio)
─────────────────────────────────          ──────────────────────────────
apps/ai_proxy/views.py
  + ImageGenerationsProxyView     ←──────  aiService.generateImage()
  + VideoGenerationsProxyView     ←──────  aiService.generateVideo()
  + VideoTaskStatusView           ←──────  aiService.getVideoTaskStatus()

apps/canvas/ (新建)               ←──────  services/canvasService.js (新建)
  models.py (Canvas)
  views.py (CRUD)
  urls.py

apps/users/views.py (已有)         ←──────  components/auth/LoginPage.jsx (新建)
```

---

## 方向一：文生图接入

### 后端

**修改 `apps/ai_proxy/views.py`** — 新增 `ImageGenerationsProxyView`：

```python
class ImageGenerationsProxyView(APIView):
    """POST /api/v1/ai/images/generations"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        prompt = request.data.get('prompt', '')
        model = request.data.get('model', '')
        size = request.data.get('size', '1024x1024')
        n = request.data.get('n', 1)
        negative_prompt = request.data.get('negative_prompt', '')

        # 按 model_name 精确匹配，找不到取优先级最高的 text2image provider
        provider = (
            ModelProvider.objects.filter(
                provider_type='text2image', is_active=True, model_name=model
            ).order_by('-priority').first()
            or ModelProvider.objects.filter(
                provider_type='text2image', is_active=True
            ).order_by('-priority').first()
        )
        if not provider:
            return Response({'error': '没有可用的文生图提供商'}, status=503)

        client = create_ai_client(provider)

        # 解析 size 字段 "1024x1024" → width=1024, height=1024
        try:
            width, height = (int(x) for x in size.split('x'))
        except Exception:
            width, height = 1024, 1024

        response = client.generate(
            prompt=prompt,
            negative_prompt=negative_prompt,
            width=width,
            height=height,
            sample_count=n,
        )

        if not response.success:
            return Response({'error': response.error}, status=502)

        return Response({
            'created': int(time.time()),
            'data': response.data,  # [{'url': '...', 'width': ..., 'height': ...}]
        })
```

**修改 `apps/ai_proxy/urls.py`** — 新增路由：

```python
path('images/generations', ImageGenerationsProxyView.as_view(), name='image-generations'),
```

### 前端

**修改 `src/services/aiService.js`** — 更新 `generateImage()`：

```js
export const generateImage = async (prompt, model, options = {}) => {
  if (model.startsWith('jimeng')) {
    return await jimengApi.post('/generate', { prompt, model, ...options });
  }
  const { negativePrompt, size = '1024x1024', n = 1 } = options;
  return await aiStoryApi.post('/api/v1/ai/images/generations', {
    prompt,
    model,
    size,
    n,
    negative_prompt: negativePrompt,
  });
};
```

**修改 `src/components/canvas/nodes/ImageGenNode.jsx`** — 替换 `setTimeout` 模拟为真实调用：

```jsx
const handleGenerate = async () => {
  if (!prompt) return;
  setIsGenerating(true);
  onDataChange?.({ ...data, status: 'running' });
  try {
    const result = await generateImage(prompt, model, { negativePrompt, size, n: 1 });
    const imageUrl = result?.data?.[0]?.url || '';
    onDataChange?.({ ...data, status: 'success', generatedImage: imageUrl });
  } catch (err) {
    onDataChange?.({ ...data, status: 'error', error: err.message });
  } finally {
    setIsGenerating(false);
  }
};
```

> 注意：确认 `LazyBase64Image` 是否支持普通 URL，如不支持改用 `<img>` 标签。

---

## 方向二：图生视频接入

视频生成耗时长，采用**提交任务 → 前端轮询**方案。

### 后端

**修改 `apps/ai_proxy/views.py`** — 新增两个视图：

```python
class VideoGenerationsProxyView(APIView):
    """POST /api/v1/ai/videos/generations — 提交视频生成任务"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        prompt = request.data.get('prompt', '')
        model = request.data.get('model', '')
        image_url = request.data.get('image', '')
        duration = request.data.get('duration', 5)

        provider = ModelProvider.objects.filter(
            provider_type='image2video', is_active=True
        ).order_by('-priority').first()
        if not provider:
            return Response({'error': '没有可用的图生视频提供商'}, status=503)

        # VideoGeneratorClient 不走 create_ai_client 工厂，直接实例化
        from core.ai_client.image2video_client import VideoGeneratorClient
        client = VideoGeneratorClient(
            api_url=provider.api_url,
            api_key=provider.api_key,
            model=provider.model_name,
        )

        try:
            task_result = client.create_video_task(
                prompt=prompt,
                model=model or provider.model_name,
                image_uri=image_url,
                duration_seconds=duration,
            )
            # 如果直接返回了视频列表（同步接口）
            if isinstance(task_result, list):
                return Response({'status': 'completed', 'data': task_result})
            # 返回 task_id 供前端轮询
            return Response({'status': 'pending', 'task_id': task_result}, status=202)
        except Exception as e:
            return Response({'error': str(e)}, status=500)


class VideoTaskStatusView(APIView):
    """GET /api/v1/ai/videos/tasks/<task_id> — 查询任务状态"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, task_id):
        provider = ModelProvider.objects.filter(
            provider_type='image2video', is_active=True
        ).order_by('-priority').first()

        from core.ai_client.image2video_client import VideoGeneratorClient
        client = VideoGeneratorClient(
            api_url=provider.api_url,
            api_key=provider.api_key,
            model=provider.model_name,
        )
        try:
            return Response(client.get_task_status(task_id))
        except Exception as e:
            return Response({'error': str(e)}, status=500)
```

**修改 `apps/ai_proxy/urls.py`** — 新增路由：

```python
path('videos/generations', VideoGenerationsProxyView.as_view(), name='video-generations'),
path('videos/tasks/<str:task_id>', VideoTaskStatusView.as_view(), name='video-task-status'),
```

> ⚠️ 注意：`VideoGeneratorClient` 不继承 `BaseAIClient`，无法通过 `create_ai_client()` 工厂创建，需直接实例化。实施前先确认 `core/ai_client/image2video_client.py` 中 `create_video_task` 和 `get_task_status` 的方法签名。

### 前端

**修改 `src/services/aiService.js`** — 更新 `generateVideo()`，新增 `getVideoTaskStatus()`：

```js
export const generateVideo = async (prompt, model, options = {}) => {
  const { imageUrl, duration = 5 } = options;
  return await aiStoryApi.post('/api/v1/ai/videos/generations', {
    prompt, model, image: imageUrl, duration,
  });
};

export const getVideoTaskStatus = async (taskId) => {
  return await aiStoryApi.get(`/api/v1/ai/videos/tasks/${taskId}`);
};
```

**修改 `src/components/canvas/nodes/VideoGenNode.jsx`** — 替换模拟逻辑：

```jsx
const handleGenerate = async () => {
  setIsGenerating(true);
  try {
    const result = await generateVideo(prompt, model, {
      imageUrl: data.inputImage,
      duration: parseInt(duration),
    });
    if (result.status === 'completed') {
      onDataChange?.({ ...data, status: 'success', generatedVideo: result.data[0]?.url });
      setIsGenerating(false);
    } else if (result.task_id) {
      pollVideoTask(result.task_id);
    }
  } catch (err) {
    onDataChange?.({ ...data, status: 'error', error: err.message });
    setIsGenerating(false);
  }
};

const pollVideoTask = (taskId) => {
  const interval = setInterval(async () => {
    try {
      const status = await getVideoTaskStatus(taskId);
      const taskStatus = status?.status || status?.data?.status;
      if (taskStatus === 'SUCCESS' || taskStatus === 'Completed') {
        clearInterval(interval);
        onDataChange?.({ ...data, status: 'success', generatedVideo: status?.data?.videos?.[0]?.url });
        setIsGenerating(false);
      } else if (taskStatus === 'Failed') {
        clearInterval(interval);
        onDataChange?.({ ...data, status: 'error', error: '视频生成失败' });
        setIsGenerating(false);
      }
    } catch {
      clearInterval(interval);
      setIsGenerating(false);
    }
  }, 5000);
};
```

---

## 方向三：画布持久化

### 后端 — 新建 `apps/canvas` app

**新建文件列表：**

```
backend/apps/canvas/
├── __init__.py
├── apps.py
├── models.py
├── serializers.py
├── views.py
└── urls.py
```

**`apps/canvas/models.py`**

```python
import uuid
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Canvas(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='canvases')
    name = models.CharField('画布名称', max_length=255, default='未命名项目')
    # 存储完整画布状态：{ nodes: [...], connections: [...], view: {...} }
    canvas_data = models.JSONField('画布数据', default=dict)
    thumbnail = models.TextField('缩略图', blank=True, default='')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'linknow_canvases'
        ordering = ['-updated_at']
        indexes = [models.Index(fields=['user', '-updated_at'])]
```

**`apps/canvas/serializers.py`**

```python
from rest_framework import serializers
from .models import Canvas

class CanvasSerializer(serializers.ModelSerializer):
    class Meta:
        model = Canvas
        fields = ['id', 'name', 'canvas_data', 'thumbnail', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

class CanvasListSerializer(serializers.ModelSerializer):
    """列表接口不返回 canvas_data，减少传输量"""
    node_count = serializers.SerializerMethodField()

    class Meta:
        model = Canvas
        fields = ['id', 'name', 'node_count', 'thumbnail', 'created_at', 'updated_at']

    def get_node_count(self, obj):
        return len(obj.canvas_data.get('nodes', []))
```

**`apps/canvas/views.py`**

```python
from rest_framework import generics, permissions
from .models import Canvas
from .serializers import CanvasSerializer, CanvasListSerializer

class CanvasListCreateView(generics.ListCreateAPIView):
    """GET /api/v1/canvas/ — 列表; POST — 新建"""
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Canvas.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        return CanvasListSerializer if self.request.method == 'GET' else CanvasSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class CanvasDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET/PUT/PATCH/DELETE /api/v1/canvas/<id>/"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CanvasSerializer

    def get_queryset(self):
        return Canvas.objects.filter(user=self.request.user)
```

**`apps/canvas/urls.py`**

```python
from django.urls import path
from .views import CanvasListCreateView, CanvasDetailView

urlpatterns = [
    path('', CanvasListCreateView.as_view(), name='canvas-list'),
    path('<uuid:pk>/', CanvasDetailView.as_view(), name='canvas-detail'),
]
```

**修改 `config/settings/base.py`** — INSTALLED_APPS 添加 `'apps.canvas'`

**修改 `config/urls.py`** — 添加：

```python
path('api/v1/canvas/', include('apps.canvas.urls')),
```

**执行迁移：**

```bash
cd backend && uv run python manage.py makemigrations canvas && uv run python manage.py migrate
```

### 前端

**新建 `src/services/canvasService.js`**

```js
import { aiStoryApi } from './api';

const BASE = '/api/v1/canvas';

export const listCanvases = () => aiStoryApi.get(`${BASE}/`);
export const createCanvas = (name, canvasData, thumbnail = '') =>
  aiStoryApi.post(`${BASE}/`, { name, canvas_data: canvasData, thumbnail });
export const getCanvas = (id) => aiStoryApi.get(`${BASE}/${id}/`);
export const updateCanvas = (id, data) => aiStoryApi.put(`${BASE}/${id}/`, data);
export const deleteCanvas = (id) => aiStoryApi.delete(`${BASE}/${id}/`);
```

**修改 `src/App.jsx`** — 集成云端保存：

1. 引入 `canvasService`，新增 `canvasId` state
2. 登录后自动加载最近的画布（`listCanvases()` 取第一条）
3. `nodes`/`connections` 变化时，防抖 2 秒后调用 `updateCanvas(canvasId, { canvas_data: { nodes, connections } })`
4. 首次保存（`canvasId` 为空）时调用 `createCanvas(projectName, { nodes, connections })`

---

## 方向四：登录 UI

### 新建 `src/components/auth/LoginPage.jsx`

全屏居中卡片，风格与现有 Modal 一致（zinc 色系，暗色主题）：

```jsx
const LoginPage = ({ theme = 'dark' }) => {
  const [mode, setMode] = useState('login');  // 'login' | 'register'
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const { login, register } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);
    try {
      if (mode === 'login') {
        await login(username, password);
      } else {
        await register(username, email, password);
        await login(username, password);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  // 渲染：Logo + 标题 + 表单 + 切换登录/注册链接
};
```

### 修改 `src/App.jsx` — 登录门控

将主内容提取为 `AppContent` 组件，根据认证状态决定渲染：

```jsx
// App.jsx 内部
const AppContent = () => {
  const { isAuthenticated, isLoading } = useAuth();
  if (isLoading) return <LoadingScreen />;
  if (!isAuthenticated) return <LoginPage theme={theme} />;
  return (/* 原有 Header + Sidebar + NodeEditor + ChatPanel 布局 */);
};
```

### 修改 `src/components/common/UserSettingsModal.jsx` — 登出按钮

```jsx
const { logout } = useAuth();
// 登出按钮 onClick 接入
<button onClick={logout}>登出账号</button>
```

---

## 实施顺序

```
第1步（~1天）：后端 images/generations + 前端 ImageGenNode 接入
第2步（~1天）：后端 videos/generations + tasks + 前端 VideoGenNode 接入
第3步（~1.5天）：后端 apps/canvas（模型+序列化+视图+URL+迁移）
第4步（~1天）：前端 canvasService + App.jsx 云端保存集成
第5步（~0.5天）：前端 LoginPage + 登录门控 + UserSettingsModal 登出
```

---

## 关键注意事项

1. **`VideoGeneratorClient` 不走工厂**：该客户端不继承 `BaseAIClient`，需直接实例化，实施前先确认 `core/ai_client/image2video_client.py` 的方法签名。

2. **图片 URL 跨域**：后端返回 `http://localhost:8000/storage/image/...`，`<img>` 标签直接加载无跨域问题。若 `LazyBase64Image` 内部用 fetch 加载，需确认 CORS 配置覆盖 `storage/` 路径。

3. **画布防抖保存**：节点变化频繁，防抖时间建议 2 秒，避免频繁写库。

4. **登录状态与画布加载竞态**：`AuthContext` 初始化时异步验证 token，`isLoading = true` 期间不触发画布加载，等 `isAuthenticated = true` 后再加载。

5. **`text2image` 客户端的 `generate()` 方法**：不同执行器（`OpenAIImagesGenerationExecutor`、`ChatCompletionsImageExecutor` 等）的 `generate()` 参数可能不同，实施前先确认目标执行器的方法签名。

---

## 验证方式

```bash
# 文生图
curl -X POST http://localhost:8000/api/v1/ai/images/generations \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"a cat","size":"1024x1024","n":1}'

# 图生视频（提交任务）
curl -X POST http://localhost:8000/api/v1/ai/videos/generations \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"a cat walking","duration":5}'

# 查询任务状态
curl http://localhost:8000/api/v1/ai/videos/tasks/<task_id> \
  -H "Authorization: Bearer <token>"

# 画布 CRUD
curl -X POST http://localhost:8000/api/v1/canvas/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"name":"测试画布","canvas_data":{"nodes":[],"connections":[]}}'
```
