"""Offline adapter for the exact owner-selected Portuguese Chatterbox model."""
import json
import re
from pathlib import Path
from f5_russian_narration import (LocalEngine, validate_profile, provenance, text_hash, check_source_identity)

LANGUAGES = ('pt',)
MODEL = 'FearL0rd/Chatterbox-TTS-Portuguese'
MODEL_REVISION = '374a99cccc419f58f2f44cf84d159f2d6d39d0b7'
KEY = 'chatterbox-portuguese'


def chunk_text(text, maximum):
    """Keep every word and punctuation mark while bounding each model request."""
    if type(maximum) is not int or not 80 <= maximum <= 240:
        raise ValueError('Portuguese chunk limit must be 80 to 240 characters')
    fragments = re.split(r'(?<=[.!?;:,])\s+', text.strip())
    chunks = []
    current = ''
    for fragment in fragments:
        for word in fragment.split():
            if len(word) > maximum:
                raise ValueError('Portuguese narration contains an oversized word')
            candidate = (current + ' ' + word).strip()
            if len(candidate) > maximum:
                chunks.append(current)
                current = word
            else:
                current = candidate
        if current.endswith(('.', '!', '?', ';', ':')) and len(current) >= maximum // 2:
            chunks.append(current)
            current = ''
    if current:
        chunks.append(current)
    if not chunks:
        raise ValueError('Portuguese narration must contain text')
    return chunks


def validate(profile):
    validate_profile(profile, MODEL, MODEL_REVISION, 'pt')
    recipe = profile.get('segmentation', {})
    if (recipe.get('mode') != 'bounded-text-v1' or
            type(recipe.get('maximum_characters')) is not int or
            not 80 <= recipe['maximum_characters'] <= 240 or
            type(recipe.get('pause_seconds')) not in (int, float) or
            not 0 <= recipe['pause_seconds'] <= 0.25):
        raise ValueError('Unsupported Portuguese segmentation recipe')


def descriptor(config):
    value = config.get(KEY)
    if isinstance(value, str):
        value = json.loads((Path(__file__).resolve().parents[1] / value).read_text())
    if value is not None:
        validate(value)
        check_source_identity(value)
    return value


class Engine(LocalEngine):
    def __init__(self, profile, local_path):
        validate(profile)
        super().__init__(profile, local_path, __file__)

    def speak(self, config, text, code, work, attempt):
        self.last_generation = None
        result = super().speak(config, text, code, work, attempt)
        if self.last_generation is None:
            recipe = self.profile['segmentation']
            self.last_generation = dict(mode=recipe['mode'],
                                        chunks=chunk_text(text, recipe['maximum_characters']),
                                        pause_seconds=recipe['pause_seconds'], cached=True)
        return result

    def load(self):
        if self.model is not None:
            return
        self.runtime()
        from chatterbox.tts import ChatterboxTTS
        from safetensors import safe_open
        root = Path(self.local['models']) / 'chatterbox-portuguese'
        model = ChatterboxTTS.from_local(root, device='cpu')
        # The official loader permits missing S3 buffers, but every trainable
        # parameter must come from the selected repository's checkpoint.
        with safe_open(root / 's3gen.safetensors', framework='pt', device='cpu') as weights:
            missing = set(dict(model.s3gen.named_parameters())) - set(weights.keys())
        if missing:
            raise ValueError('Portuguese S3 weights missing parameters: ' + ', '.join(sorted(missing)))
        self.model = model

    def synthesize(self, text):
        import numpy as np
        recipe = self.profile['segmentation']
        if recipe['mode'] != 'bounded-text-v1' or not 0 <= recipe['pause_seconds'] <= 0.25:
            raise ValueError('Unsupported Portuguese segmentation recipe')
        chunks = chunk_text(text, recipe['maximum_characters'])
        parts = []
        for chunk in chunks:
            audio = self.model.generate(chunk, audio_prompt_path=self.local['reference'],
                                        **self.profile['parameters'])
            parts.append(audio.detach().float().cpu().numpy().reshape(-1))
        gap = np.zeros(round(self.model.sr * recipe['pause_seconds']), dtype=np.float32)
        joined = []
        for index, part in enumerate(parts):
            if index:
                joined.append(gap)
            joined.append(part)
        self.last_generation = dict(mode=recipe['mode'], chunks=chunks,
                                    chunk_seconds=[len(part) / self.model.sr for part in parts],
                                    pause_seconds=recipe['pause_seconds'])
        return np.concatenate(joined), self.model.sr
