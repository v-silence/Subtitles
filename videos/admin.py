from django.contrib import admin

from .models import VideoJob


@admin.register(VideoJob)
class VideoJobAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'filename', 'target_language', 'status', 'created_at')
    list_filter = ('status', 'target_language', 'created_at')
    search_fields = ('input_file', 'error_message', 'user__username')
    readonly_fields = ('created_at', 'updated_at')

# Register your models here.
