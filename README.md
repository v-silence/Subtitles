# Subtitle Service

Простой Django-сервис для локальной генерации SRT-субтитров и перевода видео/аудио без платного API.

## Что используется

- `faster-whisper` распознает речь локально.
- `Argos Translate` переводит субтитры локально.
- Django хранит задания и отдает простой веб-интерфейс.

Первый запуск может скачать модели Whisper и языковые пакеты Argos. Это не требует OpenAI API key, но требует интернет, место на диске и время на загрузку.

## Запуск

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python manage.py migrate
python manage.py runserver
```

Перед локальным запуском без Docker должен быть доступен PostgreSQL. Параметры подключения задаются в `.env` через `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST` и `POSTGRES_PORT`.

Открой `http://127.0.0.1:8000/`.

## Пользователи

Перед созданием субтитров нужно зарегистрироваться или войти в аккаунт. Каждое задание привязывается к текущему пользователю, поэтому в списке, на странице задания и при скачивании SRT доступны только собственные переводы и субтитры.

## Запуск через Docker Compose

Запусти приложение и отдельную базу PostgreSQL:

```powershell
docker compose up --build
```

Открой `http://127.0.0.1:8000/`.

Compose поднимает два сервиса:

- `db` — PostgreSQL 16;
- `web` — Django-приложение.

Volume `postgres_data` хранит данные PostgreSQL. Volume `subtitle_data` хранит загруженные файлы, медиа и скачанные модели. Первый запуск обработки может быть долгим, потому что контейнер скачает Whisper-модель и пакеты Argos Translate.

## Настройки

В `.env` можно менять локальную модель:

```env
POSTGRES_DB=subtitle_service
POSTGRES_USER=subtitle_user
POSTGRES_PASSWORD=subtitle_password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
LOCAL_WHISPER_MODEL=base
LOCAL_WHISPER_DEVICE=cpu
LOCAL_WHISPER_COMPUTE_TYPE=int8
LOCAL_WHISPER_BEAM_SIZE=5
ARGOS_AUTO_INSTALL=1
```

Для более слабого компьютера можно поставить `LOCAL_WHISPER_MODEL=tiny`. Для лучшего качества можно попробовать `small` или `medium`, но они будут медленнее.

## Коды языков

В поле "Язык видео" можно оставить `auto`, чтобы Whisper определил язык сам. Также можно указать код вручную.

| Код | Язык |
| --- | --- |
| `auto` | автоопределение языка видео |
| `ru` | русский |
| `en` | английский |
| `es` | испанский |
| `de` | немецкий |
| `fr` | французский |
| `it` | итальянский |
| `pt` | португальский |
| `zh` | китайский |
| `ja` | японский |
| `ko` | корейский |

Дополнительно сервис понимает старые или региональные значения:

| Значение | Нормализуется в |
| --- | --- |
| `Russian`, `русский` | `ru` |
| `English`, `английский` | `en` |
| `Spanish`, `испанский` | `es` |
| `German`, `немецкий` | `de` |
| `French`, `французский` | `fr` |
| `Italian`, `итальянский` | `it` |
| `Portuguese`, `португальский` | `pt` |
| `Chinese`, `китайский` | `zh` |
| `Japanese`, `японский` | `ja` |
| `Korean`, `корейский` | `ko` |
| `zh-cn`, `zh-hans`, `zh-hant` | `zh` |
| `pt-br`, `pt-pt` | `pt` |

Для поля "Перевод" лучше использовать именно короткие коды из первой таблицы. Наличие перевода зависит от пакетов Argos Translate: если прямой пары нет, сервис попробует перевод через английский.

## Файлы

Можно загружать аудио и видео: `mp3`, `mp4`, `m4a`, `wav`, `webm`, `mov`, `avi`, `mkv`, `flac`, `ogg`. Обработка идет на локальной машине, поэтому большие файлы могут занимать много времени.
