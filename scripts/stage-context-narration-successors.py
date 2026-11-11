"""Stage exactly 13 accepted proofs under encoding-safety successor policies.

Reuses actual unchanged ASR/audio evidence. No inference or live writes.
"""
import argparse
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import local_narration_context as context
from practice_media import media_path, narration_text_path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('context_migration', ROOT / 'scripts/stage-context-narration-migration.py')
migration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migration)
require = migration.require
SUCCESSORS = {
    'design/narration/short-context-provider-v2.json': 'design/narration/short-context-provider-v3.json',
    'design/narration/workout-czech-context-provider-v2.json': 'design/narration/workout-czech-context-provider-v3.json',
    'design/narration/tai-chi-short-context-provider-v2.json': 'design/narration/tai-chi-short-context-provider-v3.json',
    'design/narration/workout-czech-count-semantics-v1.json': 'design/narration/workout-czech-count-semantics-v2.json',
}
GENERATOR_SHA = 'c07d404a3a0cd865b2a2ce6fbbc4c0e97c26b39e708afb3d680ad583dd336b38'
HELPER_SHA = 'fcf1d55218627c04fbe787d1b66987d4f7f34e7261822f02e8cc8b2beef47c1f'
POLICY_SHAS = dict(zip(SUCCESSORS, (
    '5a56a9525cb2714868d995709549be6aa171f2ff138a549af3f16908d3670d1f',
    '4558186f263b4880ecadcbd7a8f62f6ef6af460a362c04346d22a61d0ba87596',
    'def352e915dc4e03af25691402ff56201368f6783f7e5dd0f32def7e9e9fde72',
    'e88494e1032f09d7b0c3b5085a4e9a78a65602747fea79c15b74bf36b72d1e13')))


def validate_seals(sealed, original_generator):
    expected = dict(POLICY_SHAS, **{'scripts/generate-lumi-guide-narration.py': GENERATOR_SHA,
                                  'scripts/local_narration_context.py': HELPER_SHA})
    require(sealed == expected, 'Changed predecessor source seals')
    require(context.file_hash(original_generator) == GENERATOR_SHA, 'Changed archived predecessor generator')
    require(context.file_hash(context.__file__) == HELPER_SHA, 'Changed context helper')
    for old, new in SUCCESSORS.items():
        require(context.file_hash(ROOT / old) == POLICY_SHAS[old], 'Changed immutable predecessor policy')
        predecessor = migration.read_json(ROOT / old)
        successor = context.load_policy(ROOT / new)
        require(successor == dict(predecessor, verifier_sha256=context.file_hash(
            ROOT / 'scripts/generate-lumi-guide-narration.py')), 'Successor changed more than its verifier seal')


def reseal_row(speech, practice, config, code, key, text, row, previous, clip):
    full_key = code + '/' + key
    require((practice, full_key) in migration.EXPECTED, 'Outside exact 13-row scope')
    require(row == previous, 'Accepted predecessor row changed: ' + full_key)
    proof = row['speaker_verification']
    require(proof['proof_sha256'] == context.json_hash({k: v for k, v in proof.items()
            if k != 'proof_sha256'}), 'Changed predecessor proof')
    require(context.file_hash(clip) == row['sha256'] == proof['clip_sha256'], 'Changed original clip')
    old_path = proof['policy_path']
    require(old_path in SUCCESSORS, 'Unregistered predecessor policy')
    rule = context.recipe(ROOT / SUCCESSORS[old_path], code, text, proof['voice_directory'])
    require(rule is not None, 'No exact successor rule')
    old_rule = {k: v for k, v in rule.items() if k != 'sha256'}
    old_rule.update(policy_path=old_path, policy_sha256=POLICY_SHAS[old_path])
    require(context.json_hash(old_rule) == proof['recipe_sha256'], 'Changed original recipe semantics')
    module = speech.local_adapter(config, code)
    require(module is not None, 'Missing selected language adapter')
    profile = module.descriptor(config)
    require(module.provenance(profile) == row['synthesis'] == proof['source_identity'], 'Changed synthesis')
    parent = context._parent_source(config, proof, clip)
    require(context.file_hash(parent) == proof['parent']['sha256'], 'Changed parent recording')
    entry = dict(item=dict(practice=practice, config=config, code=code, key=key, text=text, row=row),
                 profile=profile, rule=rule, clip=clip, parent=parent)
    alignment = proof['parent']['alignment']
    crop_asr = row['transcription'] if rule.get('crop_asr') else None
    successor, _ = migration.migrate_row(speech, entry, alignment, crop_asr)
    derived_binding = None
    changed_fields = {'speaker_verification', 'text_sha256'}
    if rule.get('crop_asr'):
        require(practice == 'sunsalutation' and code == 'zh' and key in (
            'sun_salutation_voice_breathe_in', 'sun_salutation_voice_breathe_out'),
            'Unregistered derived context ASR binding')
        previous_identity = row['verification']
        require(previous_identity['profile_sha256'] == POLICY_SHAS[old_path] and
                previous_identity['context_recipe_sha256'] == proof['recipe_sha256'],
                'Changed predecessor derived ASR binding')
        expected_identity = dict(previous_identity, profile_sha256=rule['policy_sha256'],
                                 context_recipe_sha256=rule['sha256'])
        require(successor['verification'] == expected_identity, 'Changed ASR execution identity')
        changed_fields.add('verification')
        derived_binding = dict(previous=previous_identity, successor=expected_identity)
    require({k: v for k, v in successor.items() if k not in changed_fields} ==
            {k: v for k, v in row.items() if k not in changed_fields},
            'Reseal changed unrelated row metadata')
    allowed = {'policy_path', 'recipe_sha256', 'proof_sha256'}
    require({k: v for k, v in successor['speaker_verification'].items() if k not in allowed} ==
            {k: v for k, v in proof.items() if k not in allowed}, 'Reseal changed original evidence')
    evidence = dict(practice=practice, key=full_key, previous_row_sha256=context.json_hash(row),
                    successor_row_sha256=context.json_hash(successor), audio_sha256=row['sha256'],
                    reused_alignment_sha256=context.json_hash(alignment),
                    reused_transcription_sha256=context.json_hash(row['transcription']),
                    previous_proof=proof, derived_binding=derived_binding, inference_executed=False)
    return successor, evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('predecessors', 'sealed', 'original-generator', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    require(output.is_relative_to(ROOT / 'backup/narration'), 'Output must use the owning narration backup store')
    subprocess.run(['git', '-C', str(ROOT), 'check-ignore', '-q', str(output)], check=True)
    require(not output.exists(), 'Output exists; inspect its previous outcome instead of replaying')
    validate_seals(migration.read_json(args.sealed), args.original_generator)
    speech = migration.speech_module()
    surface = migration.read_json(ROOT / 'apps/practice/content.json')['narration']
    originals, candidates, evidence, seen = {}, {}, [], set()
    for practice in ('sunsalutation', 'workout'):
        settings = surface[practice]
        config = migration.read_json(ROOT / settings['config'])
        path = ROOT / settings['receipt']
        raw = path.read_bytes()
        original = json.loads(raw)
        previous = migration.read_json(args.predecessors / (practice + '.json'))
        candidate = copy.deepcopy(original)
        voice = media_path(settings['output_directory'])
        for expected_practice, full_key in sorted(migration.EXPECTED):
            if expected_practice != practice:
                continue
            code, key = full_key.split('/', 1)
            text = speech.entries(narration_text_path(config, code, media_path(settings['text_directory'])))[key].strip()
            row = original['clips'][full_key]
            successor, proof = reseal_row(speech, practice, config, code, key, text, row,
                                           previous['clips'][full_key], voice / code / (key + '.ogg'))
            candidate['clips'][full_key] = successor
            evidence.append(proof)
            seen.add((practice, full_key))
        originals[practice] = dict(path=path, raw=raw, sha256=context.pcm_hash(raw))
        candidates[practice] = candidate
    require(seen == migration.EXPECTED and len(evidence) == 13, 'Incomplete exact successor staging')
    for saved in originals.values():
        require(saved['path'].read_bytes() == saved['raw'], 'Live receipt changed during staging')
    output.mkdir()
    (output / 'original-receipts').mkdir()
    (output / 'receipt-candidates').mkdir()
    for practice, candidate in candidates.items():
        (output / 'original-receipts' / (practice + '.json')).write_bytes(originals[practice]['raw'])
        migration.write_json(output / 'receipt-candidates' / (practice + '.json'), candidate)
    migration.write_json(output / 'evidence.json', dict(rows=13, inference_executed=False,
        production_written=False, generator_sha256=context.file_hash(ROOT / 'scripts/generate-lumi-guide-narration.py'),
        helper_sha256=HELPER_SHA, changes=evidence,
        live_predecessor_sha256={k: v['sha256'] for k, v in originals.items()},
        policies={new: context.file_hash(ROOT / new) for new in SUCCESSORS.values()}))
    print('13 exact context successor proofs staged; original evidence preserved; no inference or live writes.')


if __name__ == '__main__':
    try:
        main()
    except (KeyError, ValueError, OSError) as error:
        sys.exit(str(error))
