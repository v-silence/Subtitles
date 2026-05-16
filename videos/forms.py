from django import forms

from .models import VideoJob


class VideoUploadForm(forms.ModelForm):
    TARGET_CHOICES = [
        ('ru', 'Русский'),
        ('en', 'Английский'),
        ('es', 'Испанский'),
        ('de', 'Немецкий'),
        ('fr', 'Французский'),
        ('it', 'Итальянский'),
        ('pt', 'Португальский'),
        ('zh', 'Китайский'),
        ('ja', 'Японский'),
        ('ko', 'Корейский'),
    ]

    source_language = forms.CharField(
        label='Язык видео',
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'auto, ru, en, es'}),
    )
    target_language = forms.ChoiceField(label='Перевод', choices=TARGET_CHOICES)

    class Meta:
        model = VideoJob
        fields = ['input_file', 'source_language', 'target_language']
        labels = {
            'input_file': 'Видео или аудио',
        }
        widgets = {
            'input_file': forms.FileInput(
                attrs={
                    'accept': '.mp3,.mp4,.mpeg,.mpga,.m4a,.wav,.webm,.mov,.avi,.mkv,.flac,.ogg',
                }
            ),
        }

    def clean_source_language(self):
        value = self.cleaned_data['source_language'].strip().lower()
        return '' if value == 'auto' else value
