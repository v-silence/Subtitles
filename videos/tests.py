import tempfile
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings

from .forms import VideoUploadForm
from .models import VideoJob
from .services import (
    SubtitleSegment,
    format_timestamp,
    normalize_language_code,
    parse_srt,
    render_srt,
    translate_srt,
)


class SrtServiceTests(SimpleTestCase):
    def test_parse_srt_returns_segments(self):
        source = (
            '1\n'
            '00:00:00,000 --> 00:00:02,000\n'
            'Hello\n\n'
            '2\n'
            '00:00:02,000 --> 00:00:04,000\n'
            'World\n'
        )

        segments = parse_srt(source)

        self.assertEqual(len(segments), 2)
        self.assertEqual(segments[0].text, 'Hello')
        self.assertEqual(segments[1].timing, '00:00:02,000 --> 00:00:04,000')

    def test_render_srt_renumbers_segments(self):
        result = render_srt(
            [
                SubtitleSegment(7, '00:00:00,000 --> 00:00:02,000', 'Hello'),
                SubtitleSegment(8, '00:00:02,000 --> 00:00:04,000', 'World'),
            ]
        )

        self.assertIn('1\n00:00:00,000 --> 00:00:02,000\nHello', result)
        self.assertIn('2\n00:00:02,000 --> 00:00:04,000\nWorld', result)

    def test_format_timestamp(self):
        timestamp = format_timestamp(3723.456)

        self.assertEqual(timestamp, '01:02:03,456')

    def test_normalize_language_names(self):
        self.assertEqual(normalize_language_code('English'), 'en')
        self.assertEqual(normalize_language_code('Russian'), 'ru')
        self.assertEqual(normalize_language_code('zh-cn'), 'zh')

    def test_translate_srt_accepts_language_names(self):
        source = '1\n00:00:00,000 --> 00:00:02,000\nPrivet\n'

        with mock.patch('videos.services.translate_text', return_value='Hello') as translator:
            result = translate_srt(source, 'Russian', 'English')

        self.assertIn('Hello', result)
        translator.assert_called_once_with('Privet', 'ru', 'en')


class UploadViewTests(TestCase):
    def setUp(self):
        self.media_dir = tempfile.TemporaryDirectory()
        self.settings_override = override_settings(MEDIA_ROOT=self.media_dir.name)
        self.settings_override.enable()
        self.user = get_user_model().objects.create_user(
            username='alice',
            password='strong-password-123',
        )
        self.other_user = get_user_model().objects.create_user(
            username='bob',
            password='strong-password-123',
        )

    def tearDown(self):
        self.settings_override.disable()
        self.media_dir.cleanup()

    def test_index_requires_login(self):
        response = self.client.get('/')

        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response['Location'])

    def test_upload_creates_job_and_processes_it(self):
        self.client.force_login(self.user)
        upload = SimpleUploadedFile('clip.mp3', b'fake audio', content_type='audio/mpeg')

        with mock.patch('videos.views.process_video_job') as processor:
            response = self.client.post(
                '/',
                {
                    'input_file': upload,
                    'source_language': '',
                    'target_language': 'ru',
                },
            )

        job = VideoJob.objects.get()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], f'/jobs/{job.pk}/')
        self.assertEqual(job.user, self.user)
        self.assertEqual(job.source_language, '')
        processor.assert_called_once_with(job)

    def test_upload_form_rejects_unknown_source_language(self):
        upload = SimpleUploadedFile('clip.mp3', b'fake audio', content_type='audio/mpeg')
        form = VideoUploadForm(
            data={
                'source_language': 'english',
                'target_language': 'ru',
            },
            files={'input_file': upload},
        )

        self.assertFalse(form.is_valid())
        self.assertIn('source_language', form.errors)

    def test_index_shows_only_current_user_jobs(self):
        self.client.force_login(self.user)
        own_job = VideoJob.objects.create(
            user=self.user,
            input_file='uploads/own.mp3',
            target_language='ru',
        )
        VideoJob.objects.create(
            user=self.other_user,
            input_file='uploads/other.mp3',
            target_language='ru',
        )

        response = self.client.get('/')

        self.assertContains(response, own_job.filename)
        self.assertNotContains(response, 'other.mp3')

    def test_detail_does_not_allow_foreign_jobs(self):
        self.client.force_login(self.user)
        job = VideoJob.objects.create(
            user=self.other_user,
            input_file='uploads/other.mp3',
            target_language='ru',
        )

        response = self.client.get(f'/jobs/{job.pk}/')

        self.assertEqual(response.status_code, 404)

    def test_download_translated_srt(self):
        self.client.force_login(self.user)
        job = VideoJob.objects.create(
            user=self.user,
            input_file='uploads/clip.mp3',
            target_language='ru',
            status=VideoJob.STATUS_DONE,
            translated_srt='1\n00:00:00,000 --> 00:00:01,000\nHello\n',
        )

        response = self.client.get(f'/jobs/{job.pk}/download/translated/')

        self.assertEqual(response.status_code, 200)
        self.assertIn('subtitles-', response['Content-Disposition'])

    def test_download_does_not_allow_foreign_jobs(self):
        self.client.force_login(self.user)
        job = VideoJob.objects.create(
            user=self.other_user,
            input_file='uploads/other.mp3',
            target_language='ru',
            status=VideoJob.STATUS_DONE,
            translated_srt='1\n00:00:00,000 --> 00:00:01,000\nHello\n',
        )

        response = self.client.get(f'/jobs/{job.pk}/download/translated/')

        self.assertEqual(response.status_code, 404)


class AuthViewTests(TestCase):
    def test_register_creates_user_and_logs_in(self):
        response = self.client.post(
            '/accounts/register/',
            {
                'username': 'new-user',
                'password1': 'strong-password-123',
                'password2': 'strong-password-123',
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/')
        self.assertTrue(get_user_model().objects.filter(username='new-user').exists())

        response = self.client.get('/')

        self.assertEqual(response.status_code, 200)
