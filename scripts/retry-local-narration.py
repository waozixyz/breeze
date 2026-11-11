#!/usr/bin/env python3
"""Retry explicit female narration with durable fresh or bound unused draws.

Uses the ordinary generator's encoding, transcript, speaker and current gates.
Old cache entries and recordings are preserved. Integrity failures stop the run.
"""
import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import shutil
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import f5_russian_narration as local
import ming_narration as ming
import ming_verification
from practice_media import media_path, narration_text_path, writable_media

DRAWS = 4
EXACT_VERSION = 'exact-unused-attempts-v1'


def load_pipeline():
    spec = importlib.util.spec_from_file_location(
        '_fresh_narration_pipeline', ROOT / 'scripts/generate-lumi-guide-narration.py')
    pipeline = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pipeline)
    return pipeline


def checksum(path):
    with Path(path).open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def stable(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False)


class RequestPlan:
    def __init__(self, provider, module, config, profile, cache, text, code):
        self.provider = provider
        self.module = module
        self.config = config
        self.profile = profile
        self.cache = Path(cache).resolve()
        self.text = text
        self.code = code
        self.request = module.text_hash(config, text, profile, code)
        self.synthesis = module.provenance(profile)

    def candidate(self, attempt):
        if type(attempt) is not int or attempt < DRAWS:
            raise ValueError('Fresh retries begin beyond the ordinary four draws')
        return self._candidate(attempt)

    def _candidate(self, attempt):
        if type(attempt) is not int or attempt < 0:
            raise ValueError('Invalid source attempt')
        if self.provider == 'ming':
            profile = ming_verification.synthesis_profile(self.profile)
            pcm = ming.json_hash(dict(synthesis=self.synthesis, text=self.text,
                language=self.code, attempt=attempt, request_sha256=self.request,
                pcm_sample_rate=self.config['pcm_sample_rate']))
            spans = ming.segment_plan(profile, self.text)['spans']
            raw = []
            for index, span in enumerate(spans):
                seed = ming.segment_seed(profile, attempt, index)
                identity = ming.json_hash(dict(synthesis=self.synthesis, text=span['text'],
                                               language=self.code, seed=seed))
                raw.append(dict(identity=identity, seed=seed))
        else:
            pcm = local.json_hash(dict(request=self.request, attempt=attempt))
            raw = []
        return dict(attempt=attempt, pcm=pcm, raw=raw,
                    seed=self.profile.get('seed', 20261108) + attempt
                    if self.provider != 'ming' else None)

    def identities(self, candidate):
        return ['pcm:' + candidate['pcm']] + ['raw:' + row['identity'] for row in candidate['raw']]

    def paths(self, candidate):
        paths = [self.cache / (candidate['pcm'] + suffix)
                 for suffix in ('.pcm', '.json', '.pcm.part', '.json.part')]
        for row in candidate['raw']:
            paths.extend(self.cache / (row['identity'] + suffix)
                         for suffix in ('.wav', '.raw.json', '.wav.part', '.raw.json.part'))
        return paths

    def occupied(self, candidate):
        return any(os.path.lexists(path) for path in self.paths(candidate))


class ExactRequestPlan(RequestPlan):
    def candidate(self, attempt):
        if type(attempt) is not int or attempt not in (2, 3):
            raise ValueError('Only the two bound unused source attempts are allowed')
        return self._candidate(attempt)


def manifest_binding(pipeline, config, practice, provider, code, module, profile, cache, config_file):
    return dict(practice=practice, provider=provider, locale=code,
                voice_directory=str(pipeline.VOICE.resolve()), cache_directory=str(Path(cache).resolve()),
                config_file=str(Path(config_file).resolve()),
                source_file=str(narration_text_path(config, code, pipeline.LOCALES).resolve()),
                synthesis=module.provenance(profile))


class ExactManifest:
    """Immutable evidence for unused ordinary attempts; never a resume token."""
    def __init__(self, path, binding, root=ROOT):
        self.path = Path(path).resolve()
        self.root = Path(root).resolve()
        self.sha256 = checksum(self.path)
        self.data = self.read(self.path)
        if (not isinstance(self.data, dict) or set(self.data) != {'version', 'binding', 'config_sha256', 'source_sha256',
                               'completion', 'entries'} or
                self.data['version'] != EXACT_VERSION or self.data['binding'] != binding or
                not isinstance(self.data['entries'], list) or not 1 <= len(self.data['entries']) <= 3):
            raise ValueError('Invalid exact manifest scope or binding')
        self.files = []
        self.file(dict(path=binding['config_file'], sha256=self.data['config_sha256']))
        self.file(dict(path=binding['source_file'], sha256=self.data['source_sha256']))
        self.completion()

    @staticmethod
    def read(path, legacy=False):
        if path.stat().st_size > 262144:
            raise ValueError('Oversized exact request evidence')
        value = path.read_text()
        if legacy:
            data, end = json.JSONDecoder().raw_decode(value)
            if value[end:].strip() not in ('', chr(92) + 'n'):
                raise ValueError('Unknown trailing diagnostic data')
            return data
        return json.loads(value)

    def file(self, record):
        if not isinstance(record, dict) or set(record) != {'path', 'sha256'}:
            raise ValueError('Invalid exact evidence file binding')
        path = Path(record['path'])
        if not path.is_absolute():
            path = self.root / path
        path = path.resolve(strict=True)
        if not path.is_file() or checksum(path) != record['sha256']:
            raise ValueError('Exact request evidence changed')
        self.files.append((path, record['sha256']))
        return path

    def assert_sources(self):
        if checksum(self.path) != self.sha256 or any(checksum(path) != digest for path, digest in self.files):
            raise ValueError('Exact manifest or source evidence changed')

    def plans(self, pipeline, config, code, keys, receipt, provider, module, profile, cache):
        binding = self.data['binding']
        actual = dict(provider=provider, locale=code, voice_directory=str(pipeline.VOICE.resolve()),
                      cache_directory=str(Path(cache).resolve()), synthesis=module.provenance(profile))
        if any(binding.get(key) != value for key, value in actual.items()):
            raise ValueError('Exact manifest runtime binding changed')
        if config.get('_context_profile') or len(keys) != len(set(keys)):
            raise ValueError('Exact ordinary attempts cannot use context or duplicate keys')
        entries = self.data['entries']
        if any(not isinstance(row, dict) for row in entries):
            raise ValueError('Invalid exact manifest entry')
        names = [row.get('key') for row in entries]
        if (any(not isinstance(name, str) for name in names) or
                len(names) != len(set(names)) or set(names) != set(keys)):
            raise ValueError('Exact manifest must match every selected key exactly')
        rows = pipeline.wanted(config, [code], keys)
        if len(rows) != len(keys):
            raise ValueError('Unknown exact narration key')
        texts = {key: text for _, key, text in rows}
        plans = {}
        for entry in entries:
            if set(entry) != {'key', 'text', 'request_sha256', 'candidates', 'diagnostic',
                              'consumed_cache_files', 'previous_row_sha256', 'previous_audio_sha256'}:
                raise ValueError('Unsupported exact manifest fields')
            key = entry['key']
            text = texts[key]
            plan = ExactRequestPlan(provider, module, config, profile, cache, text, code)
            expected = [plan.candidate(index) for index in (2, 3)]
            if (entry['text'] != text or entry['request_sha256'] != plan.request or
                    stable(entry['candidates']) != stable(expected)):
                raise ValueError('Exact source, request or attempt identities changed')
            if any(plan.occupied(candidate) for candidate in expected):
                raise ValueError('Exact request cache occupied or partial; refusing replay')
            self.assert_previous(pipeline, receipt, code, key)
            diagnostic = self.file(entry['diagnostic'])
            if {path.resolve() for path in diagnostic.parent.glob('*.json')} != {diagnostic}:
                raise ValueError('Additional prior attempt outcomes require review')
            previous = self.read(diagnostic, legacy=True)
            attempts = previous.get('attempts', [])
            if (previous.get('locale') != code or previous.get('key') != key or
                    previous.get('text_sha256') != hashlib.sha256(text.encode()).hexdigest() or
                    not isinstance(attempts, list) or len(attempts) != 2 or
                    any(not isinstance(row, dict) for row in attempts) or
                    any(type(row.get('attempt')) is not int for row in attempts) or
                    [row['attempt'] for row in attempts] != [0, 1] or
                    not attempts[0].get('reasons') or
                    any(reason in ('error', 'context') for reason in attempts[0]['reasons']) or
                    attempts[-1].get('reasons') != ['error'] or
                    attempts[-1].get('error') != 'ValueError: last page does not end the stream'):
                raise ValueError('Ambiguous or unsupported consumed ordinary attempts')
            consumed = [plan._candidate(index) for index in (0, 1)]
            required_files = {path.resolve() for row in consumed for path in plan.paths(row)
                              if not path.name.endswith('.part')}
            if any(os.path.lexists(path) for row in consumed for path in plan.paths(row)
                   if path.name.endswith('.part')):
                raise ValueError('Consumed request has an uncertain partial cache')
            if not isinstance(entry['consumed_cache_files'], list):
                raise ValueError('Invalid consumed cache evidence')
            recorded_files = [self.file(record) for record in entry['consumed_cache_files']]
            if len(recorded_files) != len(required_files) or set(recorded_files) != required_files:
                raise ValueError('Missing or duplicate consumed cache evidence')
            plans[key] = plan
        self.assert_sources()
        return plans

    def assert_previous(self, pipeline, receipt, code, key):
        entry = next(row for row in self.data['entries'] if row['key'] == key)
        clip = pipeline.clip_path(code, key)
        if clip.is_symlink() or pipeline.RECEIPT.is_symlink():
            raise ValueError('Exact publication requires regular canonical files')
        disk = json.loads(pipeline.RECEIPT.read_text()) if pipeline.RECEIPT.exists() else {'clips': {}}
        if disk != receipt:
            raise ValueError('Narration receipt changed outside the selected retry')
        rows = [source['clips'].get(code + '/' + key) for source in (receipt, disk)]
        if (any((local.json_hash(row) if row is not None else None) != entry['previous_row_sha256']
                for row in rows) or
                (checksum(clip) if clip.exists() else None) != entry['previous_audio_sha256']):
            raise ValueError('Previously selected audio or receipt changed')

    def completion(self):
        record = self.data['completion']
        if not isinstance(record, dict) or set(record) != {'path', 'sha256', 'command_id'}:
            raise ValueError('Missing completed ordinary command evidence')
        path = self.file({key: record[key] for key in ('path', 'sha256')})
        terminal = self.read(path)
        waits = [json.loads(line) for line in terminal.get('output', '').splitlines()
                 if line.startswith('{') and 'child_exit_code' in line]
        if (terminal.get('id') != record['command_id'] or terminal.get('done') is not True or
                terminal.get('status') != 'finished' or type(terminal.get('code')) is not int or
                terminal['code'] != 1 or len(waits) != 1 or
                type(waits[0].get('child_exit_code')) is not int or waits[0]['child_exit_code'] != 1 or
                waits[0].get('auto_retry') is not False or 'reported_subprocess_signal' not in waits[0] or
                waits[0]['reported_subprocess_signal'] is not None):
            raise ValueError('Ambiguous or interrupted ordinary command outcome')


class Reservations:
    """One SQLite ledger across all voice roots sharing synthesis caches."""
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            version = db.execute('PRAGMA user_version').fetchone()[0]
            if version not in (0, 1):
                raise ValueError('Unsupported narration reservation schema')
            if version == 0:
                tables = db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
                if tables:
                    raise ValueError('Unrecognized narration reservation database')
                db.execute('CREATE TABLE blocks (id INTEGER PRIMARY KEY, owner TEXT NOT NULL, '
                           'stop INTEGER NOT NULL, body TEXT NOT NULL, events TEXT NOT NULL)')
                db.execute('CREATE TABLE claims (identity TEXT PRIMARY KEY, '
                           'block_id INTEGER NOT NULL REFERENCES blocks(id))')
                db.execute('PRAGMA user_version=1')

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=30)
        try:
            db.execute('PRAGMA synchronous=FULL')
            db.execute('PRAGMA foreign_keys=ON')
            with db:
                yield db
        finally:
            db.close()

    def reserve(self, owner, plan):
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            previous = db.execute('SELECT MAX(stop) FROM blocks WHERE owner=?', (owner,)).fetchone()[0]
            start = max(DRAWS, previous or DRAWS)
            for unused in range(10000):
                candidates = [plan.candidate(start + index) for index in range(DRAWS)]
                identities = [identity for row in candidates for identity in plan.identities(row)]
                if len(set(identities)) != len(identities):
                    raise ValueError('Duplicate identities within a retry block')
                occupied = any(plan.occupied(row) for row in candidates)
                claimed = any(db.execute('SELECT 1 FROM claims WHERE identity=?', (identity,)).fetchone()
                              for identity in identities)
                if not occupied and not claimed:
                    break
                start += DRAWS
            else:
                raise RuntimeError('No unoccupied fresh narration block within search bound')
            body = dict(provider=plan.provider, locale=plan.code, text=plan.text,
                        request_sha256=plan.request, synthesis=plan.synthesis,
                        driver_sha256=checksum(__file__), candidates=candidates)
            cursor = db.execute('INSERT INTO blocks(owner,stop,body,events) VALUES(?,?,?,?)',
                                (owner, start + DRAWS, stable(body), '[]'))
            block = dict(body, id=cursor.lastrowid)
            db.executemany('INSERT INTO claims(identity,block_id) VALUES(?,?)',
                           [(identity, block['id']) for identity in identities])
        return block

    def record(self, block, events):
        with self.connection() as db:
            cursor = db.execute('UPDATE blocks SET events=? WHERE id=?', (stable(events), block['id']))
            if cursor.rowcount != 1:
                raise RuntimeError('Retry reservation disappeared')

    def reserve_exact(self, requests, manifest_sha256):
        """Reserve every selected request atomically, without searching or replaying."""
        requests = list(requests)
        if not requests:
            raise ValueError('No exact requests selected')
        blocks = {}
        identities = set()
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            for key, owner, plan in requests:
                if key in blocks or not isinstance(plan, ExactRequestPlan):
                    raise ValueError('Duplicate or unsupported exact request')
                candidates = [plan.candidate(attempt) for attempt in (2, 3)]
                claimed = [identity for row in candidates for identity in plan.identities(row)]
                if (len(set(claimed)) != len(claimed) or identities.intersection(claimed) or
                        any(plan.occupied(row) for row in candidates) or
                        db.execute('SELECT 1 FROM blocks WHERE owner=?', (owner,)).fetchone() or
                        any(db.execute('SELECT 1 FROM claims WHERE identity=?', (identity,)).fetchone()
                            for identity in claimed)):
                    raise ValueError('Exact request occupied, claimed or previously reserved; refusing replay')
                identities.update(claimed)
                blocks[key] = dict(provider=plan.provider, locale=plan.code, text=plan.text,
                    request_sha256=plan.request, synthesis=plan.synthesis, candidates=candidates,
                    driver_sha256=checksum(__file__), mode=EXACT_VERSION,
                    manifest_sha256=manifest_sha256, owner=owner)
            for key, owner, plan in requests:
                block = blocks[key]
                cursor = db.execute('INSERT INTO blocks(owner,stop,body,events) VALUES(?,?,?,?)',
                    (owner, DRAWS, stable(block), '[]'))
                block['id'] = cursor.lastrowid
                db.executemany('INSERT INTO claims(identity,block_id) VALUES(?,?)',
                    [(identity, block['id']) for row in block['candidates']
                     for identity in plan.identities(row)])
        return blocks


class RetryRejected(RuntimeError):
    """The bounded fresh block was exhausted by ordinary quality failures."""


class DrawBudgetExhausted(RuntimeError):
    pass


class RawPeakRejected(RuntimeError):
    pass


def raw_peak(error, plan, candidate):
    prefix = 'Ming finite waveform peak exceeds PCM range: '
    if plan.provider != 'ming' or not str(error).startswith(prefix):
        return None
    evidence = json.loads(str(error)[len(prefix):])
    matching = [row for row in candidate['raw'] if row['identity'] == evidence.get('identity')]
    peak = evidence.get('raw_peak')
    if (len(matching) != 1 or evidence.get('seed') != matching[0]['seed'] or
            evidence.get('finite') is not True or type(evidence.get('samples')) is not int or
            evidence['samples'] <= 0 or evidence.get('gain') != 1.0 or
            type(peak) not in (int, float) or not math.isfinite(peak) or peak < 1):
        raise ValueError('Invalid Ming raw-peak rejection evidence') from error
    identity = matching[0]['identity']
    raw = plan.cache / (identity + '.wav')
    receipt = plan.cache / (identity + '.raw.json')
    if checksum(raw) != evidence.get('raw_sha256') or json.loads(receipt.read_text()) != evidence:
        raise ValueError('Changed Ming raw-peak evidence') from error
    return evidence


def effective_text(config, code, text):
    if config.get('_context_profile'):
        import local_narration_context as context
        rule = context.recipe(config['_context_profile'], code, text, config['_context_voice_directory'])
        if rule:
            return rule['parent_text']
    return text


class RetryEngine:
    def __init__(self, engine, plan, ledger, block):
        self.engine = engine
        self.plan = plan
        self.ledger = ledger
        self.block = block
        self.events = []

    def __getattr__(self, name):
        return getattr(self.engine, name)

    def speak(self, config, text, code, work, attempt):
        if len(self.events) >= len(self.block['candidates']):
            raise DrawBudgetExhausted('The reserved source draws are exhausted')
        actual = effective_text(config, code, text)
        if (code != self.plan.code or actual != self.plan.text or
                self.plan.module.text_hash(config, actual, self.profile, code) != self.plan.request or
                self.plan.module.provenance(self.profile) != self.plan.synthesis):
            raise ValueError('Retry request changed after reservation')
        candidate = self.block['candidates'][len(self.events)]
        if self.plan.occupied(candidate):
            raise RuntimeError('Reserved fresh cache identity became occupied; refusing replay')
        event = dict(candidate, pipeline_attempt=attempt, diagnostics_run=Path(work).name, status='started')
        self.events.append(event)
        self.ledger.record(self.block, self.events)
        try:
            result = self.engine.speak(config, text, code, work, candidate['attempt'])
        except Exception as error:
            evidence = raw_peak(error, self.plan, candidate)
            event.update(status='raw_peak_rejected' if evidence else 'error',
                         error=type(error).__name__ + ': ' + str(error))
            self.ledger.record(self.block, self.events)
            if evidence:
                raise RawPeakRejected(str(error)) from error
            raise
        event['status'] = 'synthesis_returned'
        self.ledger.record(self.block, self.events)
        return result


def generate_retry(pipeline, config, code, key, text, engine, plan, ledger, block, publication=None):
    proxy = RetryEngine(engine, plan, ledger, block)
    selected = dict(config, _local_engine=proxy)
    while True:
        try:
            row = pipeline.generate(selected, '', code, key, text)
            if publication is not None:
                publication['sha256'] = row['sha256']
                publication['events'] = proxy.events
            break
        except RawPeakRejected as error:
            if len(proxy.events) == len(block['candidates']):
                raise RetryRejected(str(error)) from error
        except DrawBudgetExhausted as error:
            raise RetryRejected(str(error)) from error
        except RuntimeError as error:
            if str(error).startswith(f'{code}/{key} never matched its text; '):
                raise RetryRejected(str(error)) from error
            raise
    candidate = block['candidates'][len(proxy.events) - 1]
    if plan.provider == 'ming':
        segmentation = row.get('segmentation', {})
        if (segmentation.get('attempt') != candidate['attempt'] or
                [part.get('seed') for part in segmentation.get('chunks', [])] !=
                [part['seed'] for part in candidate['raw']]):
            raise ValueError('Accepted Ming attempt differs from reserved seed identities')
    if not pipeline.current({'clips': {code + '/' + key: row}}, selected, code, key, text):
        raise RuntimeError('Fresh narration failed the ordinary current gate')
    proxy.events[-1].update(status='accepted', audio_sha256=row['sha256'])
    ledger.record(block, proxy.events)
    row['attempts'] = len(proxy.events)
    row['retry'] = dict(reservation=block['id'], driver_sha256=checksum(__file__),
                        request_sha256=plan.request, attempts=proxy.events)
    if block.get('mode') == EXACT_VERSION:
        row['retry'].update(mode=EXACT_VERSION, manifest_sha256=block['manifest_sha256'],
                            source_attempt=candidate['attempt'], source_seed=candidate['seed'])
    return row


@contextmanager
def generation_lock(root, voice):
    directory = Path(root) / 'backup/narration'
    directory.mkdir(parents=True, exist_ok=True)
    name = hashlib.sha256(str(Path(voice).resolve()).encode()).hexdigest()[:20]
    with (directory / (name + '.lock')).open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


def archive_original(directory, clip, row):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    if clip.is_file():
        identity = checksum(clip)
        target = directory / (identity + '.ogg')
        if target.exists():
            if checksum(target) != identity:
                raise ValueError('Changed original narration archive')
        else:
            shutil.copyfile(clip, target)
    if row is not None:
        payload = stable(row).encode()
        target = directory / (hashlib.sha256(payload).hexdigest() + '.json')
        if target.exists() and target.read_bytes() != payload:
            raise ValueError('Changed original narration receipt archive')
        if not target.exists():
            target.write_bytes(payload)



def restore_publication(clip, receipt_path, old_audio, old_receipt, publication, pending_receipt, block_id):
    if clip.is_symlink() or receipt_path.is_symlink():
        raise RuntimeError('Unexpected external publication link; refusing to replace it')
    audio = clip.read_bytes() if clip.exists() else None
    receipt = receipt_path.read_bytes() if receipt_path.exists() else None
    if audio != old_audio and (audio is None or
            hashlib.sha256(audio).hexdigest() != publication.get('sha256')):
        raise RuntimeError('Unexpected external audio change; original remains archived')
    if receipt != old_receipt and (pending_receipt is None or receipt != pending_receipt):
        raise RuntimeError('Unexpected external receipt change; refusing to overwrite it')
    # Validate both files before restoring either. Never replace an unknown writer's data.
    for path, previous, observed in ((clip, old_audio, audio), (receipt_path, old_receipt, receipt)):
        if observed == previous:
            continue
        if previous is None:
            path.unlink()
        else:
            temporary = path.with_name(path.name + '.retry-restore-' + str(block_id))
            with temporary.open('xb') as output:
                output.write(previous)
            temporary.replace(path)


def run_selected(pipeline, config, code, keys, receipt, provider, module, profile, cache, ledger,
                 engine_factory, archive, exact_manifest=None):
    rows = pipeline.wanted(config, [code], keys)
    exact_plans = (exact_manifest.plans(pipeline, config, code, keys, receipt, provider, module, profile, cache)
                   if exact_manifest is not None else None)
    pending = [(locale, key, text) for locale, key, text in rows
               if not pipeline.current(receipt, config, locale, key, text)]
    result = dict(accepted=[], failed=[], skipped=[key for _, key, _ in rows
                                                  if all(key != item[1] for item in pending)])
    if not pending:
        return result
    exact_blocks = None
    if exact_plans is not None:
        requests = []
        for locale, key, text in pending:
            plan = exact_plans[key]
            owner = local.json_hash(dict(voice=str(pipeline.VOICE.resolve()), locale=locale,
                                         key=key, source=text, request=plan.request))
            requests.append((key, owner, plan))
        exact_blocks = ledger.reserve_exact(requests, exact_manifest.sha256)
    engine = engine_factory()
    for locale, key, text in pending:
        if exact_manifest is not None:
            exact_manifest.assert_sources()
            exact_manifest.assert_previous(pipeline, receipt, locale, key)
        clip = pipeline.clip_path(locale, key)
        if clip.is_symlink() or pipeline.RECEIPT.is_symlink():
            raise ValueError('Retry publication requires regular canonical files')
        clip_id = locale + '/' + key
        had_row = clip_id in receipt['clips']
        old_row = receipt['clips'].get(clip_id)
        old_audio = clip.read_bytes() if clip.exists() else None
        old_receipt = pipeline.RECEIPT.read_bytes() if pipeline.RECEIPT.exists() else None
        archive_original(archive, clip, old_row)
        plan = (exact_plans[key] if exact_plans is not None else
                RequestPlan(provider, module, config, profile, cache,
                            effective_text(config, locale, text), locale))
        owner = local.json_hash(dict(voice=str(pipeline.VOICE.resolve()), locale=locale,
                                     key=key, source=text, request=plan.request))
        block = exact_blocks[key] if exact_blocks is not None else ledger.reserve(owner, plan)
        publication = {}
        pending_receipt = None
        try:
            if exact_manifest is not None:
                exact_manifest.assert_sources()
            try:
                row = generate_retry(pipeline, config, locale, key, text, engine, plan, ledger, block, publication)
            except RetryRejected as error:
                result['failed'].append(locale + '/' + key)
                print(str(error), file=sys.stderr, flush=True)
                continue
            if pipeline.wanted(config, [locale], [key]) != [(locale, key, text)]:
                raise ValueError('Narration source changed during the retry')
            if exact_manifest is not None:
                exact_manifest.assert_sources()
            receipt['clips'][clip_id] = row
            saved = dict(receipt, clips=dict(sorted(receipt['clips'].items())))
            pending_receipt = (json.dumps(saved, indent=2, ensure_ascii=False) + '\n').encode()
            pipeline.save(receipt)
        except BaseException:
            if had_row:
                receipt['clips'][clip_id] = old_row
            else:
                receipt['clips'].pop(clip_id, None)
            restore_publication(clip, pipeline.RECEIPT, old_audio, old_receipt,
                                publication, pending_receipt, block['id'])
            if publication.get('events'):
                publication['events'][-1]['publication'] = 'rolled_back'
                ledger.record(block, publication['events'])
            raise
        result['accepted'].append(locale + '/' + key)
        print(locale + '/' + key + ': fresh clip accepted', flush=True)
    return result


def main():
    pipeline = load_pipeline()
    catalog = json.loads((ROOT / 'apps/practice/content.json').read_text())['narration']
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--practice', required=True, choices=tuple(catalog))
    parser.add_argument('--locale', required=True)
    parser.add_argument('--key', action='append', required=True)
    parser.add_argument('--jobs', type=int, choices=(1,), default=1)
    parser.add_argument('--ming-profile', type=Path)
    parser.add_argument('--local-provider', choices=tuple(key for key in pipeline.LOCAL_PROVIDERS if key != 'ming'))
    parser.add_argument('--local-voice-profile', type=Path)
    parser.add_argument('--context-profile', type=Path)
    parser.add_argument('--context-local-profile', type=Path)
    parser.add_argument('--resume-manifest', type=Path,
        help='bound evidence for exactly unused ordinary attempts 2 and 3; never replays a reservation')
    args = parser.parse_args()
    if bool(args.local_provider) != bool(args.local_voice_profile):
        parser.error('Select both --local-provider and --local-voice-profile')
    if bool(args.ming_profile) == bool(args.local_provider):
        parser.error('Select exactly one explicit local provider')
    if bool(args.context_profile) != bool(args.context_local_profile):
        parser.error('Context retries require both explicit context profiles')
    if args.resume_manifest and args.context_profile:
        parser.error('Exact ordinary attempts cannot use a context recipe')
    if args.practice.endswith('_male'):
        parser.error('Female local retries must not overwrite male recordings')
    if len(set(args.key)) != len(args.key):
        parser.error('Duplicate selected keys')
    provider = 'ming' if args.ming_profile else args.local_provider
    module = pipeline.LOCAL_PROVIDERS[provider]
    if args.locale not in module.LANGUAGES:
        parser.error('The selected provider does not support this locale')
    settings = catalog[args.practice]
    config = json.loads((ROOT / settings['config']).read_text())
    if any(key not in pipeline.narration_keys(config) for key in args.key):
        parser.error('Unknown narration key')
    local_path = args.ming_profile or args.local_voice_profile
    private = json.loads(local_path.read_text())
    if provider != 'ming' and os.path.abspath(sys.executable) != os.path.abspath(private['python']):
        parser.error('Use the selected local profile Python interpreter')
    profile = module.descriptor(config)
    if profile is None:
        parser.error('No public profile for the selected provider')
    pipeline.MEDIA_ROOT = writable_media().resolve()
    pipeline.VOICE = media_path(settings['output_directory']).resolve()
    pipeline.LOCALES = media_path(settings['text_directory']).resolve()
    pipeline.RECEIPT = ROOT / settings['receipt']
    if not pipeline.VOICE.is_relative_to(pipeline.MEDIA_ROOT):
        parser.error('Narration output must stay inside canonical practices media')
    config.update(_local_engine=True, _cached_only=False,
                  _context_voice_directory=pipeline.VOICE.relative_to(pipeline.MEDIA_ROOT).as_posix())
    if args.context_profile:
        config['_context_profile'] = str(args.context_profile)
    cache = ROOT / 'backup/narration/cache' if provider == 'ming' else Path(private['cache']).resolve()
    state = ROOT / 'backup/narration/retries'
    pipeline.subprocess.run(['git', '-C', str(ROOT), 'check-ignore', '-q', str(state / 'probe')], check=True)
    os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1')

    def factory():
        engine = module.Engine(profile, local_path)
        if args.context_profile:
            import local_narration_context as context
            engine = context.ContextEngine(engine, config, args.context_profile, args.context_local_profile,
                encode=pipeline.encode, complete_match=pipeline.complete_match,
                identity=module.provenance(profile), voice_directory=config['_context_voice_directory'])
        return engine

    with generation_lock(ROOT, pipeline.VOICE):
        receipt = json.loads(pipeline.RECEIPT.read_text()) if pipeline.RECEIPT.exists() else {'clips': {}}
        exact_manifest = None
        if args.resume_manifest:
            binding = manifest_binding(pipeline, config, args.practice, provider, args.locale,
                                       module, profile, cache, ROOT / settings['config'])
            exact_manifest = ExactManifest(args.resume_manifest, binding)
        result = run_selected(pipeline, config, args.locale, args.key, receipt, provider, module, profile,
                              cache, Reservations(state / 'requests.sqlite3'), factory, state / 'originals',
                              exact_manifest=exact_manifest)
    print(stable(result))
    return 1 if result['failed'] else 0


if __name__ == '__main__':
    sys.exit(main())
