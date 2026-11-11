"""Pinned, offline F5 Russian adapter and shared local PCM cache primitives.

Preparation is explicit: inference never downloads weights or installs packages.
Speaker-reference provenance identifies the selected synthetic Leda recording;
it does not certify perceived gender or speaker similarity.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

LANGUAGES = ('ru',)
MODEL = 'Misha24-10/F5-TTS_RUSSIAN'
MODEL_REVISION = 'ea166adeae4c80ec5ee423a671e2bdb83906cf84'
RUNTIME_VERSION = '1.1.22'
KEY = 'f5_russian'


def file_hash(path):
    with Path(path).open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def json_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    allow_nan=False).encode()).hexdigest()


def validate_profile(profile, model, revision, locale):
    if (profile.get('schema') != 1 or profile.get('model') != model or
            profile.get('model_revision') != revision or profile.get('locale') != locale):
        raise ValueError('Unsupported local voice profile')
    if profile.get('status') != 'ready':
        raise ValueError('Local voice profile is not ready: ' + profile.get('status', 'unknown'))
    for field in ('reference_sha256', 'adapter_sha256'):
        digest = profile.get(field, '')
        if len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
            raise ValueError('Missing exact voice profile hash: ' + field)
    if not profile.get('reference_text') or not profile.get('parameters') or not profile.get('environment'):
        raise ValueError('Missing reference transcript, sampling parameters or runtime pins')
    if not profile.get('artifacts'):
        raise ValueError('Missing local model artifacts')
    for name, digest in profile['artifacts'].items():
        if (Path(name).is_absolute() or '..' in Path(name).parts or len(digest) != 64 or
                any(c not in '0123456789abcdef' for c in digest)):
            raise ValueError('Invalid voice artifact: ' + name)


def validate(profile):
    validate_profile(profile, MODEL, MODEL_REVISION, 'ru')


def descriptor(config):
    value = config.get(KEY)
    if isinstance(value, str):
        value = json.loads((Path(__file__).resolve().parents[1] / value).read_text())
    if value is not None:
        validate(value)
        check_source_identity(value)
    return value


def provenance(profile):
    return dict(provider=profile['provider'], model=profile['model'],
                model_revision=profile['model_revision'], runtime_version=profile['runtime_version'],
                reference_sha256=profile['reference_sha256'], profile_sha256=json_hash(profile))


def check_source_identity(profile):
    root = Path(__file__).resolve().parent
    expected = {'f5_russian_narration.py', 'prepare-local-voice-profile.py', 'whisper_narration.py'}
    if profile['locale'] == 'cs':
        expected.add('chatterbox_czech_narration.py')
    elif profile['locale'] == 'pt':
        expected.add('chatterbox_portuguese_narration.py')
    sources = profile.get('source_files', {})
    if set(sources) != expected:
        raise ValueError('Missing local voice source fingerprints')
    for name, digest in sources.items():
        if file_hash(root / name) != digest:
            raise ValueError('Changed local voice source: ' + name)


def text_hash(config, text, profile, code):
    check_source_identity(profile)
    if code != profile['locale']:
        raise ValueError('Unsupported local voice locale: ' + code)
    return json_hash(dict(text=text, locale=code, synthesis=provenance(profile),
                          pcm_sample_rate=config['pcm_sample_rate'],
                          sample_rate=config['sample_rate'], opus_bitrate=config.get('opus_bitrate', '16k')))


class LocalEngine:
    def __init__(self, profile, local_path, adapter_path):
        self.profile = profile
        self.local = json.loads(Path(local_path).read_text())
        self.model = None
        self.last_transcription = None
        self.adapter_path = adapter_path
        if profile['adapter_sha256'] != file_hash(adapter_path):
            raise ValueError('Changed local voice adapter')
        if profile.get('base_adapter_sha256') and profile['base_adapter_sha256'] != file_hash(__file__):
            raise ValueError('Changed shared local PCM adapter')
        if profile['reference_sha256'] != file_hash(self.local['reference']):
            raise ValueError('Changed female reference recording')
        for name, expected in profile['artifacts'].items():
            if file_hash(Path(self.local['models']) / name) != expected:
                raise ValueError('Changed model artifact: ' + name)
        self.threads = self.local.get('threads', 2)
        if self.threads != self.profile.get('threads', 2):
            raise ValueError('Local thread budget differs from pinned voice profile')
        if type(self.threads) is not int or not 1 <= self.threads <= 4:
            raise ValueError('Local voice CPU budget must be one to four threads')

    def runtime(self):
        os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1',
                          OMP_NUM_THREADS=str(self.threads), MKL_NUM_THREADS=str(self.threads),
                          NUMBA_NUM_THREADS=str(self.threads), OPENBLAS_NUM_THREADS=str(self.threads), TOKENIZERS_PARALLELISM='false')
        import torch
        from importlib.metadata import version
        for package, expected in self.profile['environment'].items():
            if version(package) != expected:
                raise ValueError('Changed runtime package: ' + package)
        torch.set_num_threads(self.threads)
        self.torch = torch

    def speak(self, config, text, code, work, attempt):
        request = text_hash(config, text, self.profile, code)
        identity = json_hash(dict(request=request, attempt=attempt))
        cache = Path(self.local['cache']).resolve()
        root = Path(__file__).resolve().parents[1]
        subprocess.run(['git', '-C', str(root), 'check-ignore', '-q', str(cache / 'probe')], check=True)
        cache.mkdir(parents=True, exist_ok=True)
        pcm, receipt = cache / (identity + '.pcm'), cache / (identity + '.json')
        if pcm.is_file() and receipt.is_file():
            saved = json.loads(receipt.read_text())
            if saved.get('request') == identity and saved.get('sha256') == file_hash(pcm):
                self.last_synthesis = saved.get('amplitude')
                return pcm.read_bytes(), provenance(self.profile)
        self.load()
        import numpy as np
        import soundfile as sf
        self.torch.manual_seed(self.profile['seed'] + attempt)
        with self.torch.inference_mode():
            audio, rate = self.synthesize(text)
        audio = np.asarray(audio).reshape(-1)
        if (not isinstance(rate, (int, float)) or rate <= 0 or not 0 < len(audio) <= rate * 120 or
                not np.isfinite(audio).all()):
            raise RuntimeError('Local voice returned empty, nonfinite or oversized audio')
        ceiling = self.profile['peak_ceiling']
        if not 0 < ceiling < 1:
            raise ValueError('Invalid PCM peak ceiling')
        peak = float(np.abs(audio).max())
        gain = min(1.0, ceiling / peak) if peak else 1.0
        audio = audio * gain
        self.last_synthesis = dict(raw_peak=peak, pcm_gain=gain, peak_ceiling=ceiling)
        work = Path(work).resolve()
        work.mkdir(parents=True, exist_ok=True)
        wav = work / (self.profile['locale'] + '-voice.wav')
        sf.write(wav, audio, rate, subtype='PCM_16')
        result = subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-threads', '1',
                                 '-i', str(wav), '-ac', '1', '-ar', str(config['pcm_sample_rate']),
                                 '-f', 's16le', '-'], check=True, capture_output=True).stdout
        if not result or len(result) % 2:
            raise RuntimeError('Invalid converted PCM')
        part = pcm.with_suffix('.pcm.part')
        part.write_bytes(result)
        part.replace(pcm)
        part = receipt.with_suffix('.json.part')
        part.write_text(json.dumps(dict(request=identity, sha256=file_hash(pcm), amplitude=self.last_synthesis)) + '\n')
        part.replace(receipt)
        return result, provenance(self.profile)

    def transcribe(self, clip, code):
        """Separate pinned read-only ASR process frees the synthesis process from ASR dependencies."""
        command = self.local.get('asr_command')
        if not command:
            raise ValueError('Explicit local ASR command required')
        for index, expected in self.profile.get('asr_command_files', {}).items():
            if file_hash(command[int(index)]) != expected:
                raise ValueError('Changed ASR command file')
        if not self.profile.get('asr_command_files'):
            raise ValueError('ASR command files must be pinned')
        for name, digest in self.profile.get('asr_artifacts', {}).items():
            if file_hash(Path(self.local['asr']) / name) != digest:
                raise ValueError('Changed ASR model artifact: ' + name)
        args = [s.replace('{audio}', str(Path(clip).resolve())).replace('{language}', code) for s in command]
        row = json.loads(subprocess.run(args, check=True, capture_output=True, text=True).stdout)
        if (row.get('model') != self.profile['transcriber'] or
                row.get('revision') != self.profile['asr_revision'] or
                row.get('language') != code or row.get('audio_sha256') != file_hash(clip) or
                row.get('truncation') is not False or row.get('long_form') is not True or
                not 0 < row.get('seconds', 0) <= 120):
            raise RuntimeError('ASR did not read complete audio')
        self.last_transcription = row
        return row['text']

    def speaker_match(self, clip):
        import math
        command = self.local.get('speaker_command')
        expected = self.profile.get('speaker_command_files', {})
        if not command or not expected:
            raise ValueError('Explicit pinned speaker verifier required')
        for index, digest in expected.items():
            if file_hash(command[int(index)]) != digest:
                raise ValueError('Changed speaker verifier file')
        args = [arg.replace('{audio}', str(Path(clip).resolve())) for arg in command]
        row = json.loads(subprocess.run(args, check=True, capture_output=True, text=True).stdout)
        score = row.get('cosine')
        if (row.get('audio_sha256') != file_hash(clip) or
                row.get('reference_sha256') != self.profile['reference_sha256'] or
                row.get('model_sha256') != self.profile['speaker_model_sha256'] or
                row.get('runtime_sha256') != self.profile['speaker_runtime_sha256'] or
                not isinstance(score, (int, float)) or not math.isfinite(score)):
            raise RuntimeError('Invalid speaker consistency receipt')
        return score


class Engine(LocalEngine):
    def __init__(self, profile, local_path):
        validate(profile)
        super().__init__(profile, local_path, __file__)

    def load(self):
        if self.model is not None:
            return
        self.runtime()
        from functools import partial
        from concurrent.futures import ThreadPoolExecutor
        from importlib.resources import files
        from omegaconf import OmegaConf
        import f5_tts.infer.utils_infer as infer
        from f5_tts.model import DiT
        # Upstream parallelizes text chunks; keep one bounded model invocation.
        infer.ThreadPoolExecutor = partial(ThreadPoolExecutor, max_workers=1)
        cfg = OmegaConf.load(str(files('f5_tts').joinpath('configs/F5TTS_v1_Base.yaml')))
        root = Path(self.local['models'])
        self.model = infer.load_model(DiT, cfg.model.arch, str(root / 'f5-russian/model.safetensors'),
                                      vocab_file=str(root / 'f5-russian/vocab.txt'), device='cpu')
        self.vocoder = infer.load_vocoder(is_local=True, local_path=str(root / 'vocos-mel-24khz'), device='cpu')

    def synthesize(self, text):
        from f5_tts.infer.utils_infer import infer_process
        audio, rate, _ = infer_process(self.local['reference'], self.profile['reference_text'], text,
                                       self.model, self.vocoder, device='cpu',
                                       **self.profile['parameters'])
        return audio, rate
