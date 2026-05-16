from django.db import models


class VideoJob(models.Model):
    STATUS_QUEUED = 'queued'
    STATUS_PROCESSING = 'processing'
    STATUS_DONE = 'done'
    STATUS_FAILED = 'failed'

    STATUS_CHOICES = [
        (STATUS_QUEUED, 'В очереди'),
        (STATUS_PROCESSING, 'Обработка'),
        (STATUS_DONE, 'Готово'),
        (STATUS_FAILED, 'Ошибка'),
    ]

    input_file = models.FileField(upload_to='uploads/%Y/%m/%d/')
    source_language = models.CharField(max_length=12, blank=True)
    target_language = models.CharField(max_length=64, default='Russian')
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_QUEUED)
    original_srt = models.TextField(blank=True)
    translated_srt = models.TextField(blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Задание #{self.pk or "new"}'

    @property
    def filename(self):
        return self.input_file.name.rsplit('/', 1)[-1]
