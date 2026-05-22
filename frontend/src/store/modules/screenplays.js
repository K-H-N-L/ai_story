import screenplayApi from '@/api/screenplays';

const state = {
  screenplays: [],
  currentScreenplay: null,
  episodes: [],
  pagination: {
    page: 1,
    pageSize: 20,
    total: 0,
  },
  loading: {
    list: false,
    detail: false,
    episodes: false,
  },
};

const getters = {
  screenplayById: (state) => (id) => state.screenplays.find((s) => s.id === id),
};

const mutations = {
  SET_SCREENPLAYS(state, screenplays) {
    state.screenplays = screenplays;
  },
  SET_CURRENT_SCREENPLAY(state, screenplay) {
    state.currentScreenplay = screenplay;
  },
  ADD_SCREENPLAY(state, screenplay) {
    state.screenplays.unshift(screenplay);
  },
  UPDATE_SCREENPLAY(state, screenplay) {
    const index = state.screenplays.findIndex((s) => s.id === screenplay.id);
    if (index !== -1) {
      state.screenplays.splice(index, 1, screenplay);
    }
    if (state.currentScreenplay && state.currentScreenplay.id === screenplay.id) {
      state.currentScreenplay = { ...state.currentScreenplay, ...screenplay };
    }
  },
  REMOVE_SCREENPLAY(state, id) {
    state.screenplays = state.screenplays.filter((s) => s.id !== id);
  },
  SET_EPISODES(state, episodes) {
    state.episodes = episodes;
  },
  ADD_EPISODE(state, episode) {
    state.episodes.push(episode);
    state.episodes.sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0) || a.episode_number - b.episode_number);
    if (state.currentScreenplay) {
      state.currentScreenplay.episodes = [...state.episodes];
    }
  },
  UPDATE_EPISODE(state, episode) {
    const index = state.episodes.findIndex((e) => e.id === episode.id);
    if (index !== -1) {
      state.episodes.splice(index, 1, episode);
    }
    if (state.currentScreenplay && Array.isArray(state.currentScreenplay.episodes)) {
      const epIndex = state.currentScreenplay.episodes.findIndex((e) => e.id === episode.id);
      if (epIndex !== -1) {
        state.currentScreenplay.episodes.splice(epIndex, 1, episode);
      }
    }
  },
  REMOVE_EPISODE(state, id) {
    state.episodes = state.episodes.filter((e) => e.id !== id);
    if (state.currentScreenplay && Array.isArray(state.currentScreenplay.episodes)) {
      state.currentScreenplay.episodes = state.currentScreenplay.episodes.filter((e) => e.id !== id);
    }
  },
  SET_PAGINATION(state, pagination) {
    state.pagination = { ...state.pagination, ...pagination };
  },
  SET_LOADING(state, { key, value }) {
    state.loading[key] = value;
  },
};

const actions = {
  async fetchScreenplays({ commit }, params = {}) {
    commit('SET_LOADING', { key: 'list', value: true });
    try {
      const response = await screenplayApi.getScreenplays(params);
      commit('SET_SCREENPLAYS', response.results || response);
      commit('SET_PAGINATION', {
        total: response.count || 0,
        page: params.page || 1,
      });
      return response;
    } finally {
      commit('SET_LOADING', { key: 'list', value: false });
    }
  },

  async fetchScreenplayDetail({ commit }, id) {
    commit('SET_LOADING', { key: 'detail', value: true });
    try {
      const screenplay = await screenplayApi.getScreenplayDetail(id);
      commit('SET_CURRENT_SCREENPLAY', screenplay);
      if (screenplay.episodes) {
        commit('SET_EPISODES', screenplay.episodes);
      }
      return screenplay;
    } finally {
      commit('SET_LOADING', { key: 'detail', value: false });
    }
  },

  async createScreenplay({ commit }, data) {
    const screenplay = await screenplayApi.createScreenplay(data);
    commit('ADD_SCREENPLAY', screenplay);
    return screenplay;
  },

  async updateScreenplay({ commit }, { id, data }) {
    const screenplay = await screenplayApi.updateScreenplay(id, data);
    commit('UPDATE_SCREENPLAY', screenplay);
    return screenplay;
  },

  async deleteScreenplay({ commit }, id) {
    await screenplayApi.deleteScreenplay(id);
    commit('REMOVE_SCREENPLAY', id);
  },

  async fetchEpisodes({ commit }, screenplayId) {
    commit('SET_LOADING', { key: 'episodes', value: true });
    try {
      const response = await screenplayApi.getEpisodes(screenplayId);
      const episodes = response.results || response;
      commit('SET_EPISODES', episodes);
      return episodes;
    } finally {
      commit('SET_LOADING', { key: 'episodes', value: false });
    }
  },

  async createEpisode({ commit }, data) {
    const episode = await screenplayApi.createEpisode(data);
    commit('ADD_EPISODE', episode);
    return episode;
  },

  async updateEpisode({ commit }, { id, data }) {
    const episode = await screenplayApi.updateEpisode(id, data);
    commit('UPDATE_EPISODE', episode);
    return episode;
  },

  async deleteEpisode({ commit }, id) {
    await screenplayApi.deleteEpisode(id);
    commit('REMOVE_EPISODE', id);
  },

  clearCurrentScreenplay({ commit }) {
    commit('SET_CURRENT_SCREENPLAY', null);
    commit('SET_EPISODES', []);
  },
};

export default {
  namespaced: true,
  state,
  getters,
  mutations,
  actions,
};
