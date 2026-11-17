"""Snapshot only the six canonical sessions and their English caption text."""
import json
import pathlib
import re

root = pathlib.Path(__file__).resolve().parents[4]
source = root.parent.parent / 'modules/practices/astral_projection'
texts = dict(re.findall(r'\[([^\]]+)\]\n(.*?)\n---', (source / 'text/en.txt').read_text(), re.S))
items = json.loads((source / 'catalogue.json').read_text())['practices']
for item in items:
    session = json.loads((source / 'sessions' / (item['id'] + '.json')).read_text())
    assert item['duration'] == session['duration']
    item['title'] = texts[item['title_key']]
    item['cues'] = [dict(cue, text=texts[cue['key']]) for cue in session['cues']]
(root / 'design/astral-projection/three/src/sessions.json').write_text(json.dumps(items, ensure_ascii=False, indent=2) + '\n')
