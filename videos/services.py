import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from django.conf import settings

from .models import VideoJob


LANGUAGE_ALIASES = {
    'auto': '',
    'russian': 'ru',
    'русский': 'ru',
    'английский': 'en',
    'english': 'en',
    'spanish': 'es',
    'испанский': 'es',
    'german': 'de',
    'немецкий': 'de',
    'french': 'fr',
    'французский': 'fr',
    'italian': 'it',
    'итальянский': 'it',
    'portuguese': 'pt',
    'португальский': 'pt',
    'chinese': 'zh',
    'китайский': 'zh',
    'japanese': 'ja',
    'японский': 'ja',
    'korean': 'ko',
    'корейский': 'ko',
    'zh-cn': 'zh',
    'zh-hans': 'zh',
    'zh-hant': 'zh',
    'pt-br': 'pt',
    'pt-pt': 'pt',
}


@dataclass
class SubtitleSegment:
    number: int
    timing: str
    text: str


@dataclass
class TranscriptionResult:
    srt: str
    language: str


class ProcessingError(RuntimeError):
    pass


def process_video_job(job):
    job.status = VideoJob.STATUS_PROCESSING
    job.error_message = ''
    job.save(update_fields=['status', 'error_message', 'updated_at'])

    try:
        source_language = normalize_language_code(job.source_language)
        result = transcribe_to_srt(Path(job.input_file.path), source_language)
        detected_language = source_language or result.language
        translated_srt = translate_srt(result.srt, detected_language, job.target_language)

        job.source_language = detected_language
        job.original_srt = result.srt.strip() + '\n'
        job.translated_srt = translated_srt.strip() + '\n'
        job.status = VideoJob.STATUS_DONE
        job.save(
            update_fields=[
                'source_language',
                'original_srt',
                'translated_srt',
                'status',
                'updated_at',
            ]
        )
    except Exception as exc:
        job.status = VideoJob.STATUS_FAILED
        job.error_message = str(exc)
        job.save(update_fields=['status', 'error_message', 'updated_at'])


def transcribe_to_srt(media_path, source_language=''):
    model = _get_whisper_model()
    options = {
        'beam_size': settings.LOCAL_WHISPER_BEAM_SIZE,
    }
    if source_language:
        options['language'] = source_language

    try:
        whisper_segments, info = model.transcribe(str(media_path), **options)
    except Exception as exc:
        raise ProcessingError(f'Не удалось распознать речь локальной Whisper-моделью: {exc}') from exc

    subtitle_segments = []
    for index, segment in enumerate(whisper_segments, start=1):
        text = segment.text.strip()
        if not text:
            continue

        subtitle_segments.append(
            SubtitleSegment(
                number=index,
                timing=f'{format_timestamp(segment.start)} --> {format_timestamp(segment.end)}',
                text=text,
            )
        )

    if not subtitle_segments:
        raise ProcessingError('В файле не удалось найти речь для субтитров.')

    detected_language = normalize_language_code(getattr(info, 'language', '') or source_language)
    return TranscriptionResult(srt=render_srt(subtitle_segments), language=detected_language)


def translate_srt(srt_text, source_language, target_language):
    source_code = normalize_language_code(source_language)
    target_code = normalize_language_code(target_language)
    segments = parse_srt(srt_text)

    if not segments:
        raise ProcessingError('Не удалось разобрать SRT, полученный после распознавания.')

    if not source_code:
        raise ProcessingError('Не удалось определить язык видео. Укажите язык вручную, например en или ru.')

    if not target_code or source_code == target_code:
        return render_srt(segments)

    translated_segments = []
    for segment in segments:
        translated_segments.append(
            SubtitleSegment(
                number=segment.number,
                timing=segment.timing,
                text=translate_text(segment.text, source_code, target_code),
            )
        )

    return render_srt(translated_segments)


def translate_text(text, source_code, target_code):
    try:
        return _translate_text_with_argos(text, source_code, target_code)
    except ProcessingError as direct_error:
        if source_code == 'en' or target_code == 'en':
            raise direct_error

        try:
            english_text = _translate_text_with_argos(text, source_code, 'en')
            return _translate_text_with_argos(english_text, 'en', target_code)
        except ProcessingError as pivot_error:
            raise ProcessingError(
                f'Не удалось перевести с {source_code} на {target_code}. '
                f'Прямая ошибка: {direct_error}. Через английский: {pivot_error}'
            ) from pivot_error


def parse_srt(srt_text):
    normalized = srt_text.replace('\r\n', '\n').replace('\r', '\n').strip()
    pattern = re.compile(r'(?ms)^\s*(\d+)\s*\n([^\n]*?-->\s*[^\n]*)\s*\n(.*?)(?=\n{2,}\s*\d+\s*\n|\s*\Z)')
    segments = []

    for match in pattern.finditer(normalized):
        segments.append(
            SubtitleSegment(
                number=int(match.group(1)),
                timing=match.group(2).strip(),
                text=match.group(3).strip(),
            )
        )

    return segments


def render_srt(segments):
    blocks = []
    for index, segment in enumerate(segments, start=1):
        text = segment.text.strip()
        blocks.append(f'{index}\n{segment.timing}\n{text}')
    return '\n\n'.join(blocks) + '\n'


def format_timestamp(seconds):
    milliseconds_total = max(0, int(round(seconds * 1000)))
    hours, remainder = divmod(milliseconds_total, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    whole_seconds, milliseconds = divmod(remainder, 1000)
    return f'{hours:02d}:{minutes:02d}:{whole_seconds:02d},{milliseconds:03d}'


def normalize_language_code(value):
    normalized = (value or '').strip().lower()
    normalized = LANGUAGE_ALIASES.get(normalized, normalized)
    if '-' in normalized:
        normalized = normalized.split('-', 1)[0]
    return normalized


@lru_cache(maxsize=1)
def _get_whisper_model():
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise ProcessingError(
            'Не установлен faster-whisper. Выполните: pip install -r requirements.txt'
        ) from exc

    try:
        return WhisperModel(
            settings.LOCAL_WHISPER_MODEL,
            device=settings.LOCAL_WHISPER_DEVICE,
            compute_type=settings.LOCAL_WHISPER_COMPUTE_TYPE,
        )
    except Exception as exc:
        raise ProcessingError(f'Не удалось загрузить локальную Whisper-модель: {exc}') from exc


def _translate_text_with_argos(text, source_code, target_code):
    if source_code == target_code:
        return text

    try:
        import argostranslate.translate
    except ImportError as exc:
        raise ProcessingError(
            'Не установлен argostranslate. Выполните: pip install -r requirements.txt'
        ) from exc

    _ensure_argos_package(source_code, target_code)

    try:
        return argostranslate.translate.translate(text, source_code, target_code)
    except Exception as exc:
        raise ProcessingError(f'Argos Translate не смог выполнить перевод {source_code}->{target_code}: {exc}') from exc


@lru_cache(maxsize=64)
def _ensure_argos_package(source_code, target_code):
    if _has_argos_translation(source_code, target_code):
        return

    if not settings.ARGOS_AUTO_INSTALL:
        raise ProcessingError(
            f'Не установлен локальный пакет перевода {source_code}->{target_code}. '
            'Включите ARGOS_AUTO_INSTALL=1 или установите пакет Argos вручную.'
        )

    try:
        import argostranslate.package
    except ImportError as exc:
        raise ProcessingError(
            'Не установлен argostranslate. Выполните: pip install -r requirements.txt'
        ) from exc

    try:
        argostranslate.package.update_package_index()
        available_packages = argostranslate.package.get_available_packages()
        package = next(
            (
                item for item in available_packages
                if item.from_code == source_code and item.to_code == target_code
            ),
            None,
        )
        if package is None:
            raise ProcessingError(f'Для Argos Translate нет пакета {source_code}->{target_code}.')

        argostranslate.package.install_from_path(package.download())
    except ProcessingError:
        raise
    except Exception as exc:
        raise ProcessingError(
            f'Не удалось скачать или установить пакет Argos {source_code}->{target_code}: {exc}'
        ) from exc

    if not _has_argos_translation(source_code, target_code):
        raise ProcessingError(f'Пакет Argos {source_code}->{target_code} установлен, но перевод недоступен.')


def _has_argos_translation(source_code, target_code):
    try:
        import argostranslate.translate
    except ImportError as exc:
        raise ProcessingError(
            'Не установлен argostranslate. Выполните: pip install -r requirements.txt'
        ) from exc

    installed_languages = argostranslate.translate.get_installed_languages()
    source_language = next((item for item in installed_languages if item.code == source_code), None)
    target_language = next((item for item in installed_languages if item.code == target_code), None)
    if source_language is None or target_language is None:
        return False

    try:
        return source_language.get_translation(target_language) is not None
    except Exception:
        return False
