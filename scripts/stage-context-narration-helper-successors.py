"""Stage fifteen helper-successor proofs; no inference, encoding or live writes."""
import argparse
import importlib.util
from pathlib import Path
import subprocess
import local_narration_context as context
from practice_media import media_path, narration_text_path
ROOT = Path(__file__).resolve().parents[1]
INVENTORY_SHA = 'c26a9b63f0bbcbdce373632ec4a59b3bead05b9e29c112bc839bef4c503494d1'
VERIFIER_PREVIOUS = 'a89de167b6f76b428437c22116a0647dd85a3cdb6e8ac58c01e1af5d754fa02f'
VERIFIER_SUCCESSOR = '7c16b2311d476322e31a4d8f187d585fc0c482a9e50440bd2775965cd681bb27'
EXPECTED = {('sunsalutation', code + '/sun_salutation_voice_breathe_' + direction)
            for code in ('cs','es','fr','pt','ru','zh') for direction in ('in','out')} | {
    ('workout','cs/workout_say_go'), ('workout','pt/workout_say_push_up_rotation'),
    ('workout','pt/workout_say_switch')}
SUCCESSORS = {
    'design/narration/short-context-provider-v3.json': 'design/narration/short-context-provider-v4.json',
    'design/narration/workout-czech-context-provider-v3.json': 'design/narration/workout-czech-context-provider-v4.json',
    'design/narration/workout-portuguese-context-v1.json': 'design/narration/workout-portuguese-context-v3.json'}
spec = importlib.util.spec_from_file_location('helper_migration', ROOT / 'scripts/stage-context-narration-migration.py')
migration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migration)
require, read_json, write_json = migration.require, migration.read_json, migration.write_json


def inventory(path):
    require(context.file_hash(path) == INVENTORY_SHA, 'Changed reviewed inventory')
    manifest = read_json(path)
    rows = manifest['accepted_context_inventory']
    keys = [(r['practice'], r['key']) for r in rows]
    require(len(keys) == 15 and set(keys) == EXPECTED, 'Expected fifteen registered context rows')
    require(manifest['unique_parent_count'] == len({r['parent'] for r in rows}) == 15, 'Changed parent scope')
    for field in ('unchanged_public_policy_pins', 'unchanged_runtime_and_source_pins'):
        for name, digest in manifest[field].items():
            expected = digest
            if name == 'scripts/generate-lumi-guide-narration.py':
                require(digest == VERIFIER_PREVIOUS, 'Changed predecessor verifier pin')
                expected = VERIFIER_SUCCESSOR
            require(context.file_hash(ROOT / name) == expected, 'Changed immutable source: ' + name)
    return manifest


def audit(speech, manifest):
    surface = read_json(ROOT / 'apps/practice/content.json')['narration']
    receipts, audited = {}, []
    for old in manifest['accepted_context_inventory']:
        practice, full_key = old['practice'], old['key']
        code, key = full_key.split('/', 1)
        settings = surface[practice]
        config = read_json(ROOT / settings['config'])
        path = ROOT / settings['receipt']
        if practice not in receipts:
            receipts[practice] = dict(path=path, sha256=context.file_hash(path), document=read_json(path))
        row = receipts[practice]['document']['clips'][full_key]
        require(context.json_hash(row) == old['row_sha256'], 'Changed accepted row: ' + full_key)
        proof = row['speaker_verification']
        require(proof['proof_sha256'] == old['proof_sha256'] == context.json_hash(
            {k:v for k,v in proof.items() if k != 'proof_sha256'}), 'Changed original proof')
        require(proof['policy_path'] == old['old_policy'] and
                context.file_hash(ROOT / proof['policy_path']) == old['old_policy_sha256'], 'Changed predecessor policy')
        clip, parent = Path(old['clip']), Path(old['parent'])
        voice = media_path(settings['output_directory']).resolve()
        require(clip == voice / code / (key + '.ogg'), 'Noncanonical clip')
        require(context.file_hash(clip) == old['clip_sha256'] == row['sha256'] == proof['clip_sha256'], 'Changed clip')
        require(context._parent_source(config, proof, clip).resolve() == parent, 'Changed parent path')
        require(context.file_hash(parent) == old['parent_sha256'] == proof['parent']['sha256'], 'Changed parent WAV')
        pcm = context.read_wav(parent)
        require(context.pcm_hash(pcm) == old['parent_pcm_sha256'] == proof['parent']['pcm_sha256'], 'Changed parent PCM')
        require(context.json_hash(proof['parent']['alignment']) == old['parent_alignment_sha256'], 'Changed original ASR')
        require(context.json_hash(row['transcription']) == old['old_transcription_sha256'], 'Changed crop ASR')
        bounds = proof['crop']['start_sample'], proof['crop']['end_sample']
        require(list(bounds) == old['crop_samples'] and bounds[0] == 0, 'Changed crop boundaries')
        require(context.pcm_hash(pcm[bounds[0]*2:bounds[1]*2]) == proof['crop']['pcm_sha256'] and
                context.packet_hash(clip) == proof['crop']['encoded_packets_sha256'], 'Changed contiguous crop or packets')
        text = speech.entries(narration_text_path(config, code,
            media_path(settings['text_directory'])))[key].strip()
        module = speech.local_adapter(config, code)
        require(module is not None, 'Missing local provider')
        profile = module.descriptor(config)
        require(module.provenance(profile) == row['synthesis'] == old['synthesis'] == proof['source_identity'], 'Changed source identity')
        rule = context.recipe(ROOT / SUCCESSORS[proof['policy_path']], code, text, proof['voice_directory'])
        require(rule is not None and rule['parent_text'] == proof['parent']['text'], 'Changed parent request')
        require(bool(rule.get('crop_asr')) == old['needs_fresh_crop_ASR'], 'Changed crop ASR scope')
        speech.VOICE = voice
        require(not speech.current(receipts[practice]['document'], config, code, key, text),
                'Predecessor already current; inspect earlier outcome')
        audited.append(dict(item=dict(practice=practice,config=config,code=code,key=key,text=text,row=row),
                            profile=profile,rule=rule,clip=clip,parent=parent))
    seen = {(practice,key) for practice,saved in receipts.items()
            for key,row in saved['document']['clips'].items()
            if row.get('speaker_verification',{}).get('scope') == 'context_parent'}
    require(seen == EXPECTED, 'Live accepted context scope changed')
    for saved in receipts.values():
        require(context.file_hash(saved['path']) == saved['sha256'], 'Receipt writer changed during audit')
    return receipts, audited


def jobs(audited, local, results):
    require(len(audited) == 15 and {(e['item']['practice'],e['item']['code']+'/'+e['item']['key'])
            for e in audited} == EXPECTED, 'Incomplete fifteen-row job scope')
    plan = []
    for entry in audited:
        item = entry['item']
        tasks = [('alignment','--align-audio',entry['parent'])]
        if entry['rule'].get('crop_asr'):
            tasks.append(('transcription','--transcribe-audio',entry['clip']))
        for kind, flag, audio in tasks:
            command = ['build-queue','--',local['python'],str(ROOT/'scripts/local_narration_context.py'),
                       flag,str(audio),'--language',item['code'],'--model',local['model'],
                       '--policy',str(ROOT/entry['rule']['policy_path'])]
            plan.append(dict(kind=kind,practice=item['practice'],key=item['code']+'/'+item['key'],
                input=str(audio),input_sha256=context.file_hash(audio),command=command,
                output=str(results/(migration.stem(entry)+'.'+kind+'.json'))))
    require(len(plan) == 17 and sum(j['kind']=='transcription' for j in plan) == 2,
            'Expected fifteen parent and two crop jobs')
    return plan


def stage(speech, receipts, audited, results):
    # Reuse the historical pure function; never relabel old alignment metadata.
    require(len(audited) == 15 and {(e['item']['practice'],e['item']['code']+'/'+e['item']['key'])
            for e in audited} == EXPECTED, 'Incomplete fifteen-row stage scope')
    return migration.stage(speech, receipts, audited, results)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('inventory','context-local','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--results',type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    require(output.is_relative_to(ROOT/'backup/narration'), 'Use the owning private narration store')
    subprocess.run(['git','-C',str(ROOT),'check-ignore','-q',str(output)],check=True)
    require(not output.exists(), 'Output exists; inspect its previous outcome instead of replaying')
    manifest = inventory(args.inventory)
    speech = migration.speech_module()
    receipts, audited = audit(speech, manifest)
    plan = jobs(audited,read_json(args.context_local),output/'asr-results')
    candidates, changes = stage(speech,receipts,audited,args.results) if args.results else ({},[])
    output.mkdir()
    write_json(output/'asr-job-plan.json',plan)
    if candidates:
        (output/'original-receipts').mkdir()
        (output/'receipt-candidates').mkdir()
        for practice,candidate in candidates.items():
            write_json(output/'original-receipts'/(practice+'.json'),receipts[practice]['document'])
            write_json(output/'receipt-candidates'/(practice+'.json'),candidate)
    write_json(output/'evidence.json',dict(rows=15,jobs=17,changes=changes,
        inference_executed=False,production_written=False,inventory_sha256=INVENTORY_SHA,
        helper_sha256=context.file_hash(context.__file__),
        generator_sha256=context.file_hash(ROOT/'scripts/generate-lumi-guide-narration.py'),
        original_receipt_sha256={k:v['sha256'] for k,v in receipts.items()},
        successor_policies={v:context.file_hash(ROOT/v) for v in SUCCESSORS.values()}))
    print('15 accepted proofs audited; 17 blind ASR jobs planned; '+
          ('15 candidates staged; no live writes.' if candidates else 'fresh evidence still required.'))


if __name__ == '__main__':
    main()
