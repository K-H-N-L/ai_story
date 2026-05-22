const stageLabelMap = {
  rewrite: '改写',
  asset_extraction: '资产提取',
  storyboard: '分镜',
  image_generation: '图片生成',
  multi_grid_image: '多图生成',
  image_edit: '图片编辑',
  camera_movement: '运镜',
  video_generation: '视频生成',
};

const getStageLabel = (stageType) => stageLabelMap[stageType] || stageType || '未知阶段';

const getProjectDetailHeadline = ({ project, stages }) => {
  const failedStage = stages.find((stage) => stage.status === 'failed');
  const processingStage = stages.find((stage) => stage.status === 'processing');

  if (processingStage) {
    return `当前正在执行 ${getStageLabel(processingStage.stage_type)} 阶段。`;
  }

  if (failedStage) {
    return `${getStageLabel(failedStage.stage_type)} 阶段存在失败记录，建议优先定位。`;
  }

  if (project?.status === 'completed') {
    return '当前项目流程已完成，可以回看并微调内容。';
  }

  if (project?.status === 'paused') {
    return '当前项目已暂停，可继续恢复流程或局部调整。';
  }

  return '当前项目处于可编辑状态，可以继续执行或微调。';
};

export const buildFallbackPageAgentContext = (route) => ({
  scopeKey: `route:${route.name || route.path}`,
  pageType: 'generic',
  title: route.meta?.title || '当前页面',
  subtitle: '页面助手',
  summary: '我会结合当前页面进度，帮你判断下一步，并引导你使用合适的功能入口。',
  quickActions: [
    '我现在适合先做什么？',
    '推荐我下一步该用哪个入口',
  ],
  capabilities: [],
  meta: {
    routeName: route.name || '',
    path: route.fullPath || route.path,
  },
});

export const buildProjectDetailAgentContext = ({ route, project, stages = [], seriesEpisodes = [] }) => {
  const completedStages = stages.filter((stage) => stage.status === 'completed').length;
  const failedStages = stages.filter((stage) => stage.status === 'failed');
  const processingStage = stages.find((stage) => stage.status === 'processing') || null;
  const pausedStages = stages.filter((stage) => stage.status === 'paused').length;
  const storyboardStage = stages.find((stage) => stage.stage_type === 'storyboard') || null;
  const storyboards = storyboardStage?.domain_data?.storyboards || [];
  const cameraReadyCount = storyboards.filter((item) => item.camera_movement?.data?.id).length;

  return {
    scopeKey: `project_detail:${project?.id || route.params.id}`,
    pageType: 'project_detail',
    title: project?.display_name || project?.name || '分集详情',
    subtitle: project?.series_name || '项目画布',
    summary: getProjectDetailHeadline({ project, stages }),
    quickActions: [
      '我现在最适合推进哪一步？',
      '推荐我下一步操作',
      '带我去分镜阶段',
      '打开第一个分镜的助手',
    ],
    capabilities: [
      'focus_stage',
      'focus_storyboard',
      'open_storyboard_chat',
      'open_camera_chat',
      'run_pipeline',
      'pause_pipeline',
      'resume_pipeline',
      'refresh_canvas',
    ],
    stats: {
      totalStages: stages.length,
      completedStages,
      failedStages: failedStages.length,
      pausedStages,
      storyboardCount: storyboards.length,
      cameraReadyCount,
      episodeCount: seriesEpisodes.length,
    },
    entities: {
      projectId: project?.id || null,
      projectStatus: project?.status || 'draft',
      processingStage: processingStage?.stage_type || '',
      failedStage: failedStages[0]?.stage_type || '',
      firstStoryboardId: storyboards[0]?.id || null,
      firstCameraId: storyboards.find((item) => item.camera_movement?.data?.id)?.camera_movement?.data?.id || null,
      firstCameraStoryboardId: storyboards.find((item) => item.camera_movement?.data?.id)?.id || null,
    },
    meta: {
      routeName: route.name || '',
      path: route.fullPath || route.path,
      stageNames: stages.map((stage) => stage.stage_type),
    },
  };
};
