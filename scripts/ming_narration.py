"""Offline Ming adapter. Local paths are supplied separately from public provenance.

No model downloads, service discovery or installation happens here. The caller
uses the interpreter belonging to the explicitly selected local runtime.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import narration_segments

LANGUAGES = ('en', 'es', 'de', 'fr', 'ja', 'ko', 'zh')
MODEL = 'inclusionAI/Ming-3.0-tts-0.5B'
MODEL_REVISION = '7247f4c94a5b2e987404ed28a5cfec41b1a4ca61'
RUNTIME_REVISION = 'a39b80660bdc5a4394d5e1d41af6dbfd9c443a54'


def segment_plan(profile, text):
    return narration_segments.plan(text, profile['segmentation']['maximum_units'])


def segment_seed(profile, attempt, index):
    return profile.get('seed', 20261108) + attempt * 1000003 + index


def request_arguments(profile, text, code, embedding):
    if code not in LANGUAGES:
        raise ValueError('Ming does not support locale ' + code)
    return dict(task='FREEFORM', instruction=profile['instruction'], text=text,
                language_id=code, spk_emb_path=embedding, use_spk_emb=True,
                raw_text=True, cfg=2.0, sigma=0.25, temperature=0.0,
                max_decode_steps=1000)


def file_hash(path):
    with Path(path).open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def json_hash(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    allow_nan=False).encode()).hexdigest()


def descriptor(config):
    """The public manifest is sufficient for offline package certification."""
    value = config.get('ming')
    if value is None:
        return None
    if isinstance(value, str):
        root = Path(__file__).resolve().parents[1]
        value = json.loads((root / value).read_text())
    validate(value)
    return value


def validate(value):
    if (value.get('schema') != 1 or value.get('model') != MODEL or
            value.get('model_revision') != MODEL_REVISION or
            value.get('runtime_revision') != RUNTIME_REVISION or
            value.get('task') != 'FREEFORM' or not value.get('instruction') or
            not 0 < value.get('minimum_speaker_cosine', 0) < 1):
        raise ValueError('Unsupported Ming female voice profile')
    if value.get('segmentation') != dict(version=narration_segments.VERSION,
            maximum_units=24, pause_ms=0, assembly='concatenate',
            seed_rule='base+attempt*1000003+span', minimum_decode_budget_seconds=16):
        raise ValueError('Unsupported lossless Ming segmentation profile')
    for field in ('reference_sha256', 'embedding_sha256'):
        if (not isinstance(value.get(field), str) or len(value[field]) != 64 or
                any(c not in '0123456789abcdef' for c in value[field])):
            raise ValueError('Ming profile requires exact reference and embedding hashes')
    if set(value.get('artifacts', {})) != {'runtime', 'model', 'asr'}:
        raise ValueError('Ming profile requires runtime, model and local ASR manifests')
    for kind, artifacts in value['artifacts'].items():
        if not artifacts:
            raise ValueError('Empty Ming artifact manifest: ' + kind)
        for name, expected in artifacts.items():
            path = Path(name)
            if (path.is_absolute() or '..' in path.parts or
                    not isinstance(expected, str) or len(expected) != 64 or
                    any(c not in '0123456789abcdef' for c in expected)):
                raise ValueError('Invalid Ming artifact: ' + name)


def provenance(profile):
    return dict(provider='Ming', model=profile['model'],
                model_revision=profile['model_revision'],
                runtime_revision=profile['runtime_revision'],
                reference_sha256=profile['reference_sha256'],
                embedding_sha256=profile['embedding_sha256'],
                profile_sha256=json_hash(profile))


def text_hash(config, text, profile, code):
    plan = segment_plan(profile, text)
    return json_hash(dict(plan=plan,
                          requests=[request_arguments(profile, span['text'], code, profile['embedding_sha256'])
                                    for span in plan['spans']],
                          seed=profile.get('seed', 20261108),
                          adapter_sha256=file_hash(__file__), synthesis=provenance(profile),
                          sample_rate=config['sample_rate'],
                          opus_bitrate=config.get('opus_bitrate', '16k')))


class Engine:
    def __init__(self, profile, local_path):
        validate(profile)
        self.profile = profile
        self.local = json.loads(Path(local_path).read_text())
        self.model = None
        self.torch = None
        self.asr = None
        self.last_transcription = None
        self.last_generation = None
        root = Path(__file__).resolve().parents[1]
        for field, script in (('adapter_sha256', 'ming_narration.py'),
                              ('asr_adapter_sha256', 'whisper_narration.py'),
                              ('segmenter_sha256', 'narration_segments.py')):
            if profile.get(field) != file_hash(root / 'scripts' / script):
                raise ValueError('Ming adapter source differs from its profile')
        for kind, artifacts in profile['artifacts'].items():
            root = Path(self.local[kind])
            if not root.is_dir():
                raise ValueError('Missing local Ming directory: ' + kind)
            for name, expected in artifacts.items():
                if file_hash(root / name) != expected:
                    raise ValueError('Changed local Ming artifact: ' + kind + '/' + name)
        for kind in ('reference', 'embedding'):
            if file_hash(self.local[kind]) != profile[kind + '_sha256']:
                raise ValueError('Changed Ming female ' + kind)
        command = self.local.get('asr_command')
        if command:
            if (not isinstance(command, list) or not all(isinstance(arg, str) for arg in command) or
                    not any('{audio}' in arg for arg in command) or
                    not any('{language}' in arg for arg in command)):
                raise ValueError('Local ASR command requires audio and language arguments')
            expected = profile.get('asr_command_files', {})
            actual = {str(index): file_hash(arg) for index, arg in enumerate(command)
                      if Path(arg).is_file()}
            if not expected or expected != actual:
                raise ValueError('Local ASR command files differ from their pinned hashes')
        threads = self.local.get('threads', 2)
        if type(threads) is not int or not 1 <= threads <= 4:
            raise ValueError('Ming threads must be between one and four')
        self.threads = threads

    def load(self):
        if self.model is not None:
            return
        os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1',
                          OMP_NUM_THREADS=str(self.threads), MKL_NUM_THREADS=str(self.threads))
        sys.path.insert(0, self.local['runtime'])
        import torch
        from ming_tts import MingTTS
        from importlib.metadata import version
        for package, expected in self.profile.get('environment', {}).items():
            if version(package) != expected:
                raise ValueError('Changed Ming runtime dependency: ' + package)
        torch.set_num_threads(self.threads)
        torch.set_num_interop_threads(1)
        self.torch = torch
        self.model = MingTTS(self.local['model'], device='cpu', text_normalization=False)

    def request_budget(self, text, code):
        """Inspect the actual dense prompt contract, without generating speech."""
        import prompt_contract
        import tts_tasks
        from modeling_bailingmm import MAX_CACHE_LEN
        request = tts_tasks.build_task_generation_kwargs(**request_arguments(
            self.profile, text, code, self.local['embedding']))
        model = self.model.model
        ids, _, _ = prompt_contract.build_input_ids(
            model.tokenizer, model.model_type, request['prompt'], request['text'],
            num_speakers=1, instruction=request['instruction'])
        steps = min(1000, (MAX_CACHE_LEN - len(ids)) // model.patch_size)
        encoder = model.config.audio_tokenizer_config.enc_kwargs
        seconds_per_step = (encoder['hop_size'] * model.config.audio_tokenizer_config.patch_size
                            * model.patch_size / self.model.sample_rate)
        budget = dict(input_tokens=len(ids), cache_tokens=MAX_CACHE_LEN,
                      decode_steps=steps, decode_seconds=steps * seconds_per_step)
        if budget['decode_seconds'] < self.profile['segmentation']['minimum_decode_budget_seconds']:
            raise ValueError('Ming text span leaves insufficient decode cache: ' + str(budget))
        return budget

    def synthesize_span(self, text, code, attempt, index, cache):
        import numpy as np
        import soundfile as sf
        seed = segment_seed(self.profile, attempt, index)
        identity = json_hash(dict(synthesis=provenance(self.profile), text=text,
                                  language=code, seed=seed))
        raw = cache / (identity + '.wav')
        receipt = cache / (identity + '.raw.json')
        budget = self.request_budget(text, code)
        diagnostics = None
        if raw.is_file() and receipt.is_file():
            previous = json.loads(receipt.read_text())
            if previous.get('raw_sha256') == file_hash(raw):
                audio, sample_rate = sf.read(raw, dtype='float32')
                if sample_rate != self.model.sample_rate:
                    raise ValueError('Cached Ming sample rate changed')
                diagnostics = previous
        if diagnostics is None:
            self.torch.manual_seed(seed)
            with self.torch.autocast('cpu', dtype=self.torch.bfloat16):
                audio = self.model.synthesize(**request_arguments(
                    self.profile, text, code, self.local['embedding']))
            audio = audio.detach().float().cpu().numpy().reshape(-1)
            finite = bool(np.isfinite(audio).all())
            diagnostics = dict(identity=identity, seed=seed, samples=len(audio),
                               sample_rate=self.model.sample_rate, finite=finite,
                               raw_peak=float(np.abs(audio).max()) if len(audio) and finite else None,
                               gain=1.0, budget=budget)
            # Persist the finite float waveform before a peak failure. PCM_16
            # would destroy the very overshoot needed for diagnosis.
            if len(audio) and finite:
                temporary = raw.with_suffix('.wav.part')
                sf.write(temporary, audio, self.model.sample_rate, format='WAV', subtype='FLOAT')
                temporary.replace(raw)
                diagnostics['raw_sha256'] = file_hash(raw)
            temporary = receipt.with_suffix('.json.part')
            temporary.write_text(json.dumps(diagnostics, allow_nan=False) + '\n')
            temporary.replace(receipt)
        if not diagnostics['samples'] or not diagnostics['finite']:
            raise RuntimeError('Ming returned invalid waveform: ' + json.dumps(diagnostics))
        if diagnostics['raw_peak'] >= 1:
            raise RuntimeError('Ming finite waveform peak exceeds PCM range: ' + json.dumps(diagnostics))
        return audio, diagnostics

    def speak(self, config, text, code, work, attempt):
        if code not in LANGUAGES:
            raise ValueError('Ming does not support locale ' + code)
        root = Path(__file__).resolve().parents[1]
        cache = root / 'backup/narration/cache'
        subprocess.run(['git', '-C', str(root), 'check-ignore', '-q', str(cache / 'probe')],
                        check=True, capture_output=True)
        cache.mkdir(parents=True, exist_ok=True)
        identity = json_hash(dict(synthesis=provenance(self.profile), text=text,
                                  language=code, attempt=attempt,
                                  request_sha256=text_hash(config, text, self.profile, code),
                                  pcm_sample_rate=config['pcm_sample_rate']))
        cached_pcm = cache / (identity + '.pcm')
        cached_receipt = cache / (identity + '.json')
        if cached_pcm.is_file() and cached_receipt.is_file():
            previous = json.loads(cached_receipt.read_text())
            if previous.get('sha256') == file_hash(cached_pcm):
                self.last_generation = previous['segmentation']
                return cached_pcm.read_bytes(), provenance(self.profile)
        self.load()
        import numpy as np
        import soundfile as sf
        plan = segment_plan(self.profile, text)
        chunks = []
        rows = []
        for index, span in enumerate(plan['spans']):
            audio, diagnostics = self.synthesize_span(span['text'], code, attempt, index, cache)
            chunks.append(audio)
            rows.append(diagnostics)
        audio = np.concatenate(chunks)
        self.last_generation = dict(plan=plan, attempt=attempt, chunks=rows)
        wav = work / 'ming.wav'
        pcm = work / 'ming.pcm'
        sf.write(wav, audio, self.model.sample_rate, subtype='PCM_16')
        subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-threads', '1',
                        '-i', str(wav), '-ac', '1', '-ar', str(config['pcm_sample_rate']),
                        '-f', 's16le', str(pcm)], check=True, capture_output=True)
        temporary = cached_pcm.with_suffix('.pcm.part')
        temporary.write_bytes(pcm.read_bytes())
        temporary.replace(cached_pcm)
        temporary = cached_receipt.with_suffix('.json.part')
        temporary.write_text(json.dumps(dict(sha256=file_hash(cached_pcm), request_sha256=identity,
                                             segmentation=self.last_generation)) + '\n')
        temporary.replace(cached_receipt)
        return pcm.read_bytes(), provenance(self.profile)

    def speaker_match(self, clip):
        """CAMPPlus similarity tests identity consistency, not perceived gender."""
        self.load()
        import numpy as np
        _, actual = self.model._load_prompt([str(clip)])
        reference = self.torch.load(self.local['embedding'], map_location='cpu', weights_only=True)
        first = np.asarray(actual[0]).reshape(-1)
        second = reference.detach().cpu().numpy().reshape(-1)
        denominator = np.linalg.norm(first) * np.linalg.norm(second)
        score = float(np.dot(first, second) / denominator) if denominator else 0.0
        return score if math.isfinite(score) else 0.0

    def transcribe(self, clip, code):
        # The optional interpreter allows reuse of a separate existing local
        # ASR environment. Its wrapper must return JSON, never expected text.
        command = self.local.get('asr_command')
        if command:
            argv = [arg.replace('{audio}', str(clip)).replace('{language}', code)
                    for arg in command]
            result = subprocess.run(argv, check=True, capture_output=True, text=True,
                                    timeout=300)
            if len(result.stdout) > 65536:
                raise RuntimeError('Local ASR returned an oversized transcript')
            row = json.loads(result.stdout)
        else:
            if self.asr is None:
                from whisper_narration import Transcriber
                self.asr = Transcriber(self.local['asr'], self.threads)
            row = self.asr.transcribe(clip, code)
        if (row.get('language') != code or row.get('audio_sha256') != file_hash(clip) or
                row.get('truncation') is not False or not row.get('long_form') or
                not 0 < row.get('seconds', 0) <= 120):
            raise RuntimeError('Local ASR did not verify the complete selected audio')
        self.last_transcription = row
        return row['text'].strip()
