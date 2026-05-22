<template>
  <div class="page-shell">
    <div class="page-header">
      <div class="page-header-main">
        <h1 class="page-title">
          剧本管理
        </h1>
        <p class="page-subtitle">
          {{ pagination.total }} 个剧本
        </p>
      </div>
      <button
        class="primary-action"
        @click="showCreateDialog = true"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          stroke-width="1.5"
          stroke="currentColor"
          class="w-5 h-5"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            d="M12 4.5v15m7.5-7.5h-15"
          />
        </svg>
        <span>新建剧本</span>
      </button>
    </div>

    <div class="filter-card">
      <div class="search-box">
        <svg
          class="search-icon"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
          />
        </svg>
        <input
          v-model="filters.search"
          type="text"
          placeholder="搜索剧本..."
          class="search-input"
          @keyup.enter="handleFilter"
        >
      </div>

      <div class="status-filters">
        <button
          v-for="status in statusOptions"
          :key="status.value"
          :class="['status-filter-btn', { active: filters.status === status.value }]"
          @click="handleStatusFilter(status.value)"
        >
          {{ status.label }}
        </button>
      </div>
    </div>

    <LoadingContainer :loading="loading">
      <div
        v-if="!loading && screenplays.length === 0"
        class="empty-state"
      >
        <div class="empty-hero">
          暂无剧本
        </div>
        <p class="empty-hint">
          创建您的第一个剧本，开始编写分集文案。
        </p>
        <button
          class="secondary-action"
          @click="showCreateDialog = true"
        >
          创建剧本
        </button>
      </div>

      <div
        v-else
        class="card-grid"
      >
        <article
          v-for="screenplay in screenplays"
          :key="screenplay.id"
          class="data-card"
          role="button"
          tabindex="0"
          @click="handleView(screenplay.id)"
          @keyup.enter="handleView(screenplay.id)"
        >
          <div class="card-top">
            <div>
              <h2 class="card-title">
                {{ screenplay.title }}
              </h2>
              <p class="card-desc">
                {{ screenplay.description || '暂无描述' }}
              </p>
            </div>
            <span class="status-pill">{{ screenplay.status_display }}</span>
          </div>

          <div class="card-meta">
            <div class="meta-item">
              <span class="meta-label">分集数</span>
              <span class="meta-value">{{ screenplay.episodes_count || 0 }}</span>
            </div>
            <div class="meta-item">
              <span class="meta-label">创建时间</span>
              <span class="meta-value">{{ formatDate(screenplay.created_at) }}</span>
            </div>
          </div>

          <div class="card-footer">
            <span class="meta-time">更新于 {{ formatDate(screenplay.updated_at) }}</span>
            <div class="project-card-actions">
              <button
                class="project-card-action"
                @click.stop="handleEdit(screenplay)"
              >
                编辑
              </button>
              <button
                class="project-card-action project-card-action--danger"
                :disabled="deletingId === screenplay.id"
                @click.stop="handleDelete(screenplay)"
              >
                {{ deletingId === screenplay.id ? '删除中...' : '删除' }}
              </button>
            </div>
          </div>
        </article>
      </div>
    </LoadingContainer>

    <!-- 新建/编辑剧本弹窗 -->
    <div
      v-if="showCreateDialog || showEditDialog"
      class="modal-overlay"
      @click.self="closeDialogs"
    >
      <div class="modal-card">
        <h3 class="modal-title">
          {{ showEditDialog ? '编辑剧本' : '新建剧本' }}
        </h3>
        <form @submit.prevent="handleSubmit">
          <div class="form-group">
            <label class="form-label">剧本标题</label>
            <input
              v-model="form.title"
              type="text"
              class="form-input"
              placeholder="请输入剧本标题"
              required
            >
          </div>
          <div class="form-group">
            <label class="form-label">剧本描述</label>
            <textarea
              v-model="form.description"
              class="form-textarea"
              placeholder="请输入剧本描述（可选）"
              rows="3"
            />
          </div>
          <div class="form-group">
            <label class="form-label">状态</label>
            <select
              v-model="form.status"
              class="form-select"
            >
              <option value="draft">
                草稿
              </option>
              <option value="in_progress">
                进行中
              </option>
              <option value="completed">
                已完成
              </option>
              <option value="archived">
                已归档
              </option>
            </select>
          </div>
          <div class="modal-actions">
            <button
              type="button"
              class="btn-cancel"
              @click="closeDialogs"
            >
              取消
            </button>
            <button
              type="submit"
              class="btn-confirm"
              :disabled="submitting"
            >
              {{ submitting ? '保存中...' : '保存' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script>
import { mapState, mapActions } from 'vuex';
import LoadingContainer from '@/components/common/LoadingContainer.vue';
import { formatDate } from '@/utils/helpers';

export default {
  name: 'ScreenplayList',
  components: { LoadingContainer },
  data() {
    return {
      loading: false,
      deletingId: null,
      submitting: false,
      showCreateDialog: false,
      showEditDialog: false,
      editingId: null,
      filters: {
        search: '',
        status: '',
      },
      form: {
        title: '',
        description: '',
        status: 'draft',
      },
      statusOptions: [
        { value: '', label: '全部' },
        { value: 'draft', label: '草稿' },
        { value: 'in_progress', label: '进行中' },
        { value: 'completed', label: '已完成' },
        { value: 'archived', label: '已归档' },
      ],
    };
  },
  computed: {
    ...mapState('screenplays', ['screenplays', 'pagination']),
  },
  created() {
    this.fetchData();
  },
  methods: {
    ...mapActions('screenplays', ['fetchScreenplays', 'createScreenplay', 'updateScreenplay', 'deleteScreenplay']),
    formatDate,
    async fetchData(page = this.pagination.page) {
      this.loading = true;
      try {
        await this.fetchScreenplays({
          page,
          page_size: this.pagination.pageSize,
          search: this.filters.search,
          status: this.filters.status,
        });
      } finally {
        this.loading = false;
      }
    },
    handleFilter() {
      this.fetchData(1);
    },
    handleStatusFilter(status) {
      this.filters.status = status;
      this.handleFilter();
    },
    handleView(id) {
      this.$router.push({ name: 'ScreenplayDetail', params: { id } });
    },
    handleEdit(screenplay) {
      this.editingId = screenplay.id;
      this.form = {
        title: screenplay.title,
        description: screenplay.description || '',
        status: screenplay.status,
      };
      this.showEditDialog = true;
    },
    async handleDelete(screenplay) {
      const confirmed = await this.$confirm(
        `确定删除剧本「${screenplay.title}」吗？此操作不可恢复。`,
        '删除剧本',
        { tone: 'danger', confirmText: '删除' }
      );
      if (!confirmed) return;

      this.deletingId = screenplay.id;
      try {
        await this.deleteScreenplay(screenplay.id);
        this.$message.success('剧本已删除');
      } catch (error) {
        console.error('Failed to delete screenplay:', error);
        this.$message.error('删除剧本失败');
      } finally {
        this.deletingId = null;
      }
    },
    async handleSubmit() {
      this.submitting = true;
      try {
        if (this.showEditDialog) {
          await this.updateScreenplay({ id: this.editingId, data: this.form });
          this.$message.success('剧本已更新');
        } else {
          await this.createScreenplay(this.form);
          this.$message.success('剧本已创建');
        }
        this.closeDialogs();
      } catch (error) {
        console.error('Failed to save screenplay:', error);
        this.$message.error('保存剧本失败');
      } finally {
        this.submitting = false;
      }
    },
    closeDialogs() {
      this.showCreateDialog = false;
      this.showEditDialog = false;
      this.editingId = null;
      this.form = { title: '', description: '', status: 'draft' };
    },
  },
};
</script>

<style scoped>
.page-shell {
  min-height: 100%;
  padding: 2.5rem 3.5rem 3rem;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.page-header-main {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.page-title {
  font-size: 2.2rem;
  font-weight: 600;
  color: #0f172a;
  margin: 0;
  letter-spacing: -0.02em;
}

.layout-shell.theme-dark .page-title {
  color: #e2e8f0;
}

.page-subtitle {
  font-size: 0.95rem;
  color: #64748b;
  margin: 0;
}

.primary-action {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  background: #ffffff;
  color: #0f172a;
  border: 1px solid rgba(15, 23, 42, 0.12);
  border-radius: 999px;
  font-size: 0.95rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.layout-shell.theme-dark .primary-action {
  background: rgba(15, 23, 42, 0.9);
  border-color: rgba(148, 163, 184, 0.25);
  color: #e2e8f0;
}

.primary-action:hover {
  border-color: rgba(20, 184, 166, 0.6);
  box-shadow: 0 12px 24px rgba(20, 184, 166, 0.18);
  transform: translateY(-1px);
}

.filter-card {
  display: flex;
  gap: 1rem;
  margin-bottom: 2.5rem;
  flex-wrap: wrap;
  padding: 1rem 1.25rem;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.86);
  border: 1px solid rgba(148, 163, 184, 0.2);
  box-shadow: 0 16px 32px rgba(15, 23, 42, 0.08);
  backdrop-filter: blur(10px);
}

.layout-shell.theme-dark .filter-card {
  background: rgba(15, 23, 42, 0.86);
  border-color: rgba(148, 163, 184, 0.2);
  box-shadow: 0 16px 32px rgba(2, 6, 23, 0.55);
}

.search-box {
  position: relative;
  flex: 1;
  min-width: 280px;
  max-width: 420px;
}

.search-icon {
  position: absolute;
  left: 1rem;
  top: 50%;
  transform: translateY(-50%);
  width: 1.25rem;
  height: 1.25rem;
  color: #94a3b8;
  pointer-events: none;
}

.search-input {
  width: 100%;
  padding: 0.875rem 1rem 0.875rem 3rem;
  border: 1px solid rgba(148, 163, 184, 0.35);
  border-radius: 14px;
  font-size: 0.95rem;
  background: rgba(255, 255, 255, 0.9);
  transition: all 0.2s ease;
  outline: none;
}

.layout-shell.theme-dark .search-input {
  background: rgba(15, 23, 42, 0.9);
  border-color: rgba(148, 163, 184, 0.25);
  color: #e2e8f0;
}

.search-input:focus {
  border-color: rgba(20, 184, 166, 0.6);
  box-shadow: 0 0 0 3px rgba(20, 184, 166, 0.18);
}

.status-filters {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.status-filter-btn {
  padding: 0.625rem 1.25rem;
  border: 1px solid rgba(148, 163, 184, 0.35);
  background: rgba(255, 255, 255, 0.9);
  color: #64748b;
  border-radius: 999px;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.layout-shell.theme-dark .status-filter-btn {
  background: rgba(15, 23, 42, 0.9);
  border-color: rgba(148, 163, 184, 0.25);
  color: #cbd5e1;
}

.status-filter-btn.active {
  background: rgba(20, 184, 166, 0.16);
  color: #0f172a;
  border-color: rgba(20, 184, 166, 0.5);
}

.layout-shell.theme-dark .status-filter-btn.active {
  background: rgba(94, 234, 212, 0.2);
  color: #e2e8f0;
  border-color: rgba(94, 234, 212, 0.5);
}

.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 1.5rem;
}

.data-card {
  background: linear-gradient(90deg, rgba(20, 184, 166, 0.7) 0%, rgba(14, 165, 233, 0.7) 100%)
      0 0 / 0 3px no-repeat,
    rgba(255, 255, 255, 0.92);
  border-radius: 18px;
  padding: 1.5rem;
  border: 1px solid rgba(148, 163, 184, 0.2);
  box-shadow: 0 16px 32px rgba(15, 23, 42, 0.08);
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.layout-shell.theme-dark .data-card {
  background: linear-gradient(90deg, rgba(94, 234, 212, 0.5) 0%, rgba(56, 189, 248, 0.5) 100%)
      0 0 / 0 3px no-repeat,
    rgba(15, 23, 42, 0.92);
  border-color: rgba(148, 163, 184, 0.2);
  box-shadow: 0 16px 32px rgba(2, 6, 23, 0.55);
}

.data-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 18px 36px rgba(15, 23, 42, 0.12);
  border-color: rgba(148, 163, 184, 0.35);
  background-size: 100% 3px, auto;
}

.card-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
}

.card-title {
  font-size: 1.1rem;
  font-weight: 600;
  color: #0f172a;
  margin: 0;
}

.layout-shell.theme-dark .card-title {
  color: #e2e8f0;
}

.card-desc {
  margin: 0.5rem 0 0;
  color: #64748b;
  font-size: 0.9rem;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.layout-shell.theme-dark .card-desc {
  color: #94a3b8;
}

.status-pill {
  padding: 0.2rem 0.6rem;
  border-radius: 999px;
  font-size: 0.75rem;
  background: rgba(148, 163, 184, 0.14);
  color: #334155;
  white-space: nowrap;
}

.layout-shell.theme-dark .status-pill {
  background: rgba(148, 163, 184, 0.2);
  color: #e2e8f0;
}

.card-meta {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.75rem;
  background: rgba(148, 163, 184, 0.1);
  border-radius: 14px;
  padding: 0.75rem 1rem;
}

.layout-shell.theme-dark .card-meta {
  background: rgba(30, 41, 59, 0.6);
}

.meta-item {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.meta-label {
  font-size: 0.75rem;
  color: #94a3b8;
}

.meta-value {
  font-size: 0.95rem;
  color: #0f172a;
  font-weight: 600;
}

.layout-shell.theme-dark .meta-value {
  color: #e2e8f0;
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.meta-time {
  font-size: 0.8rem;
  color: #94a3b8;
}

.project-card-actions {
  opacity: 0;
  transition: opacity 0.2s ease;
  display: flex;
  gap: 0.5rem;
}

.data-card:hover .project-card-actions {
  opacity: 1;
}

.project-card-action {
  padding: 0.35rem 0.75rem;
  border-radius: 8px;
  font-size: 0.8rem;
  border: 1px solid rgba(148, 163, 184, 0.3);
  background: rgba(255, 255, 255, 0.8);
  color: #334155;
  cursor: pointer;
  transition: all 0.15s ease;
}

.layout-shell.theme-dark .project-card-action {
  background: rgba(15, 23, 42, 0.8);
  border-color: rgba(148, 163, 184, 0.25);
  color: #e2e8f0;
}

.project-card-action:hover {
  border-color: rgba(20, 184, 166, 0.5);
}

.project-card-action--danger:hover {
  border-color: rgba(239, 68, 68, 0.5);
  color: #ef4444;
}

.empty-state {
  text-align: center;
  padding: 4rem 1rem;
}

.empty-hero {
  font-size: 1.3rem;
  font-weight: 600;
  color: #0f172a;
}

.layout-shell.theme-dark .empty-hero {
  color: #e2e8f0;
}

.empty-hint {
  color: #94a3b8;
  margin: 0.6rem 0 1.6rem;
}

.secondary-action {
  padding: 0.75rem 1.75rem;
  border-radius: 999px;
  background: #0f172a;
  color: #ffffff;
  border: none;
  cursor: pointer;
}

.layout-shell.theme-dark .secondary-action {
  background: #e2e8f0;
  color: #0f172a;
}

/* Modal styles */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.modal-card {
  background: #ffffff;
  border-radius: 20px;
  padding: 2rem;
  width: 90%;
  max-width: 480px;
  box-shadow: 0 24px 48px rgba(0, 0, 0, 0.15);
}

.layout-shell.theme-dark .modal-card {
  background: #1e293b;
}

.modal-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: #0f172a;
  margin: 0 0 1.5rem;
}

.layout-shell.theme-dark .modal-title {
  color: #e2e8f0;
}

.form-group {
  margin-bottom: 1.25rem;
}

.form-label {
  display: block;
  font-size: 0.875rem;
  font-weight: 500;
  color: #334155;
  margin-bottom: 0.5rem;
}

.layout-shell.theme-dark .form-label {
  color: #cbd5e1;
}

.form-input,
.form-textarea,
.form-select {
  width: 100%;
  padding: 0.75rem 1rem;
  border: 1px solid rgba(148, 163, 184, 0.35);
  border-radius: 12px;
  font-size: 0.95rem;
  background: rgba(255, 255, 255, 0.9);
  outline: none;
  transition: all 0.2s ease;
  box-sizing: border-box;
}

.layout-shell.theme-dark .form-input,
.layout-shell.theme-dark .form-textarea,
.layout-shell.theme-dark .form-select {
  background: rgba(15, 23, 42, 0.9);
  border-color: rgba(148, 163, 184, 0.25);
  color: #e2e8f0;
}

.form-input:focus,
.form-textarea:focus,
.form-select:focus {
  border-color: rgba(20, 184, 166, 0.6);
  box-shadow: 0 0 0 3px rgba(20, 184, 166, 0.18);
}

.form-textarea {
  resize: vertical;
  min-height: 80px;
}

.modal-actions {
  display: flex;
  gap: 0.75rem;
  justify-content: flex-end;
  margin-top: 1.5rem;
}

.btn-cancel {
  padding: 0.625rem 1.25rem;
  border-radius: 999px;
  border: 1px solid rgba(148, 163, 184, 0.35);
  background: transparent;
  color: #64748b;
  cursor: pointer;
  font-size: 0.9rem;
}

.layout-shell.theme-dark .btn-cancel {
  color: #94a3b8;
  border-color: rgba(148, 163, 184, 0.25);
}

.btn-confirm {
  padding: 0.625rem 1.5rem;
  border-radius: 999px;
  border: none;
  background: linear-gradient(135deg, #14b8a6, #0ea5e9);
  color: #ffffff;
  cursor: pointer;
  font-size: 0.9rem;
  font-weight: 500;
}

.btn-confirm:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

@media (max-width: 768px) {
  .page-shell {
    padding: 2rem 1.5rem;
  }

  .page-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .primary-action {
    width: 100%;
    justify-content: center;
  }

  .card-footer {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.75rem;
  }

  .project-card-actions {
    opacity: 1;
  }
}
</style>
