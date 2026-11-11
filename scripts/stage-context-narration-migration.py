"""Audit 13 frozen context proofs; stage successors from separately scheduled ASR.

Never runs inference, creates engines, changes audio, or writes live receipts.
Without --results this only audits and writes a 15-job plan. With --results all
13 rows must pass offline verification before any candidates are saved.
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
INVENTORY_SHA = '71d59ebd66e6ec165d6e60ee1f15330f48e18553dccc511be2584ccd0a74c42e'
FROZEN_SHA = '62e4355f018384a884a0115cfac5f7431aea6c45ef250f5a58e759e96fa37114'
SUCCESSORS = {
    'design/narration/short-context.json': 'design/narration/short-context-provider-v2.json',
    'design/narration/workout-czech-context.json': 'design/narration/workout-czech-context-provider-v2.json',
}
EXPECTED = {
    ('sunsalutation', code + '/sun_salutation_voice_breathe_' + direction)
    for code in ('cs', 'es', 'fr', 'pt', 'ru', 'zh') for direction in ('in', 'out')
} | {('workout', 'cs/workout_say_go')}


def speech_module():
    spec = importlib.util.spec_from_file_location('migration_speech', ROOT / 'scripts/generate-lumi-guide-narration.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_json(path):
    with Path(path).open() as source:
        return json.load(source)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def write_json(path, value):
    with Path(path).open('x') as output:
        json.dump(value, output, ensure_ascii=False, indent=2, allow_nan=False)
        output.write('\n')


def frozen_inputs(inventory_path, frozen_path, sealed_path):
    require(context.file_hash(inventory_path) == INVENTORY_SHA, 'Changed original inventory')
    require(context.file_hash(frozen_path) == FROZEN_SHA, 'Changed frozen context rows')
    inventory = read_json(inventory_path)
    sealed = read_json(sealed_path)
    required = {'scripts/local_narration_context.py', 'scripts/generate-lumi-guide-narration.py',
                *SUCCESSORS.values(), 'design/narration/tai-chi-short-context-provider-v2.json',
                'design/narration/workout-czech-count-semantics-v1.json'}
    require(set(sealed) == required, 'Incomplete sealed bindings')
    for name, digest in sealed.items():
        require(context.file_hash(ROOT / name) == digest, 'Changed sealed source: ' + name)
    with Path(frozen_path).open() as source:
        rows = [json.loads(line) for line in source]
    keys = [(row['practice'], row['code'] + '/' + row['key']) for row in rows]
    require(len(keys) == 13 and set(keys) == EXPECTED, 'Expected frozen 13 rows')
    old = {(row['practice'], row['key']): row for row in inventory['context_rows']}
    require(len(old) == 13 and set(old) == EXPECTED, 'Changed inventory scope')
    return inventory, rows, old


def audit(speech, inventory, rows, old, media):
    receipts, audited = {}, []
    surface = read_json(ROOT / 'apps/practice/content.json')['narration']
    for item in rows:
        practice, code, key = item['practice'], item['code'], item['key']
        full_key = code + '/' + key
        info = inventory['practices'][practice]
        config = read_json(ROOT / info['config'])
        require(config == item['config'], 'Changed configuration: ' + practice)
        path = ROOT / info['receipt']
        if practice not in receipts:
            receipts[practice] = dict(path=path, sha256=context.file_hash(path), document=read_json(path))
            require(context.file_hash(path) == receipts[practice]['sha256'], 'Receipt changed during audit')
        row = receipts[practice]['document']['clips'][full_key]
        require(row == item['row'], 'Target row changed: ' + full_key)
        proof, previous = row['speaker_verification'], old[practice, full_key]
        require(proof['proof_sha256'] == previous['proof_sha256'] == context.json_hash(
            {k: v for k, v in proof.items() if k != 'proof_sha256'}), 'Changed original proof')
        require(proof['recipe_sha256'] == previous['recipe_sha256'] and
                context.file_hash(ROOT / proof['policy_path']) == previous['policy_sha256'], 'Changed old policy')
        require(context.json_hash(proof['parent']['alignment']) == previous['alignment_sha256'],
                'Changed original alignment')
        voice = proof['voice_directory']
        clip = media / voice / code / (key + '.ogg')
        require(context.file_hash(clip) == row['sha256'] == previous['clip_sha256'] == item['clip_sha256'],
                'Changed clip: ' + full_key)
        parent = context._parent_source(config, proof, clip)
        pcm = context.read_wav(parent)
        require(context.file_hash(parent) == previous['parent_sha256'] == proof['parent']['sha256'] and
                context.pcm_hash(pcm) == previous['parent_pcm_sha256'], 'Changed parent audio')
        require(context.packet_hash(clip) == proof['crop']['encoded_packets_sha256'], 'Changed crop packets')
        require(context.pcm_hash(pcm[proof['crop']['start_sample'] * 2:proof['crop']['end_sample'] * 2]) ==
                proof['crop']['pcm_sha256'], 'Changed PCM crop')
        source = narration_text_path(config, code, speech.media_path(surface[practice]['text_directory']))
        require(speech.entries(source)[key].strip() == item['text'], 'Changed requested text')
        module = speech.local_adapter(config, code)
        require(module is not None, 'Missing selected local adapter')
        profile = module.descriptor(config)
        require(module.provenance(profile) == row['synthesis'] == proof['source_identity'], 'Changed synthesis')
        rule = context.recipe(ROOT / SUCCESSORS[proof['policy_path']], code, item['text'], voice)
        require(rule is not None and rule['parent_text'] == proof['parent']['text'], 'Changed parent request')
        speech.VOICE = media / voice
        require(not speech.current(receipts[practice]['document'], config, code, key, item['text']),
                'Original unexpectedly current; inspect prior outcome before replay')
        audited.append(dict(item=item, profile=profile, rule=rule, clip=clip, parent=parent))
    return receipts, audited


def stem(entry):
    item = entry['item']
    return item['practice'] + '--' + item['code'] + '--' + item['key']


def jobs(audited, local, results):
    plan = []
    for entry in audited:
        item = entry['item']
        tasks = [('alignment', '--align-audio', entry['parent'])]
        if entry['rule'].get('crop_asr'):
            tasks.append(('transcription', '--transcribe-audio', entry['clip']))
        for kind, flag, audio in tasks:
            command = ['build-queue', '--', local['python'], str(ROOT / 'scripts/local_narration_context.py'),
                       flag, str(audio), '--language', item['code'], '--model', local['model'],
                       '--policy', str(ROOT / entry['rule']['policy_path'])]
            plan.append(dict(kind=kind, practice=item['practice'], key=item['code'] + '/' + item['key'],
                audio_sha256=context.file_hash(audio), output=str(results / (stem(entry) + '.' + kind + '.json')),
                command=command))
    require(len(plan) == 15, 'Expected 13 parent and two crop jobs')
    return plan


def migrate_row(speech, entry, alignment, crop_transcription=None):
    item, rule, profile = entry['item'], entry['rule'], entry['profile']
    code, text = item['code'], item['text']
    row = copy.deepcopy(item['row'])
    proof = row['speaker_verification']
    old_proof = copy.deepcopy(proof)
    require(alignment.get('helper_sha256') == context.file_hash(context.__file__) and
            alignment.get('audio_sha256') == proof['parent']['sha256'], 'Stale or mismatched ASR execution')
    pcm = context.read_wav(entry['parent'])
    start, end = context.prefix_range(text, alignment, len(pcm) // 2,
        retain_leading_pcm0=rule.get('prefix_alignment') == context.RETAIN_LEADING_PCM0,
        comparison=context.rule_comparison(rule))
    require((start, end) == (proof['crop']['start_sample'], proof['crop']['end_sample']),
            'Fresh alignment changed crop boundaries; original recording cannot be migrated')
    proof.update(policy_path=rule['policy_path'], recipe_sha256=rule['sha256'])
    proof['parent']['alignment'] = copy.deepcopy(alignment)
    proof['proof_sha256'] = context.json_hash({k: v for k, v in proof.items() if k != 'proof_sha256'})
    if rule.get('crop_asr'):
        require(crop_transcription is not None, 'Missing fresh Chinese crop ASR')
        row['transcription'] = copy.deepcopy(crop_transcription)
        row['transcript'] = crop_transcription['text'].strip()
        row['verification'] = speech.context_verification_identity(profile, code, proof)
        row['transcriber'] = row['verification']['model'] + '@' + row['verification']['revision']
    else:
        require(crop_transcription is None, 'Unexpected replacement of ordinary crop ASR')
    row['text_sha256'] = speech.text_hash(item['config'], text, code, row['synthesis'], proof)
    row['match'] = speech.assessment(item['config'], code, text, row['transcript'], row['seconds'], True,
                                     speaker_verification=proof)[0]
    speech.VOICE = entry['clip'].parent.parent
    require(speech.current({'clips': {code + '/' + item['key']: row}}, item['config'], code, item['key'], text),
            'Successor failed complete offline validation: ' + code + '/' + item['key'])
    provenance = dict(previous_row_sha256=context.json_hash(item['row']),
        previous_proof=old_proof, previous_transcription=item['row']['transcription'],
        previous_verification=item['row'].get('verification'),
        fresh_alignment_sha256=context.json_hash(alignment),
        fresh_crop_transcription_sha256=context.json_hash(crop_transcription) if crop_transcription else None)
    return row, provenance


def stage(speech, receipts, audited, results):
    candidates = {name: copy.deepcopy(saved['document']) for name, saved in receipts.items()}
    changes = []
    for entry in audited:
        alignment = read_json(results / (stem(entry) + '.alignment.json'))
        crop = read_json(results / (stem(entry) + '.transcription.json')) if entry['rule'].get('crop_asr') else None
        row, provenance = migrate_row(speech, entry, alignment, crop)
        item = entry['item']
        key = item['code'] + '/' + item['key']
        candidates[item['practice']]['clips'][key] = row
        changes.append(dict(practice=item['practice'], key=key, **provenance))
    for saved in receipts.values():
        require(context.file_hash(saved['path']) == saved['sha256'], 'Receipt writer changed during staging')
    return candidates, changes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('inventory', 'frozen', 'sealed', 'context-local', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--results', type=Path, help='Existing separately scheduled ASR outputs; never runs them')
    args = parser.parse_args()
    media = media_path('assets/practices/').resolve()
    output = args.output.resolve()
    require(output.is_relative_to(ROOT / 'backup/narration') or output.is_relative_to(media / 'backup/narration'),
            'Output must be in the owning ignored narration backup store')
    owner = ROOT if output.is_relative_to(ROOT) else media
    subprocess.run(['git', '-C', str(owner), 'check-ignore', '-q', str(output)], check=True)
    require(not output.exists(), 'Output already exists; inspect the prior outcome instead of replaying')
    inventory, rows, old = frozen_inputs(args.inventory, args.frozen, args.sealed)
    speech = speech_module()
    receipts, audited = audit(speech, inventory, rows, old, media)
    plan = jobs(audited, read_json(args.context_local), output / 'asr-results')
    candidates, changes = stage(speech, receipts, audited, args.results) if args.results else ({}, [])
    # Failed or incomplete ASR evidence leaves no staged receipt output.
    output.mkdir(parents=True)
    write_json(output / 'audit.json', dict(rows=13, stale=13, inference_executed=False,
        source_bindings=read_json(args.sealed), inventory_sha256=INVENTORY_SHA, frozen_sha256=FROZEN_SHA,
        rows_audited=[dict(practice=e['item']['practice'], key=e['item']['code'] + '/' + e['item']['key'],
            current=False, clip_sha256=e['item']['row']['sha256'],
            previous_proof_sha256=e['item']['row']['speaker_verification']['proof_sha256'],
            successor_recipe_sha256=e['rule']['sha256']) for e in audited]))
    write_json(output / 'asr-job-plan.json', plan)
    if candidates:
        (output / 'original-receipts').mkdir()
        (output / 'receipt-candidates').mkdir()
        for practice, receipt in candidates.items():
            write_json(output / 'original-receipts' / (practice + '.json'), receipts[practice]['document'])
            write_json(output / 'receipt-candidates' / (practice + '.json'), receipt)
        write_json(output / 'migration-evidence.json', dict(changes=changes, production_written=False))
    print('13 original proofs audited; 15 ASR jobs planned; ' +
          ('13 successor rows staged.' if candidates else 'fresh ASR evidence still required.'))


if __name__ == '__main__':
    try:
        main()
    except (KeyError, ValueError, OSError) as error:
        sys.exit(str(error))
