"""
Mock LLM 客户端实现
用于测试和开发环境，返回模拟的 LLM 响应
"""

import time
import json
from typing import Dict, Any, Generator
from .base import LLMClient, AIResponse


class MockLLMClient(LLMClient):
    """
    Mock LLM 客户端
    返回预定义的模拟响应，用于测试工作流
    """

    # 模拟响应模板
    MOCK_RESPONSES = {
        "rewrite": """{
    "story_title": "小画家的梦想",
    "rewritten_text": "在一个宁静的小镇上，住着一位年轻的画家。每天清晨，他都会来到河边，用画笔记录下大自然的美丽瞬间。这个故事讲述了艺术与生活的完美融合，展现了一个追梦者的日常。通过细腻的笔触，我们看到了他对艺术的执着追求。",
    "highlights": [
        "宁静小镇的自然风光",
        "画家对艺术的执着追求",
        "日常生活中的艺术灵感"
    ]
}""",

        "storyboard": """{
    "scenes": [
      {
        "scene_number": 1,
        "narration": "一只可爱的小猫站在森林入口，好奇地望着前方茂密的树林，阳光透过树叶洒在它身上。",
        "visual_prompt": "场景描述:神秘森林的入口处，古老的大树参天而立，阳光透过树叶的缝隙洒下斑驳的光影，地面铺满了绿色的苔藓和落叶。远景是深邃的森林，隐约可见一条蜿蜒的小径。 主体刻画:一只可爱的橙色小猫，毛茸茸的身体，大大的眼睛闪烁着好奇的光芒，站立在一块大石头上，前爪轻轻抬起。 风格落地:3D皮克斯风格 光影与质感:温暖的阳光洒在小猫身上，照亮了它橙色的毛发，形成柔和的光影效果。 视角与构图:中景视角，小猫位于画面中央，森林作为背景。 光线描述:阳光从画面上方斜射下来，营造出神秘而温暖的氛围。",
        "shot_type": "中景"
      },
      {
        "scene_number": 2,
        "narration": "小猫在森林中遇到了一只友好的松鼠，松鼠正在树枝上吃坚果。",
        "visual_prompt": "场景描述:森林深处，高大的橡树和松树环绕，树枝上挂满了松果和坚果。地面有一些野花点缀。 主体刻画:小猫抬头看着树上的松鼠，松鼠坐在树枝上，嘴里叼着一颗坚果，尾巴蓬松地翘起。 风格落地:3D皮克斯风格 光影与质感:柔和的森林光线，透过树叶的光斑洒在动物们身上。 视角与构图:近景视角，聚焦小猫和松鼠的互动。 光线描述:自然光从树冠上方洒落，营造出宁静的森林氛围。",
        "shot_type": "近景"
      },
      {
        "scene_number": 3,
        "narration": "小猫和松鼠一起在森林中探险，穿过一条小溪，水面倒映着蓝天。",
        "visual_prompt": "场景描述:森林中的小溪，清澈的水流潺潺流过，水面倒映着蓝天和树木的影子。溪边有一些鹅卵石和野花。 主体刻画:小猫小心翼翼地跨过小溪中的石头，松鼠在旁边的树枝上陪伴着它。 风格落地:3D皮克斯风格 光影与质感:水面波光粼粼，阳光在水面上形成闪烁的光点。 视角与构图:全景视角，展现森林小溪的美丽景色。 光线描述:明亮的阳光照射在小溪上，波光粼粼。",
        "shot_type": "全景"
      }
    ]
}""",

        "camera_movement": """{
  "movement_type": "zoom_in",
  "movement_params": {
      "description": "缓慢推进镜头，聚焦主体"
  }
}""",

        "default": """这是一个模拟的 LLM 响应。

在实际使用中，这里会返回根据提示词生成的真实内容。Mock API 主要用于：
1. 开发环境的快速测试
2. 工作流程的验证
3. 前端界面的调试
4. 成本控制（避免频繁调用真实 API）

请在生产环境中配置真实的 LLM 服务。"""
    }

    async def _generate_text(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float,
        **kwargs
    ) -> AIResponse:
        """
        生成模拟的文本响应

        Args:
            prompt: 输入提示词
            max_tokens: 最大token数（Mock中忽略）
            temperature: 温度参数（Mock中忽略）
            **kwargs: 其他参数

        Returns:
            AIResponse: 模拟响应对象
        """
        start_time = time.time()

        # 模拟API延迟
        time.sleep(0.5)

        # 根据提示词内容判断响应类型
        response_text = self._get_mock_response(prompt)

        # 模拟token使用量
        tokens_used = len(response_text) // 4  # 粗略估算

        latency_ms = int((time.time() - start_time) * 1000)

        return AIResponse(
            success=True,
            text=response_text,
            metadata={
                'tokens_used': tokens_used,
                'latency_ms': latency_ms,
                'model': self.model_name,
                'is_mock': True
            }
        )

    def generate_stream(
        self,
        prompt: str,
        system_prompt: str = "",
        max_tokens: int = 2000,
        temperature: float = 0.7,
        **kwargs
    ) -> Generator[Dict[str, Any], None, None]:
        """
        流式生成模拟文本

        Args:
            prompt: 输入提示词
            system_prompt: 系统提示词
            max_tokens: 最大token数
            temperature: 温度参数
            **kwargs: 其他参数

        Yields:
            Dict包含: type (token/done/error), content, metadata
        """
        start_time = time.time()

        stage_type = kwargs.get('stage_type')
        response_text = self._get_mock_response(system_prompt, stage_type)

        # 模拟流式输出，每次返回几个字符
        chunk_size = 10
        full_text = ""

        for i in range(0, len(response_text), chunk_size):
            chunk = response_text[i:i + chunk_size]
            full_text += chunk

            # 模拟网络延迟
            time.sleep(0.05)

            yield {
                'type': 'token',
                'content': chunk,
                'full_text': full_text
            }

        # 发送完成信号
        latency_ms = int((time.time() - start_time) * 1000)

        yield {
            'type': 'done',
            'full_text': full_text,
            'metadata': {
                'latency_ms': latency_ms,
                'model': self.model_name,
                'finish_reason': 'stop',
                'is_mock': True
            }
        }

    def _get_mock_response(self, prompt: str, stage_type: str = None) -> str:
        """
        根据提示词内容或阶段类型返回相应的模拟响应

        Args:
            prompt: 输入提示词
            stage_type: 阶段类型 ('rewrite'|'storyboard'|'camera_movement'|'asset_extraction')

        Returns:
            str: 模拟响应文本
        """
        if stage_type:
            stage_type_lower = stage_type.lower()
            if stage_type_lower == 'rewrite':
                return self.MOCK_RESPONSES['rewrite']
            elif stage_type_lower == 'storyboard':
                return self.MOCK_RESPONSES['storyboard']
            elif stage_type_lower == 'camera_movement':
                return self.MOCK_RESPONSES['camera_movement']
            elif stage_type_lower == 'asset_extraction':
                return """{
  "summary": "从剧本中提取的关键资产",
  "items": [
    {
      "name": "小猫",
      "type": "character",
      "description": "勇敢的小猫主角"
    },
    {
      "name": "神秘森林",
      "type": "scene",
      "description": "故事发生的主要场景"
    },
    {
      "name": "动物朋友",
      "type": "character",
      "description": "小猫在森林中遇到的各种动物"
    }
  ]
}"""

        prompt_lower = prompt.lower()

        # 根据关键词判断响应类型
        if any(keyword in prompt_lower for keyword in ['改写', 'rewrite', '润色', '优化文案']):
            return self.MOCK_RESPONSES['rewrite']
        elif any(keyword in prompt_lower for keyword in ['分镜', 'storyboard']):
            return self.MOCK_RESPONSES['storyboard']
        elif any(keyword in prompt_lower for keyword in ['运镜', 'camera', '镜头', 'movement']):
            return self.MOCK_RESPONSES['camera_movement']
        else:
            return self.MOCK_RESPONSES['storyboard']

    async def validate_config(self) -> bool:
        """
        验证配置（Mock客户端始终返回True）

        Returns:
            bool: 始终返回True
        """
        return True

    async def health_check(self) -> bool:
        """
        健康检查（Mock客户端始终返回True）

        Returns:
            bool: 始终返回True
        """
        return True
