#!/usr/bin/env python3
"""Freeze, verify and publish Practices cues made by Jungle's Ming bundle worker.

Copy the two plan files from `plan` into the existing private worker bundle,
run Jungle's speech_ming.py generate --bundle there, then return generation/
for local `verify`. `publish` requires complete locale packs and reviewed text.
Local verification can use ICU's uconv to compare Mandarin transcript spellings.
"""
import argparse
from array import array
from collections import defaultdict
import fcntl
from itertools import groupby
import re
import runpy
import shutil
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import unicodedata
import wave

import ming_narration
import ming_verification
from practice_media import ROOT, media_path, narration_text_path


PRACTICES = ('guide', 'taichi', 'sunsalutation', 'workout',
             'astral_projection', 'astral_projection_bruce')
PILOT = {
    'sunsalutation': 'sun_salutation_voice_mountain_start',
    'workout': 'workout_say_start',
}
APPROVED_EMBEDDING = '5666d1a4f3f75d48d6589b834fa3a27607c250daabc76ec750890e5db3626d5e'
PROVENANCE = 'jungle-narration.json'
COUNT_SPELLINGS = {
    'en': ('one', 'two', 'three'),
    'de': ('eins', 'zwei', 'drei'),
    'es': ('uno', 'dos', 'tres'),
    'fr': ('un', 'deux', 'trois'),
    'zh': ('一', '二', '三'),
    'ja': ('いち', 'に', 'さん'),
    'ko': ('하나', '둘', '셋'),
}
ENGLISH_NUMBER_WORDS = {
    word: str(value) for value, word in enumerate(
        ('zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten'))
}
ENGLISH_NUMBER = '|'.join(ENGLISH_NUMBER_WORDS) + r'|\d+(?:\.\d+)?'
ENGLISH_TIME_SPAN = re.compile(
    rf'(?<![\w-])({ENGLISH_NUMBER})(?:\s+(or|to)\s+({ENGLISH_NUMBER}))?'
    r'(?=\s+(?:comfortable\s+)?(?:seconds?|minutes?|hours?)\b)', re.IGNORECASE)


def workout_count_transcript(guide, code, text, heard):
    expected = guide['normalized'](text)
    normalized = guide['normalized'](heard)
    if code == 'en' and expected == 'two' and normalized == 'too':
        return text
    # A recognizer can render a spoken number as a digit. Require the entire
    # utterance and the reviewed count to represent the same number.
    digit = unicodedata.normalize('NFKC', heard).strip().rstrip('.!?。！？')
    if digit in ('1', '2', '3') and expected == COUNT_SPELLINGS[code][int(digit) - 1]:
        return text
    return heard


def sentence_slices(jungle, request, offsets):
    text = request['text']
    # An explicit Mandarin comma can separate a breath cue from the movement.
    boundaries = '.!?。！？' + ('，' if request['language'] == 'zh' else '')
    if (not isinstance(offsets, list) or not offsets or
            any(type(index) is not int or not 0 < index < len(text) or
                text[index - 1] not in boundaries or
                (text[index - 1] in '.!?' and not text[index].isspace()) for index in offsets) or
            offsets != sorted(set(offsets))):
        raise ValueError('Sentence slices must end at ordered punctuation offsets in the reviewed cue')
    edges = [0, *offsets, len(text)]
    slices = []
    for start, end in zip(edges, edges[1:]):
        fragment = text[start:end].strip()
        if not fragment:
            raise ValueError('Empty sentence slice in the reviewed cue')
        part = dict(request, text=fragment)
        slices.append((dict(request=jungle.identity(part), start=start, end=end), part))
    return slices


def cue_plan(jungle, guide, media, practices, languages, pilot, adapter, overrides=None,
             slice_offsets=None, *, workout_short=False, retakes=None):
    settings = jungle.read(ROOT / 'apps/practice/content.json')['narration']
    overrides = overrides or {}
    slice_offsets = slice_offsets or {}
    requests, cues, configs, compositions = {}, [], {}, {}
    for practice in practices:
        surfaces = settings[practice]
        config = jungle.read(ROOT / surfaces['config'])
        configs[practice] = config
        inventory = {'keys': config['short_workout_keys']} if workout_short else config
        keys = guide['narration_keys'](inventory)
        if pilot:
            keys = [key for key in keys if key == PILOT[practice]]
        default_text = media_path(surfaces['text_directory'], media)
        voice = media_path(surfaces['output_directory'], media).with_name('voice-jungle')
        for language in languages:
            source = narration_text_path(config, language, default_text, media)
            lines = guide['entries'](source)
            for key in keys:
                text = lines.get(key, '').strip()
                if not text:
                    raise ValueError(f'{source}: missing reviewed cue {key}')
                target = (voice / language / (key + '.ogg')).relative_to(media).as_posix()
                selected_adapter = overrides.get(target, adapter)
                request = jungle.request_for(
                    dict(language=language, text=text, adapter=selected_adapter), 'normal')
                if retakes:
                    request = jungle.retake_request(request, retakes)
                request_id = jungle.identity(request)
                if target in slice_offsets:
                    parts = sentence_slices(jungle, request, slice_offsets[target])
                    requests.update((part['request'], fragment) for part, fragment in parts)
                    compositions[target] = dict(request=request, parts=[part for part, _ in parts])
                else:
                    requests[request_id] = request
                cues.append(dict(practice=practice, key=key, language=language, path=target,
                                 request=request_id,
                                 maximum_seconds=guide['maximum_clip_seconds'](config, key)))
    paths = defaultdict(set)
    for cue in cues:
        paths[cue['path']].add(cue['request'])
    if any(len(ids) != 1 for ids in paths.values()):
        raise ValueError('Practice configurations disagree on the reviewed text for a shared cue')
    plan = dict(format=jungle.FORMAT, requests=requests, cues=cues)
    if compositions:
        plan['compositions'] = compositions
    return plan, configs


def verify_clip(clip, frames):
    decoded = subprocess.run(
        ['ffmpeg', '-nostdin', '-v', 'error', '-xerror', '-threads', '1', '-i', str(clip),
         '-map', '0:a:0', '-f', 'f32le', '-c:a', 'pcm_f32le', '-'],
        check=True, capture_output=True).stdout
    samples = array('f')
    samples.frombytes(decoded)
    if sys.byteorder != 'little':
        samples.byteswap()
    if len(samples) != frames or not samples:
        raise ValueError(f'Unexpected decoded duration or channel count: {clip.name}')
    peak = max(abs(value) for value in samples)
    if not 0.005 < peak < 1:
        raise ValueError(f'Silent or clipped decoded Opus ({peak:.5f} FS): {clip.name}')
    return round(peak, 6)


def quiet_count_end(samples, rate, maximum_seconds):
    # Match Jungle's PCM silence threshold. Leave a quiet margin on both
    # sides so the cut preserves the complete first utterance.
    start, cut = 0, None
    for quiet, group in groupby(samples, lambda sample: abs(sample) <= 180):
        end = start + sum(1 for _ in group)
        candidate = min(int(maximum_seconds * rate), end - int(0.02 * rate))
        if quiet and candidate >= rate / 2 and candidate - start >= int(0.06 * rate):
            cut = candidate
        start = end
    return cut


def trim_workout_count(jungle, recordings, key, maximum_seconds, source_opus):
    from speech_codec import EncodeOpusFile

    with wave.open(str(recordings / (key + '.wav')), 'rb') as source:
        params = source.getparams()
        pcm = source.readframes(source.getnframes())
    samples = array('h')
    samples.frombytes(pcm)
    if sys.byteorder != 'little':
        samples.byteswap()
    end = quiet_count_end(samples, params.framerate, maximum_seconds)
    if end is None:
        return None
    clip = recordings / f'{key}.count-{end}.opus'
    with TemporaryDirectory(dir=recordings) as temporary:
        wav = Path(temporary) / 'count.wav'
        opus = Path(temporary) / 'count.opus'
        with wave.open(str(wav), 'wb') as output:
            output.setparams(params)
            output.writeframes(pcm[:end * params.sampwidth])
        encoded = EncodeOpusFile(wav, opus, end)
        trim = dict(end_sample_22050=end, source_ogg_sha256=source_opus['sha256'],
                    trimmed_pcm_sha256=jungle.digest(wav))
        opus.replace(clip)
    return clip, encoded, trim


def checked_recording(jungle, recordings, key, request, embeddings):
    receipt = jungle.cached(key, request, folder=recordings)
    if (receipt is None or not receipt.get('decoder_completion', {}).get('stopped') or
            receipt['speaker_embedding_sha256'] not in embeddings or
            jungle.digest(recordings / (key + '.raw.wav')) != receipt['raw_sha256']):
        raise ValueError(f'Missing or invalid Jungle generation receipt for {key}')
    return receipt


def composition_stem(jungle, key, parts):
    slices = [{field: part[field] for field in ('request', 'start', 'end')} for part in parts]
    return f'{key}.split-{jungle.identity(slices)}'


def compose_sentences(jungle, recordings, stem, composition, requests, embeddings):
    from speech_codec import EncodeOpusFile

    parts = []
    params = (1, 2, 22050)
    with TemporaryDirectory(dir=recordings) as temporary:
        wav = Path(temporary) / 'composition.wav'
        with wave.open(str(wav), 'wb') as output:
            output.setparams((*params, 0, 'NONE', 'not compressed'))
            for part in composition['parts']:
                key = part['request']
                receipt = checked_recording(jungle, recordings, key, requests[key], embeddings)
                with wave.open(str(recordings / (key + '.wav')), 'rb') as source:
                    frames = source.getnframes()
                    if source.getparams()[:3] != params or frames != receipt['pcm']['frame_count']:
                        raise ValueError(f'Incompatible Jungle sentence PCM for {key}')
                    parts.append(dict(part, start_frame_22050=output.getnframes(), frame_count_22050=frames,
                                      pcm=receipt['pcm'], raw_sha256=receipt['raw_sha256'],
                                      speaker_embedding_sha256=receipt['speaker_embedding_sha256'],
                                      waveform_processing=receipt['waveform_processing'],
                                      decoder_completion=receipt['decoder_completion'],
                                      runtime_environment=receipt['runtime_environment']))
                    output.writeframesraw(source.readframes(frames))
            frames = output.getnframes()
        pcm = jungle.measure(wav)
        opus = EncodeOpusFile(wav, recordings / (stem + '.opus'), frames)
        return dict(pcm=pcm, opus=opus, raw_sha256=jungle.digest(wav), model_sample_rate=params[2],
                    waveform_processing=dict(method='concatenate verified native-rate PCM'),
                    runtime_environment=parts[0]['runtime_environment'],
                    decoder_completion=dict(stopped=True, parts=len(parts)), composition=parts)


def english_time_digits(text):
    """Keep the numbers check when ASR writes a spoken time span as digits."""
    def digits(match):
        first, link, last = match.groups()
        first = ENGLISH_NUMBER_WORDS.get(first.lower(), first)
        if last is None:
            return first
        return f'{first} {link} {ENGLISH_NUMBER_WORDS.get(last.lower(), last)}'

    return ENGLISH_TIME_SPAN.sub(digits, text)


def icu_transliterate(converter, text, transform):
    return subprocess.run(
        [converter, '-f', 'utf-8', '-t', 'utf-8', '-x', transform],
        input=text, text=True, encoding='utf-8', check=True, capture_output=True).stdout


def mandarin_pronunciation(converter, text):
    ideographs = [char for char in text
                  if not char.isspace() and not unicodedata.category(char).startswith('P')]
    if not ideographs or not all(unicodedata.name(char, '').startswith('CJK UNIFIED IDEOGRAPH')
                                for char in ideographs):
        return '', 0
    pinyin = icu_transliterate(converter, text, 'Han-Latin; NFC')
    tones = ''.join(char for char in pinyin
                    if not char.isspace() and not unicodedata.category(char).startswith('P'))
    return tones, len(ideographs)


def transcript_alignment(guide, config, code, text, heard, seconds, chinese_converter):
    if code == 'en' and (ENGLISH_TIME_SPAN.search(text) or ENGLISH_TIME_SPAN.search(heard)):
        expected, transcript = english_time_digits(text), english_time_digits(heard)
        score = guide['complete_match'](dict(config, verify_numbers=True), code,
                                        expected, transcript, seconds, ming=True)
        if (expected, transcript) != (text, heard):
            return score, dict(transform='English time spans to digits',
                               expected=expected, transcript=transcript)
        return score, None
    if code == 'zh' and text.startswith(('呼气', '吸气')):
        if re.search(r'(?:不|别|勿)(?:要)?[呼吸][气氣]', heard):
            return 0.0, None
    score = guide['complete_match'](config, code, text, heard, seconds, ming=True)
    if code == 'zh' and score < config['minimum_match'] and chinese_converter is not None:
        simplified = icu_transliterate(chinese_converter, heard, 'Traditional-Simplified')
        simplified_score = guide['complete_match'](config, code, text, simplified, seconds, ming=True)
        if simplified_score < config['minimum_match']:
            # Recognizers can select different characters for the same spoken syllables.
            # Compare the entire tonal string exactly, including the closing phrase.
            expected, expected_count = mandarin_pronunciation(chinese_converter, text)
            transcript, transcript_count = mandarin_pronunciation(chinese_converter, simplified)
            if expected and (transcript, transcript_count) == (expected, expected_count):
                return 1.0, dict(transform='ICU Han-Latin with tones',
                                 expected=expected, transcript=transcript)
        if simplified_score > score:
            return simplified_score, dict(transform='ICU Traditional-Simplified', transcript=simplified)
    return score, None


def verified_recordings(jungle, guide, plan, configs, bundle, asr_paths):
    from speech_codec import OggOpusFrames

    generation = bundle / 'generation'
    recordings = generation / 'recordings'
    embeddings = set()
    for path in generation.glob('female-speaker-*.json'):
        row = jungle.read(path)
        tensor = path.with_suffix('.pt')
        if (row['tensor_sha256'] == APPROVED_EMBEDDING and row['shape'] == [1, 192] and
                tensor.is_file() and jungle.digest(tensor) == row['file_sha256']):
            embeddings.add(row['file_sha256'])
    profile = jungle.read(ROOT / 'design/narration/ming-female.json')
    ming_verification.validate(profile)
    routes = profile['verification']['routes']
    # The pinned larger model distinguishes wording in French directions and
    # short Mandarin breath cues that Whisper Small misreads.
    large_route = next(route for route in routes.values()
                       if route['model'] == 'openai/whisper-large-v3-turbo')
    results, proofs = {}, {}
    failures = []
    route_name, recognizer = None, None
    chinese_converter = shutil.which('uconv')

    def transcribe(clip, code, route):
        nonlocal route_name, recognizer
        if route_name != route['model']:
            recognizer = None
            model_path = asr_paths[route['model']]
            for name, expected in route['artifacts'].items():
                if jungle.digest(Path(model_path) / name) != expected:
                    raise ValueError(f'Changed local {route["model"]} artifact: {name}')
            recognizer = ming_verification.Recognizer(model_path, route, 4)
            route_name = route['model']
        return recognizer.transcribe(clip, code)

    for cue in sorted(plan['cues'], key=lambda cue: (cue['language'], cue['practice'])):
        key = cue['request']
        composition = plan.get('compositions', {}).get(cue['path'])
        request = plan['requests'][key] if composition is None else composition['request']
        stem = key if composition is None else composition_stem(jungle, key, composition['parts'])
        code = request['language']
        workout_count = cue['practice'] == 'workout' and cue['key'].startswith('workout_say_count_')
        workout_go = cue['practice'] == 'workout' and cue['key'] == 'workout_say_go'
        count_budget = cue['maximum_seconds'] if workout_count or workout_go else None
        sun_uses_large_model = cue['practice'] == 'sunsalutation' and code in ('fr', 'zh')
        route = large_route if sun_uses_large_model else routes[code]
        proof_key = stem, count_budget, route['model']
        if proof_key not in proofs:
            clip = recordings / (stem + '.opus')
            if composition is None:
                receipt = checked_recording(jungle, recordings, key, request, embeddings)
            else:
                receipt = compose_sentences(jungle, recordings, stem, composition, plan['requests'], embeddings)
            opus = receipt['opus']
            trim = None
            if composition is None and count_budget is not None and opus['frames_48000'] > count_budget * 48000:
                shortened = trim_workout_count(jungle, recordings, key, count_budget, opus)
                if shortened is not None:
                    clip, opus, trim = shortened
            if OggOpusFrames(clip.read_bytes()) != opus['frames_48000']:
                raise ValueError(f'Invalid Opus header or duration for {cue["path"]}')
            try:
                peak = verify_clip(clip, opus['frames_48000'])
            except (ValueError, subprocess.CalledProcessError) as error:
                failures.append(f'{cue["path"]}: {error}')
                continue
            proof = transcribe(clip, code, route)
            proofs[proof_key] = dict(
                request=request, request_sha256=key, pcm=receipt['pcm'],
                text_sha256=guide['digest'](request['text'].encode('utf-8')),
                raw_sha256=receipt['raw_sha256'], model_sample_rate=receipt['model_sample_rate'],
                codec=opus['settings'], sha256=opus['sha256'], frames_48000=opus['frames_48000'],
                seconds=opus['frames_48000'] / 48000, encoder=opus['encoder'], decoded_peak=peak,
                waveform_processing=receipt['waveform_processing'],
                runtime_environment=receipt['runtime_environment'],
                decoder_completion=receipt['decoder_completion'], transcript=proof)
            if trim is not None:
                proofs[proof_key]['count_trim'] = trim
            if composition is not None:
                proofs[proof_key]['composition'] = receipt['composition']
        row = proofs[proof_key]
        seconds = row['frames_48000'] / 48000
        config = configs[cue['practice']]
        text, heard = request['text'], row['transcript']['text']
        if workout_count:
            heard = workout_count_transcript(guide, code, text, heard)
        score, comparison = transcript_alignment(guide, config, code, text, heard, seconds, chinese_converter)
        if sun_uses_large_model and score < config['minimum_match']:
            alternate_route = routes[code]
            alternate = transcribe(recordings / (stem + '.opus'), code, alternate_route)
            alternate_score, alternate_comparison = transcript_alignment(
                guide, config, code, text, alternate['text'], seconds, chinese_converter)
            if alternate_score == 1.0:
                row = dict(row, transcript=alternate)
                score, comparison = alternate_score, alternate_comparison
                route = alternate_route
        if not (0.5 <= seconds <= cue['maximum_seconds'] and score >= config['minimum_match']):
            failures.append(f'{cue["path"]}: {seconds:.3f}s (max {cue["maximum_seconds"]}s), '
                            f'alignment {score:.3f}: {row["transcript"]["text"]!r}')
            continue
        if 'composition' in row:
            row = dict(row, composition=[dict(part) for part in row['composition']])
        for part in row.get('composition', []):
            key = part['request']
            fragment = plan['requests'][key]['text']
            transcript = transcribe(recordings / (key + '.opus'), code, route)
            part_score, part_comparison = transcript_alignment(
                guide, config, code, fragment, transcript['text'], part['pcm']['duration'], chinese_converter)
            if part_score < config['minimum_match']:
                failures.append(f'{cue["path"]}, slice {part["start"]}:{part["end"]}: '
                                f'alignment {part_score:.3f}: {transcript["text"]!r}')
            part['transcript'] = transcript
            part['alignment'] = round(part_score, 6)
            if part_comparison is not None:
                part['transcript_comparison'] = part_comparison
        target = results.setdefault(cue['path'], dict(row, practices={}))
        target['practices'][cue['practice']] = dict(
            cue=cue['key'], alignment=round(score, 6), maximum_seconds=cue['maximum_seconds'])
        if comparison is not None:
            target['practices'][cue['practice']]['transcript_comparison'] = comparison
    if failures:
        raise ValueError('\n'.join(failures))
    return results


def publish(jungle, bundle, media, results):
    git = ['git', '-C', str(media)]
    checkout = subprocess.check_output([*git, 'rev-parse', '--show-toplevel'], text=True).strip()
    if Path(checkout).resolve() != media:
        raise ValueError('Publish requires the Practices checkout root')
    recovery = media / 'backup/jungle-narration'
    subprocess.run([*git, 'check-ignore', '-q', str(recovery / 'publish.lock')], check=True)
    recovery.mkdir(parents=True, exist_ok=True)
    with (recovery / 'publish.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        publish_locked(jungle, bundle, media, recovery, results)


def publish_locked(jungle, bundle, media, recovery, results):
    manifest = media / PROVENANCE
    provenance = jungle.read(manifest) if manifest.exists() else dict(
        format='practices-jungle-narration-1', speaker_tensor_sha256=APPROVED_EMBEDDING, clips={})
    if provenance['speaker_tensor_sha256'] != APPROVED_EMBEDDING:
        raise ValueError('Practices profile differs from the approved Jungle speaker')
    for name, result in results.items():
        target = media / name
        old = provenance['clips'].get(name)
        if target.exists():
            current = jungle.digest(target)
            if current == result['sha256']:
                continue
            if old is None or current != old['sha256']:
                raise ValueError(f'Refusing to overwrite a recording changed outside this producer: {name}')
            original = recovery / current / name
            original.parent.mkdir(parents=True, exist_ok=True)
            if not original.exists():
                shutil.copyfile(target, original)
            if jungle.digest(original) != current:
                raise ValueError(f'Incorrect recovery copy: {original}')
    for name, result in results.items():
        target = media / name
        if not target.exists() or jungle.digest(target) != result['sha256']:
            target.parent.mkdir(parents=True, exist_ok=True)
            recording = result['request_sha256']
            if 'count_trim' in result:
                recording += f'.count-{result["count_trim"]["end_sample_22050"]}'
            if 'composition' in result:
                recording = composition_stem(jungle, recording, result['composition'])
            clip = bundle / 'generation/recordings' / (recording + '.opus')
            temporary = target.with_suffix('.ogg.new')
            shutil.copyfile(clip, temporary)
            if jungle.digest(temporary) != result['sha256']:
                temporary.unlink()
                raise ValueError(f'Verified recording changed before publication: {name}')
            temporary.replace(target)
        previous = provenance['clips'].get(name)
        if previous and previous['request_sha256'] == result['request_sha256']:
            result['practices'] = previous['practices'] | result['practices']
        provenance['clips'][name] = result
    provenance['clips'] = dict(sorted(provenance['clips'].items()))
    jungle.write(manifest, provenance)


def check_plan(jungle, bundle, selected, spec):
    frozen = jungle.read(bundle / 'generation/plan.json')
    expected = dict(spec, plan_sha256=jungle.identity(frozen))
    if jungle.read(bundle / 'bundle.json') != expected:
        raise ValueError('The worker bundle differs from its frozen plan and speaker identity')
    frozen_rows = {(cue['practice'], cue['language'], cue['key']): cue for cue in frozen['cues']}
    for cue in selected['cues']:
        slot = cue['practice'], cue['language'], cue['key']
        composition = selected.get('compositions', {}).get(cue['path'])
        keys = [cue['request']] if composition is None else [part['request'] for part in composition['parts']]
        if (frozen_rows.get(slot) != cue or
                frozen.get('compositions', {}).get(cue['path']) != composition or
                any(frozen['requests'].get(key) != selected['requests'][key] for key in keys)):
            raise ValueError(f'The worker plan differs from the current cue text for {cue["path"]}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('plan', 'verify', 'publish'))
    parser.add_argument('--jungle', type=Path, required=True)
    parser.add_argument('--media-root', type=Path, required=True)
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--asr-paths', type=Path, help='existing offline Ming local-path configuration')
    parser.add_argument('--practice', action='append', choices=PRACTICES)
    parser.add_argument('--locale', action='append', choices=ming_narration.LANGUAGES)
    parser.add_argument('--adapter', help='supported CPU adapter from the pinned Jungle worker')
    parser.add_argument('--adapter-overrides', type=Path,
                        help='JSON mapping of reviewed output paths to verified Jungle CPU adapters')
    parser.add_argument('--sentence-slices', type=Path,
                        help='JSON mapping of reviewed output paths to sentence-end offsets for long cues')
    parser.add_argument('--retakes', type=Path,
                        help='reviewed rejected request IDs with bounded replacement seeds and reasons')
    parser.add_argument('--pilot', action='store_true', help='only the two English Sun/Workout samples')
    parser.add_argument('--workout-short', action='store_true',
                        help='only the new four-minute Workout announcements')
    args = parser.parse_args()
    if args.pilot and (args.practice or args.locale or args.workout_short or args.command == 'publish'):
        parser.error('the fixed pilot can only be planned or verified')
    if args.workout_short and args.practice not in (None, ['workout']):
        parser.error('--workout-short only applies to workout')
    if args.command != 'plan' and args.asr_paths is None:
        parser.error('--asr-paths is required for local transcript verification')
    sys.path.insert(0, str(args.jungle.resolve() / 'tools'))
    import speech_ming as jungle

    guide = runpy.run_path(str(ROOT / 'scripts/generate-lumi-guide-narration.py'))
    media = args.media_root.resolve()
    if args.workout_short:
        practices = ('workout',)
    else:
        practices = tuple(PILOT) if args.pilot else dict.fromkeys(args.practice or PRACTICES)
    languages = ('en',) if args.pilot else dict.fromkeys(args.locale or jungle.LANGUAGES)
    adapter = args.adapter or jungle.CPU_ADAPTERS[0]
    if adapter not in jungle.CPU_ADAPTERS:
        parser.error('the CPU adapter must be supported by the Jungle worker')
    overrides = {} if args.adapter_overrides is None else jungle.read(args.adapter_overrides)
    if not isinstance(overrides, dict) or any(value not in jungle.CPU_ADAPTERS for value in overrides.values()):
        parser.error('adapter overrides must map output paths to supported Jungle CPU adapters')
    offsets = {} if args.sentence_slices is None else jungle.read(args.sentence_slices)
    if not isinstance(offsets, dict):
        parser.error('sentence slices must map reviewed output paths to offsets')
    retakes = {} if args.retakes is None else jungle.read(args.retakes)
    if not isinstance(retakes, dict):
        parser.error('retakes must map rejected request IDs to seeds and reasons')
    plan, configs = cue_plan(jungle, guide, media, practices, languages, args.pilot, adapter, overrides, offsets,
                             workout_short=args.workout_short, retakes=retakes)
    if args.command == 'plan' and (overrides.keys() | offsets.keys()) - {cue['path'] for cue in plan['cues']}:
        parser.error('adapter overrides or sentence slices contain paths outside the selected reviewed cues')
    spec = dict(model_revision=jungle.MODEL_REVISION, runtime_revision=jungle.RUNTIME_REVISION,
                reference_sha256=jungle.REFERENCE_SHA, plan_sha256=jungle.identity(plan),
                embedding_tensor_sha256=APPROVED_EMBEDDING)
    if args.command == 'plan':
        jungle.write(args.bundle / 'generation/plan.json', plan)
        jungle.write(args.bundle / 'bundle.json', spec)
        print(f'{len(plan["cues"])} reviewed cue slots, {len(plan["requests"])} unique requests')
        return
    check_plan(jungle, args.bundle, plan, spec)
    results = verified_recordings(jungle, guide, plan, configs, args.bundle,
                                  jungle.read(args.asr_paths)['verification_models'])
    if args.command == 'publish':
        publish(jungle, args.bundle, media, results)
    print(f'{len(results)} clips decoded and aligned against {len(plan["cues"])} reviewed cue slots')
    if args.pilot:
        for name, row in results.items():
            print(f'{name}: {row["frames_48000"] / 48000:.3f}s, peak {row["decoded_peak"]:.4f} FS, '
                  f'transcript {row["transcript"]["text"]!r}, sha256 {row["sha256"]}')


if __name__ == '__main__':
    main()
