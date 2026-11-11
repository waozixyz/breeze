#!/usr/bin/env python3
"""Prepare explicit local profiles; pilot and speaker QA never fetch models."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

from f5_russian_narration import file_hash

ROOT = Path(__file__).resolve().parents[1]
STORE = ROOT / 'backup/narration/local-models'
MODELS = Path('/mnt/storage/Projects/harness/models/weights/tts')
JUNGLE = Path('/mnt/storage/Projects/waozixyz/learning/jungle/local/speech-development')


def prepare(code):
    subprocess.run(['git', '-C', str(ROOT), 'check-ignore', '-q', str(STORE / 'probe')], check=True)
    import f5_russian_narration as ru
    adapter = __import__({'ru':'f5_russian_narration','cs':'chatterbox_czech_narration','pt':'chatterbox_portuguese_narration'}[code])
    reference_key = 'settings_guide_audio' if code == 'cs' else 'profile_guide_you'
    source = Path('/mnt/storage/Projects/waozixyz/modules/practices/guide/voice') / code / (reference_key+'.ogg')
    reference = STORE / ('reference-' + code + '.wav')
    subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-i', str(source), '-ar', '24000',
                    '-ac', '1', str(reference)], check=True)
    text = (ROOT / ('locales/' + code + '.txt')).read_text().split('['+reference_key+']\n')[1].split('\n---')[0]
    interpreter = STORE / ('f5-venv' if code == 'ru' else 'czech-venv') / 'bin/python'
    asr_root = Path('/mnt/storage/Projects/harness/models/weights/asr') / ('whisper-small' if code == 'ru' else 'whisper-large-v3-turbo')
    asr = [str(JUNGLE / 'ming-evaluation/venv/bin/python'), str(ROOT / 'scripts/whisper_narration.py'),
           '--model', str(Path('/mnt/storage/Projects/harness/models/weights/asr/whisper-small')), '--audio', '{audio}', '--language', '{language}']
    if code != 'ru':
        asr = [asr[0], str(Path(__file__).resolve()), '--asr-audio', '{audio}', '--asr-language', '{language}']
    speaker = [asr[0], str(Path(__file__).resolve()), '--speaker', '{audio}', '--reference', str(reference)]
    files = ['f5-russian/model.safetensors', 'f5-russian/vocab.txt', 'vocos-mel-24khz/config.yaml', 'vocos-mel-24khz/pytorch_model.bin'] if code == 'ru' else (['chatterbox-czech/t3_cs.safetensors', 'chatterbox-multilingual/ve.pt', 'chatterbox-multilingual/s3gen.pt', 'chatterbox-multilingual/grapheme_mtl_merged_expanded_v1.json', 'chatterbox-multilingual/Cangjie5_TC.json'] if code == 'cs' else ['chatterbox-portuguese/'+name for name in ['tokenizer.json','conds.pt','ve.safetensors','t3_cfg.safetensors','s3gen.safetensors']])
    ready = all((MODELS / f).is_file() for f in files)
    environment = json.loads(subprocess.check_output([str(interpreter), '-c',
        'import importlib.metadata as m,json;print(json.dumps({d.metadata["Name"]:d.version for d in m.distributions()}))'])) if interpreter.exists() else {}
    local = dict(models=str(MODELS), reference=str(reference), cache=str(STORE / 'cache'),
                 threads=4, asr=str(asr_root), asr_command=asr, speaker_command=speaker, python=str(interpreter))
    profile = dict(schema=1, provider={'ru':'F5Russian','cs':'ChatterboxCzech','pt':'ChatterboxPortuguese'}[code],
                   status='ready' if ready else 'pending-model-artifacts', locale=code,
                   model=adapter.MODEL, model_revision=adapter.MODEL_REVISION,
                   license={'ru':'cc-by-nc-4.0','cs':'cc0-1.0','pt':'mit'}[code],
                   runtime_version='1.1.22' if code == 'ru' else '0.1.6',
                   adapter_sha256=file_hash(adapter.__file__), reference_sha256=file_hash(reference),
                   reference_text=text, reference_source='guide/voice/' + code + '/' + reference_key + '.ogg',
                   reference_source_sha256=file_hash(source), reference_voice='Leda',
                   speaker_evidence='CAMPPlus cosine measures consistency, not perceived gender',
                   transcriber='openai/whisper-small' if code == 'ru' else 'openai/whisper-large-v3-turbo',
                   asr_revision='973afd24965f72e36ca33b3055d56a652f456b4d' if code == 'ru' else '41f01f3fe87f28c78e2fbf8b568835947dd65ed9', minimum_speaker_cosine=0.65,
                   seed=20261108, threads=local['threads'], peak_ceiling=0.95, environment=environment,
                   parameters=dict(nfe_step=32, cfg_strength=2.0, sway_sampling_coef=-1.0, speed=1.0,
                                   target_rms=0.1, cross_fade_duration=0.15) if code == 'ru' else dict(exaggeration=0.3, cfg_weight=0.5, temperature=0.8, repetition_penalty=2.0, min_p=0.05, top_p=1.0),
                   artifacts={f:file_hash(MODELS / f) for f in files if (MODELS / f).exists()},
                   asr_command_files={str(i):file_hash(p) for i,p in enumerate(asr) if Path(p).is_file()},
                   speaker_command_files={str(i):file_hash(p) for i,p in enumerate(speaker) if Path(p).is_file()})
    camp = MODELS / 'ming-3.0-tts-0.5b/campplus.onnx'
    profile['speaker_model_sha256'] = file_hash(camp)
    profile['speaker_runtime_sha256'] = file_hash(JUNGLE / 'ming-evaluation/runtime/spkemb_extractor.py')
    profile['asr_artifacts'] = {str(p.relative_to(asr_root)):file_hash(p) for p in asr_root.rglob('*') if p.is_file() and '.cache' not in p.parts}
    if code == 'cs':
        profile['base_adapter_sha256'] = file_hash(ru.__file__)
        profile['base_model'] = dict(model='ResembleAI/chatterbox', revision='5bb1f6ee58e50c3b8d408bc82a6d3740c2db6e18', license='mit')
        profile['language_id'] = 'cs'
        profile['language_token_id'] = 719
        profile['normalization'] = 'NFKD'
        profile['parameters']['exaggeration'] = 0.5
        profile['tokenizer_adaptation'] = 'Explicit native [cs] tokenizer token; scoped upstream registry extension; local mapping; unused Chinese segmenter disabled. Untagged model-card pilot failed ASR.'
    if code == 'pt':
        profile['base_adapter_sha256'] = file_hash(ru.__file__)
        profile['parameters'].update(exaggeration=0.5, repetition_penalty=1.2)
        profile['segmentation'] = dict(mode='bounded-text-v1', maximum_characters=160, pause_seconds=0.12)
    if code == 'ru':
        profile['vocoder'] = dict(model='charactr/vocos-mel-24khz', revision='0feb3fdd929bcd6649e0e7c5a688cf7dd012ef21')
    source_names = ['f5_russian_narration.py', 'prepare-local-voice-profile.py', 'whisper_narration.py']
    if code == 'cs': source_names.append('chatterbox_czech_narration.py')
    if code == 'pt': source_names.append('chatterbox_portuguese_narration.py')
    profile['source_files'] = {name:file_hash(ROOT / 'scripts' / name) for name in source_names}
    path = ROOT / ('design/narration/'+{'ru':'f5-russian','cs':'chatterbox-czech','pt':'chatterbox-portuguese'}[code]+'.json')
    path.write_text(json.dumps(profile, indent=2, ensure_ascii=False) + '\n')
    (STORE / (code + '-local.json')).write_text(json.dumps(local, indent=2) + '\n')
    print(json.dumps(dict(locale=code, status=profile['status'], reference_sha256=profile['reference_sha256'])))


def speaker(audio, reference):
    import numpy as np
    import torch
    torch.set_num_threads(2)
    sys.path.insert(0, str(JUNGLE / 'ming-evaluation/runtime'))
    from spkemb_extractor import SpkembExtractor
    model = MODELS / 'ming-3.0-tts-0.5b/campplus.onnx'
    extractor = SpkembExtractor(str(model))
    def embedding(path):
        raw = subprocess.check_output(['ffmpeg', '-nostdin', '-v', 'error', '-threads', '1', '-i', str(path),
                                       '-ac', '1', '-ar', '16000', '-f', 'f32le', '-'])
        return extractor(torch.from_numpy(np.frombuffer(raw, dtype='<f4').copy()).unsqueeze(0)).numpy().reshape(-1)
    a,b = embedding(audio), embedding(reference)
    cosine = float(np.dot(a,b) / (np.linalg.norm(a)*np.linalg.norm(b)))
    print(json.dumps(dict(cosine=cosine, model_sha256=file_hash(model), audio_sha256=file_hash(audio),
                          reference_sha256=file_hash(reference), gender_verified=False,
                          runtime_sha256=file_hash(JUNGLE / 'ming-evaluation/runtime/spkemb_extractor.py'))))


def cue_definition(key):
    canonical = Path('/mnt/storage/Projects/waozixyz/modules/practices')
    definitions = [('design/lumi-guide/narration.json', ROOT / 'locales'),
                   ('design/astral-projection/bruce-narration.json', canonical / 'astral_projection/text'),
                   ('design/sun-salutation/narration/narration.json', ROOT / 'design/sun-salutation/narration/text')]
    for name, directory in definitions:
        config = json.loads((ROOT / name).read_text())
        keys = config.get('keys') or json.loads((ROOT / config['keys_file']).read_text())
        if key in keys: return config, directory
    raise ValueError('Pilot key must be a registered guide or practice cue')


def pilot(code, cue_key=None, attempt=0):
    module = __import__({'ru':'f5_russian_narration','cs':'chatterbox_czech_narration','pt':'chatterbox_portuguese_narration'}[code])
    profile = json.loads((ROOT / ('design/narration/'+{'ru':'f5-russian','cs':'chatterbox-czech','pt':'chatterbox-portuguese'}[code]+'.json')).read_text())
    engine = module.Engine(profile, STORE / (code + '-local.json'))
    work = STORE / ('pilot-' + code + ('-' + cue_key if cue_key else '') + ('-attempt'+str(attempt) if attempt else ''))
    text = {'ru':'Расслабь плечи и спокойно дыши.','cs':'Uvolni ramena a klidně dýchej.','pt':'Relaxe os ombros e respire com calma.'}[code]
    if cue_key:
        _, text_directory = cue_definition(cue_key)
        text = (text_directory / (code+'.txt')).read_text().split('['+cue_key+']\n')[1].split('\n---')[0]
    config = dict(pcm_sample_rate=24000, sample_rate=16000, opus_bitrate='16k')
    pcm, identity = engine.speak(config, text, code, work, attempt)
    clip = work / 'pilot.ogg'
    subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-f', 's16le', '-ar', '24000', '-ac', '1',
                    '-i', '-', '-ar', '16000', '-c:a', 'libopus', '-b:a', '16k', str(clip)], input=pcm, check=True)
    receipt = dict(expected=text, cue_key=cue_key, attempt=attempt, synthesis=identity, pcm_seconds=len(pcm)/48000, amplitude=engine.last_synthesis, clip_sha256=file_hash(clip))
    (work / 'synthesis.json').write_text(json.dumps(receipt, indent=2, ensure_ascii=False)+'\n')
    print(json.dumps(receipt, ensure_ascii=False))


def qa(code, cue_key=None, attempt=0):
    import array
    module = __import__({'ru':'f5_russian_narration','cs':'chatterbox_czech_narration','pt':'chatterbox_portuguese_narration'}[code])
    profile_path = ROOT / ('design/narration/'+{'ru':'f5-russian','cs':'chatterbox-czech','pt':'chatterbox-portuguese'}[code]+'.json')
    engine = module.Engine(json.loads(profile_path.read_text()), STORE / (code + '-local.json'))
    work = STORE / ('pilot-' + code + ('-' + cue_key if cue_key else '') + ('-attempt'+str(attempt) if attempt else ''))
    clip = work / 'pilot.ogg'
    text = engine.transcribe(clip, code)
    score = engine.speaker_match(clip)
    raw = subprocess.check_output(['ffmpeg', '-nostdin', '-v', 'error', '-i', str(clip),
                                   '-ac', '1', '-ar', '16000', '-f', 's16le', '-'])
    samples = array.array('h', raw)
    synthesis = json.loads((work / 'synthesis.json').read_text())
    receipt = dict(expected=synthesis['expected'], actual=text, asr=engine.last_transcription,
                   speaker_cosine=score, decoded_samples=len(samples), decoded_seconds=len(samples)/16000,
                   decoded_peak=max(abs(n) for n in samples)/32768, gender_verified=False)
    import importlib.util
    spec = importlib.util.spec_from_file_location('pilot_verifier', ROOT / 'scripts/generate-lumi-guide-narration.py')
    verifier = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(verifier)
    config = cue_definition(cue_key)[0] if cue_key else dict(minimum_match=0.92)
    budget = verifier.maximum_clip_seconds(config, cue_key) if cue_key else 40.0
    receipt['match'] = verifier.complete_match(config, code, receipt['expected'], text, receipt['decoded_seconds'], True)
    receipt['maximum_seconds'] = budget
    receipt['accepted'] = (receipt['match'] >= config['minimum_match'] and score >= engine.profile['minimum_speaker_cosine'] and receipt['decoded_seconds'] <= budget and receipt['decoded_peak'] < 1)
    (work / 'qa.json').write_text(json.dumps(receipt, indent=2, ensure_ascii=False)+'\n')
    print(json.dumps(receipt, ensure_ascii=False))
    return receipt['accepted']


def turbo_asr(rows):
    """Blind diagnostic with the pinned stronger recognizer; no expected text input."""
    os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', OMP_NUM_THREADS='2', MKL_NUM_THREADS='2')
    import numpy as np
    import torch
    from transformers import WhisperProcessor, WhisperForConditionalGeneration
    torch.set_num_threads(2)
    metadata = json.loads((STORE / 'whisper-turbo-model.json').read_text())
    model_path = Path('/mnt/storage/Projects/harness/models/weights/asr/whisper-large-v3-turbo')
    if metadata['model'] != 'openai/whisper-large-v3-turbo' or metadata['revision'] != '41f01f3fe87f28c78e2fbf8b568835947dd65ed9':
        raise ValueError('Unpinned diagnostic recognizer')
    for name, digest in metadata['artifacts'].items():
        if file_hash(model_path / name) != digest: raise ValueError('Changed ASR model: ' + name)
    processor = WhisperProcessor.from_pretrained(model_path, local_files_only=True)
    model = WhisperForConditionalGeneration.from_pretrained(model_path, local_files_only=True, low_cpu_mem_usage=True).eval()
    results = []
    for item in rows:
        if set(item) != {'audio', 'language'}: raise ValueError('Blind ASR accepts only audio and language')
        path = Path(item['audio'])
        raw = subprocess.check_output(['ffmpeg', '-nostdin', '-v', 'error', '-threads', '1', '-i', str(path),
                                       '-ac', '1', '-ar', '16000', '-f', 'f32le', '-'])
        audio = np.frombuffer(raw, dtype='<f4').copy()
        if not 0 < len(audio) <= 16000*120 or not np.isfinite(audio).all(): raise ValueError('Invalid complete QA audio')
        features = processor(audio, sampling_rate=16000, return_tensors='pt', truncation=False,
                             padding='longest', return_attention_mask=True)
        with torch.inference_mode():
            tokens = model.generate(input_features=features.input_features, attention_mask=features.attention_mask,
                                    language=item['language'], task='transcribe', return_timestamps=True,
                                    max_new_tokens=440, do_sample=False)
        results.append(dict(audio=str(path), text=processor.batch_decode(tokens, skip_special_tokens=True)[0].strip(),
                            language=item['language'], model=metadata['model'], revision=metadata['revision'],
                            audio_sha256=file_hash(path), input_samples=len(audio), seconds=len(audio)/16000,
                            truncation=False, long_form=True))
    return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare', choices=['ru', 'cs', 'pt'])
    parser.add_argument('--pilot', choices=['ru', 'cs', 'pt'])
    parser.add_argument('--qa', choices=['ru', 'cs', 'pt'])
    parser.add_argument('--diagnose-asr', type=Path)
    parser.add_argument('--cue-key')
    parser.add_argument('--attempt', type=int, choices=range(4), default=0)
    parser.add_argument('--asr-audio', type=Path)
    parser.add_argument('--asr-language', choices=['ru','cs','pt'])
    parser.add_argument('--speaker', type=Path)
    parser.add_argument('--reference', type=Path)
    args = parser.parse_args()
    if args.prepare: prepare(args.prepare)
    elif args.pilot: pilot(args.pilot, args.cue_key, args.attempt)
    elif args.qa: sys.exit(0 if qa(args.qa, args.cue_key, args.attempt) else 1)
    elif args.diagnose_asr: print(json.dumps(turbo_asr(json.loads(args.diagnose_asr.read_text())), ensure_ascii=False))
    elif args.asr_audio and args.asr_language: print(json.dumps(turbo_asr([dict(audio=str(args.asr_audio),language=args.asr_language)])[0], ensure_ascii=False))
    elif args.speaker and args.reference: speaker(args.speaker, args.reference)
    else: parser.error('Select --prepare, --pilot or --speaker with --reference')
