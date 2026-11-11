"""Bounded local attempt records; never mark an audio clip accepted."""
import json
from pathlib import Path
import re
import subprocess


class Attempts:
    def __init__(self, root, code, key, run, text_sha256):
        if any(not re.fullmatch('[a-zA-Z0-9_-]{1,160}', value) for value in (code, key, run)):
            raise ValueError('Invalid narration diagnostic identifier')
        self.path = Path(root) / 'backup/narration/diagnostics' / code / key / (run + '.json')
        subprocess.run(['git', '-C', str(root), 'check-ignore', '-q', str(self.path)],
                       check=True, capture_output=True)
        self.data = dict(schema=1, locale=code, key=key, text_sha256=text_sha256, attempts=[])

    def save(self, row):
        if len(self.data['attempts']) >= 4:
            raise ValueError('Too many narration diagnostic attempts')
        row = dict(row)
        for key, limit in (('transcript', 8192), ('error', 2048)):
            if isinstance(row.get(key), str) and len(row[key]) > limit:
                row[key] = row[key][:limit]
                row[key + '_truncated'] = True
        self.data['attempts'].append(row)
        payload = json.dumps(self.data, ensure_ascii=False, allow_nan=False, indent=2) + '\n'
        if len(payload.encode()) > 65536:
            raise ValueError('Oversized narration diagnostic record')
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix('.json.part')
        temporary.write_text(payload)
        temporary.replace(self.path)
