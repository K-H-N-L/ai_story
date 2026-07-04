import json
import re

from apps.prompts.models import PromptTemplate, PromptTemplateSet


PROJECT_STAGE_TYPES = [
    'rewrite',
    'asset_extraction',
    'storyboard',
    'image_generation',
    'multi_grid_image',
    'camera_movement',
    'video_generation',
    'image_edit',
]


def ensure_project_stages(project, stage_types=None):
    """确保项目存在指定阶段记录，兼容旧项目缺失阶段数据的情况。"""
    from .models import ProjectStage

    target_stage_types = stage_types or PROJECT_STAGE_TYPES

    for stage_type in target_stage_types:
        ProjectStage.objects.get_or_create(
            project=project,
            stage_type=stage_type,
            defaults={'status': 'pending'},
        )


def get_effective_prompt_template_set(project):
    """获取项目实际生效的提示词集。"""
    template_set = getattr(project, 'prompt_template_set', None)
    if template_set:
        return template_set

    return PromptTemplateSet.objects.filter(is_default=True).first()




def normalize_stage_template_states(stage_states):
    """标准化阶段启用状态，并处理 image_generation 与 multi_grid/image_edit 的互斥优先级。"""
    normalized = {stage_type: bool(stage_states.get(stage_type, False)) for stage_type in PROJECT_STAGE_TYPES}

    use_advanced_image_flow = normalized.get('multi_grid_image', False) or normalized.get('image_edit', False)
    if use_advanced_image_flow:
        normalized['image_generation'] = False

    return normalized


def get_project_stage_order(stage_states=None):
    """根据阶段启用状态返回实际执行顺序。"""
    normalized = normalize_stage_template_states(stage_states or {stage_type: True for stage_type in PROJECT_STAGE_TYPES})

    stage_order = ['rewrite', 'asset_extraction', 'storyboard']

    if normalized.get('multi_grid_image'):
        stage_order.append('multi_grid_image')
    if normalized.get('image_edit'):
        stage_order.append('image_edit')
    if normalized.get('image_generation'):
        stage_order.append('image_generation')
    if normalized.get('camera_movement'):
        stage_order.append('camera_movement')
    if normalized.get('video_generation'):
        stage_order.append('video_generation')

    return stage_order

def get_stage_template_states(project):
    """返回项目各阶段对应提示词模板是否启用。"""
    template_set = get_effective_prompt_template_set(project)

    if not template_set:
        return {stage_type: False for stage_type in PROJECT_STAGE_TYPES}

    enabled_stage_types = set(
        PromptTemplate.objects.filter(
            template_set=template_set,
            is_active=True,
            stage_type__in=PROJECT_STAGE_TYPES,
        ).values_list('stage_type', flat=True)
    )

    return normalize_stage_template_states({
        stage_type: stage_type in enabled_stage_types
        for stage_type in PROJECT_STAGE_TYPES
    })


def is_stage_template_enabled(project, stage_type: str) -> bool:
    """判断指定阶段的提示词模板是否启用。"""
    return get_stage_template_states(project).get(stage_type, False)


def _extract_json_from_text(text: str) -> str:
        """从文本中提取JSON内容,处理可能包含markdown代码块的情况"""
        text = text.strip()

        if '```' in text:
            match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
            if match:
                text = match.group(1).strip()

        first_brace = text.find('{')
        last_brace = text.rfind('}')
        if first_brace != -1 and last_brace != -1 and first_brace < last_brace:
            text = text[first_brace:last_brace + 1]

        return text

def parse_storyboard_json(json_text: str) -> dict:
    """解析分镜JSON数据"""
    try:
        # 提取纯JSON内容
        clean_json = _extract_json_from_text(json_text)

        # 解析JSON
        storyboard_data = json.loads(clean_json)

        # 验证数据结构
        if 'scenes' not in storyboard_data:
            raise ValueError("JSON数据中缺少 'scenes' 字段")

        if not isinstance(storyboard_data['scenes'], list):
            raise ValueError("'scenes' 必须是数组类型")

        # 验证并补全每个场景的必需字段
        for i, scene in enumerate(storyboard_data['scenes']):
            if not isinstance(scene, dict):
                continue
            if 'scene_number' not in scene:
                scene['scene_number'] = i + 1
            if 'shot_type' not in scene:
                scene['shot_type'] = scene.get('camera_angle', scene.get('shot', 'medium'))
            if 'visual_prompt' not in scene:
                scene['visual_prompt'] = scene.get('description', scene.get('prompt', ''))
            if 'narration' not in scene:
                scene['narration'] = scene.get('dialogue', scene.get('text', ''))

        return storyboard_data

    except json.JSONDecodeError as e:
        raise ValueError(f"JSON解析失败: {str(e)}\n原始内容:\n{json_text[:200]}...")
    except Exception as e:
        raise ValueError(f"分镜数据解析失败: {str(e)}")


def parse_json(json_text: str) -> dict:
    """解析JSON数据"""
    try:
        # 提取纯JSON内容
        clean_json = _extract_json_from_text(json_text)

        # 解析JSON
        data = json.loads(clean_json)

        return data

    except json.JSONDecodeError:
        return json_text
    except Exception:
        return json_text
