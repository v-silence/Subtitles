from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import VideoUploadForm
from .models import VideoJob
from .services import process_video_job


def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('videos:index')
    else:
        form = UserCreationForm()

    return render(request, 'videos/register.html', {'form': form})


@require_POST
def logout_view(request):
    logout(request)
    return redirect('videos:login')


@login_required
def index(request):
    if request.method == 'POST':
        form = VideoUploadForm(request.POST, request.FILES)
        if form.is_valid():
            job = form.save(commit=False)
            job.user = request.user
            job.save()
            process_video_job(job)
            return redirect('videos:detail', pk=job.pk)
    else:
        form = VideoUploadForm(initial={'target_language': 'ru'})

    jobs = VideoJob.objects.filter(user=request.user)[:8]
    return render(request, 'videos/index.html', {'form': form, 'jobs': jobs})


@login_required
def detail(request, pk):
    job = get_user_job(request, pk)
    return render(request, 'videos/detail.html', {'job': job})


@login_required
@require_POST
def retry(request, pk):
    job = get_user_job(request, pk)
    process_video_job(job)
    return redirect('videos:detail', pk=job.pk)


@login_required
def download_original(request, pk):
    job = get_user_job(request, pk)
    return _download_srt(job, job.original_srt, 'original')


@login_required
def download_translated(request, pk):
    job = get_user_job(request, pk)
    return _download_srt(job, job.translated_srt, 'translated')


def get_user_job(request, pk):
    return get_object_or_404(VideoJob, pk=pk, user=request.user)


def _download_srt(job, content, suffix):
    if not content:
        raise Http404('SRT еще не готов.')

    response = HttpResponse(content, content_type='application/x-subrip; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="subtitles-{job.pk}-{suffix}.srt"'
    return response
