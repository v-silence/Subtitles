from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import VideoUploadForm
from .models import VideoJob
from .services import process_video_job


def index(request):
    if request.method == 'POST':
        form = VideoUploadForm(request.POST, request.FILES)
        if form.is_valid():
            job = form.save()
            process_video_job(job)
            return redirect('videos:detail', pk=job.pk)
    else:
        form = VideoUploadForm(initial={'target_language': 'ru'})

    jobs = VideoJob.objects.all()[:8]
    return render(request, 'videos/index.html', {'form': form, 'jobs': jobs})


def detail(request, pk):
    job = get_object_or_404(VideoJob, pk=pk)
    return render(request, 'videos/detail.html', {'job': job})


@require_POST
def retry(request, pk):
    job = get_object_or_404(VideoJob, pk=pk)
    process_video_job(job)
    return redirect('videos:detail', pk=job.pk)


def download_original(request, pk):
    job = get_object_or_404(VideoJob, pk=pk)
    return _download_srt(job, job.original_srt, 'original')


def download_translated(request, pk):
    job = get_object_or_404(VideoJob, pk=pk)
    return _download_srt(job, job.translated_srt, 'translated')


def _download_srt(job, content, suffix):
    if not content:
        raise Http404('SRT еще не готов.')

    response = HttpResponse(content, content_type='application/x-subrip; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="subtitles-{job.pk}-{suffix}.srt"'
    return response
