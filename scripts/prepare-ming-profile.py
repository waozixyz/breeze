#!/usr/bin/env python3
"""Fingerprint an existing offline installation; never install or load models."""
import argparse
from importlib.metadata import version
import json
from pathlib import Path

from ming_narration import MODEL, MODEL_REVISION, RUNTIME_REVISION, file_hash, json_hash, validate
from whisper_narration import MODEL as ASR_MODEL, REVISION as ASR_REVISION
import ming_verification

ROOT = Path(__file__).resolve().parents[1]


def artifacts(root, extensions):
    root = Path(root)
    return {path.relative_to(root).as_posix(): file_hash(path)
            for path in sorted(root.rglob('*'))
            if path.is_file() and path.suffix in extensions and
            not any(part.startswith('.') or part == '__pycache__' for part in path.relative_to(root).parts)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--local', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--previous-verification-profile', type=Path,
        help='retain reviewed verifier identities only for unchanged synthesis and locale ASR artifacts')
    args = parser.parse_args()
    local = json.loads(args.local.read_text())
    if args.previous_verification_profile and not local.get('verification_models'):
        parser.error('Previous QA identities require explicit verification models')
    profile = dict(
        schema=1, model=MODEL, model_revision=MODEL_REVISION,
        runtime_revision=RUNTIME_REVISION, voice='inner-breeze-calm-female',
        reference_sha256=file_hash(local['reference']), embedding_sha256=file_hash(local['embedding']),
        task='FREEFORM', seed=20261108, minimum_speaker_cosine=0.70,
        instruction=('Speak softly and slowly, like a calm, caring adult meditation guide. '
                     'Use a natural, airy female voice, low energy and gentle pauses between phrases. '
                     'Read the supplied text exactly in its language without music or extra words.'),
        transcriber=ASR_MODEL + '@' + ASR_REVISION,
        environment={name: version(name) for name in ('torch', 'transformers', 'numpy', 'soundfile')},
        adapter_sha256=file_hash(ROOT / 'scripts/ming_narration.py'),
        asr_adapter_sha256=file_hash(ROOT / 'scripts/whisper_narration.py'),
        segmenter_sha256=file_hash(ROOT / 'scripts/narration_segments.py'),
        segmentation=dict(version=1, maximum_units=24, pause_ms=0, assembly='concatenate',
                          seed_rule='base+attempt*1000003+span', minimum_decode_budget_seconds=16),
        artifacts=dict(runtime=artifacts(local['runtime'], {'.py'}),
                       model=artifacts(local['model'], {'.json', '.txt', '.safetensors', '.bin', '.onnx'}),
                       asr=artifacts(local['asr'], {'.json', '.txt', '.safetensors', '.bin'})),
        documentation=['https://github.com/inclusionAI/Ming-3.0-tts/blob/main/cookbooks/instruction_en.md',
                       'https://huggingface.co/docs/transformers/model_doc/whisper'])
    command = local.get('asr_command')
    if command:
        profile['asr_command_files'] = {str(index): file_hash(arg)
                                        for index, arg in enumerate(command) if Path(arg).is_file()}
    if local.get('verification_models'):
        manifests = {model: artifacts(local['verification_models'][model],
                                      {'.json', '.txt', '.safetensors', '.bin'})
                     for model in ming_verification.MODELS}
        routes = {}
        for code in ming_verification.LANGUAGES:
            model = 'openai/whisper-large-v3-turbo' if code in ('ja', 'ko') else ASR_MODEL
            routes[code] = dict(model=model, revision=ming_verification.MODELS[model],
                                artifacts=manifests[model])
        profile['verification'] = dict(mode='per-locale-whisper-v1', routes=routes,
            adapter_sha256=file_hash(ROOT / 'scripts/ming_verification.py'))
        if args.previous_verification_profile:
            previous = json.loads(args.previous_verification_profile.read_text())
            if ming_verification.synthesis_profile(previous) != ming_verification.synthesis_profile(profile):
                raise ValueError('Cannot reuse QA identities from a different synthesis profile')
            compatible = {}
            for code, route in routes.items():
                candidates = [ming_verification.verification_identity(previous, code)]
                candidates += previous.get('verification', {}).get('compatible', {}).get(code, [])
                retained = []
                for identity in candidates:
                    if (identity and identity['model'] == route['model'] and
                            identity['revision'] == route['revision'] and
                            identity['artifacts_sha256'] == json_hash(route['artifacts']) and
                            identity not in retained):
                        retained.append(identity)
                if retained:
                    compatible[code] = retained
            profile['verification']['compatible'] = compatible
    validate(profile)
    ming_verification.validate(profile)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(profile, indent=2, ensure_ascii=False) + '\n')
    print('Fingerprint saved; no models loaded or audio generated.')


if __name__ == '__main__':
    main()
