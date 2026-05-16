import tempfile
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings

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
                SubtitleSegment(7, '00:00:00,000 --> 00:00:02,000', 'Привет'),
                SubtitleSegment(8, '00:00:02,000 --> 00:00:04,000', 'Мир'),
            ]
        )

        self.assertIn('1\n00:00:00,000 --> 00:00:02,000\nПривет', result)
        self.assertIn('2\n00:00:02,000 --> 00:00:04,000\nМир', result)

    def test_format_timestamp(self):
        timestamp = format_timestamp(3723.456)

        self.assertEqual(timestamp, '01:02:03,456')

    def test_normalize_language_names(self):
        self.assertEqual(normalize_language_code('English'), 'en')
        self.assertEqual(normalize_language_code('Russian'), 'ru')
        self.assertEqual(normalize_language_code('английский'), 'en')

    def test_translate_srt_accepts_language_names(self):
        source = '1\n00:00:00,000 --> 00:00:02,000\nПривет\n'

        with mock.patch('videos.services.translate_text', return_value='Hello') as translator:
            result = translate_srt(source, 'Russian', 'English')

        self.assertIn('Hello', result)
        translator.assert_called_once_with('Привет', 'ru', 'en')


class UploadViewTests(TestCase):
    def setUp(self):
        self.media_dir = tempfile.TemporaryDirectory()
        self.settings_override = override_settings(MEDIA_ROOT=self.media_dir.name)
        self.settings_override.enable()

    def tearDown(self):
        self.settings_override.disable()
        self.media_dir.cleanup()

    def test_upload_creates_job_and_processes_it(self):
        upload = SimpleUploadedFile('clip.mp3', b'fake audio', content_type='audio/mpeg')

        with mock.patch('videos.views.process_video_job') as processor:
            response = self.client.post(
                '/',
                {
                    'input_file': upload,
                    'source_language': 'auto',
                    'target_language': 'ru',
                },
            )

        job = VideoJob.objects.get()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], f'/jobs/{job.pk}/')
        self.assertEqual(job.source_language, '')
        processor.assert_called_once_with(job)

    def test_download_translated_srt(self):
        job = VideoJob.objects.create(
            input_file='uploads/clip.mp3',
            target_language='ru',
            status=VideoJob.STATUS_DONE,
            translated_srt='1\n00:00:00,000 --> 00:00:01,000\nПривет\n',
        )

        response = self.client.get(f'/jobs/{job.pk}/download/translated/')

        self.assertEqual(response.status_code, 200)
        self.assertIn('subtitles-', response['Content-Disposition'])

# Create your tests here.
