from django.contrib import admin
from .models import Screenplay, ScreenplayEpisode


class ScreenplayEpisodeInline(admin.TabularInline):
    model = ScreenplayEpisode
    extra = 0
    fields = ['episode_number', 'episode_title', 'sort_order', 'updated_at']
    readonly_fields = ['updated_at']


@admin.register(Screenplay)
class ScreenplayAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'status', 'episodes_count', 'created_at', 'updated_at']
    list_filter = ['status', 'created_at']
    search_fields = ['title', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at']
    inlines = [ScreenplayEpisodeInline]

    def episodes_count(self, obj):
        return obj.episodes.count()
    episodes_count.short_description = '分集数'


@admin.register(ScreenplayEpisode)
class ScreenplayEpisodeAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'screenplay', 'episode_number', 'sort_order', 'updated_at']
    list_filter = ['screenplay']
    search_fields = ['episode_title', 'content']
    readonly_fields = ['id', 'created_at', 'updated_at']
