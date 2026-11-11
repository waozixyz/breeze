"""Offline Czech fine-tuned Chatterbox; explicit authorized weights only."""
import json
from pathlib import Path
from f5_russian_narration import (LocalEngine, validate_profile, provenance, text_hash, check_source_identity)

LANGUAGES = ('cs',)
MODEL = 'Thomcles/Chatterbox-TTS-Czech'
MODEL_REVISION = '1be084192841e27c8bdf7386326405dee08db803'
KEY = 'chatterbox_czech'


def validate(profile):
    validate_profile(profile, MODEL, MODEL_REVISION, 'cs')


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

    def load(self):
        if self.model is not None:
            return
        self.runtime()
        from chatterbox.mtl_tts import ChatterboxMultilingualTTS
        from safetensors.torch import load_file
        from chatterbox.models.t3 import T3
        from chatterbox.models.t3.modules.t3_config import T3Config
        from chatterbox.models.s3gen import S3Gen
        from chatterbox.models.voice_encoder import VoiceEncoder
        from chatterbox.models.tokenizers import MTLTokenizer
        root = Path(self.local['models'])
        # Same official from_local component construction, loading the selected
        # fine-tune directly so a second 2GB T3 checkpoint is unnecessary.
        ve = VoiceEncoder()
        ve.load_state_dict(self.torch.load(root / 'chatterbox-multilingual/ve.pt', map_location='cpu', weights_only=True))
        t3 = T3(T3Config.multilingual())
        t3.load_state_dict(load_file(root / 'chatterbox-czech/t3_cs.safetensors', device='cpu'))
        s3gen = S3Gen()
        s3gen.load_state_dict(self.torch.load(root / 'chatterbox-multilingual/s3gen.pt', map_location='cpu', weights_only=True))
        from chatterbox.models.tokenizers.tokenizer import ChineseCangjieConverter
        from unittest.mock import patch
        def local_mapping(converter, model_dir=None):
            data = json.loads((root / 'chatterbox-multilingual/Cangjie5_TC.json').read_text())
            for entry in data:
                word, code = entry.split('\t')[:2]
                converter.word2cj[word] = code
                converter.cj2word.setdefault(code, []).append(word)
        # Czech never uses Chinese segmentation. Avoid upstream's unconditional
        # HF mapping lookup and pkuseg network initialization during construction.
        with patch.object(ChineseCangjieConverter, '_load_cangjie_mapping', local_mapping), \
                patch.object(ChineseCangjieConverter, '_init_segmenter', lambda converter: None):
            tokenizer = MTLTokenizer(str(root / 'chatterbox-multilingual/grapheme_mtl_merged_expanded_v1.json'))
        self.model = ChatterboxMultilingualTTS(t3.eval(), s3gen.eval(), ve.eval(), tokenizer, 'cpu')

    def synthesize(self, text):
        from chatterbox import mtl_tts
        from functools import partial
        from unicodedata import normalize
        from unittest.mock import patch
        language = self.profile['language_id']
        if language == 'cs':
            token = self.model.tokenizer.tokenizer.token_to_id('[cs]')
            if token != self.profile['language_token_id'] or token == self.model.tokenizer.tokenizer.token_to_id('[UNK]'):
                raise RuntimeError('Pinned tokenizer has no Czech language token')
        # The fine-tuned checkpoint's tokenizer includes [cs]; the upstream
        # registry omits it. Scope the registry extension to this single call.
        if self.profile['normalization'] not in ('NFC', 'NFKD'):
            raise ValueError('Czech reference tokenizer requires a pinned normalization form')
        tokens = partial(self.model.tokenizer.text_to_tokens, nfkd_normalize=self.profile['normalization'] == 'NFKD')
        with patch.dict(mtl_tts.SUPPORTED_LANGUAGES, {'cs': 'Czech'}), \
                patch.object(self.model.tokenizer, 'text_to_tokens', tokens):
            audio = self.model.generate(normalize(self.profile['normalization'], text), language_id=language, audio_prompt_path=self.local['reference'],
                                        **self.profile['parameters'])
        return audio.detach().float().cpu().numpy(), self.model.sr
