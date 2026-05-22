import apiClient from '@/services/apiClient';

/**
 * 剧本管理API服务
 */
export default {
  // 剧本 CRUD
  getScreenplays(params) {
    return apiClient.get('/scripts/screenplays/', { params });
  },

  getScreenplayDetail(id) {
    return apiClient.get(`/scripts/screenplays/${id}/`);
  },

  createScreenplay(data) {
    return apiClient.post('/scripts/screenplays/', data);
  },

  updateScreenplay(id, data) {
    return apiClient.patch(`/scripts/screenplays/${id}/`, data);
  },

  deleteScreenplay(id) {
    return apiClient.delete(`/scripts/screenplays/${id}/`);
  },

  // 分集 CRUD
  getEpisodes(screenplayId) {
    return apiClient.get('/scripts/episodes/', {
      params: { screenplay: screenplayId },
    });
  },

  getEpisodeDetail(id) {
    return apiClient.get(`/scripts/episodes/${id}/`);
  },

  createEpisode(data) {
    return apiClient.post('/scripts/episodes/', data);
  },

  updateEpisode(id, data) {
    return apiClient.patch(`/scripts/episodes/${id}/`, data);
  },

  deleteEpisode(id) {
    return apiClient.delete(`/scripts/episodes/${id}/`);
  },
};
