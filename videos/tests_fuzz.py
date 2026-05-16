from unittest import mock
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.test import Client, SimpleTestCase
from hypothesis import given, settings
from hypothesis.extra.django import TestCase
from hypothesis import strategies as st

from .models import VideoJob
from .services import (
    SubtitleSegment,
    format_timestamp,
    normalize_language_code,
    parse_srt,
    render_srt,
    translate_srt,
)


FUZZ_EXAMPLES = 100


class FuzzSubtitleServiceTests(SimpleTestCase):
    @given(st.text(max_size=5000))
    @settings(max_examples=FUZZ_EXAMPLES, deadline=None)
    def test_parse_srt_never_crashes_on_random_text(self, value):
        result = parse_srt(value)

        self.assertIsInstance(result, list)

    @given(
        st.lists(
            st.builds(
                SubtitleSegment,
                number=st.integers(min_value=-1000, max_value=1000),
                timing=st.text(min_size=1, max_size=80),
                text=st.text(max_size=500),
            ),
            max_size=50,
        )
    )
    @settings(max_examples=FUZZ_EXAMPLES, deadline=None)
    def test_render_srt_never_crashes_on_random_segments(self, segments):
        result = render_srt(segments)

        self.assertIsInstance(result, str)

    @given(st.text(max_size=500))
    @settings(max_examples=FUZZ_EXAMPLES, deadline=None)
    def test_normalize_language_code_never_crashes(self, value):
        result = normalize_language_code(value)

        self.assertIsInstance(result, str)

    @given(st.one_of(st.none(), st.text(max_size=500)))
    @settings(max_examples=FUZZ_EXAMPLES, deadline=None)
    def test_normalize_language_code_handles_none_and_text(self, value):
        result = normalize_language_code(value)

        self.assertIsInstance(result, str)

    @given(
        st.floats(
            min_value=-100000,
            max_value=100000,
            allow_nan=False,
            allow_infinity=False,
        )
    )
    @settings(max_examples=FUZZ_EXAMPLES, deadline=None)
    def test_format_timestamp_never_crashes_on_numbers(self, value):
        result = format_timestamp(value)

        self.assertIsInstance(result, str)
        self.assertIn(',', result)

    @given(
        text=st.text(max_size=200),
        source_language=st.text(max_size=50),
        target_language=st.text(max_size=50),
    )
    @settings(max_examples=FUZZ_EXAMPLES, deadline=None)
    def test_translate_srt_with_random_language_names_does_not_return_500_level_exception(
        self,
        text,
        source_language,
        target_language,
    ):
        srt = f'1\n00:00:00,000 --> 00:00:01,000\n{text}\n'

        with mock.patch('videos.services.translate_text', return_value='translated'):
            try:
                result = translate_srt(srt, source_language, target_language)
            except Exception as exc:
                self.assertIsInstance(exc, RuntimeError)
            else:
                self.assertIsInstance(result, str)


class FuzzViewTests(TestCase):
    def setUp(self):
        suffix = uuid4().hex
        self.client = Client()
        self.user = get_user_model().objects.create_user(
            username=f'fuzz-user-{suffix}',
            password='strong-password-123',
        )
        self.other_user = get_user_model().objects.create_user(
            username=f'other-fuzz-user-{suffix}',
            password='strong-password-123',
        )
        self.client.force_login(self.user)

    @given(
        source_language=st.text(max_size=100),
        target_language=st.text(max_size=100),
    )
    @settings(max_examples=50, deadline=None)
    def test_upload_form_rejects_random_payloads_without_server_error(
        self,
        source_language,
        target_language,
    ):
        self.client.force_login(self.user)
        response = self.client.post(
            '/',
            {
                'source_language': source_language,
                'target_language': target_language,
            },
        )

        self.assertNotEqual(response.status_code, 500)

    @given(pk=st.integers(min_value=1, max_value=10**9))
    @settings(max_examples=50, deadline=None)
    def test_random_job_detail_ids_do_not_crash(self, pk):
        self.client.force_login(self.user)
        response = self.client.get(f'/jobs/{pk}/')

        self.assertNotEqual(response.status_code, 500)

    @given(
        translated_srt=st.text(max_size=1000),
        suffix_pk=st.integers(min_value=1, max_value=1000),
    )
    @settings(max_examples=50, deadline=None)
    def test_foreign_download_attempts_do_not_expose_data(self, translated_srt, suffix_pk):
        self.client.force_login(self.user)
        job = VideoJob.objects.create(
            user=self.other_user,
            input_file=f'uploads/foreign-{suffix_pk}.mp3',
            target_language='ru',
            status=VideoJob.STATUS_DONE,
            translated_srt=translated_srt,
        )

        response = self.client.get(f'/jobs/{job.pk}/download/translated/')

        self.assertEqual(response.status_code, 404)
