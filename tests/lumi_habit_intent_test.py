#!/usr/bin/env python3
"""Lumi understands habit requests offline, in every language it has
templates for: each phrase maps to exactly these app tool calls, and near
misses make none.

The test builds a Ziran program around apps/lumi/habit_intent.zi with the
translated templates from locales/*.txt, runs it without a display, and
compares the calls it prints with the table below.
"""
import json
from pathlib import Path
import os
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / 'build/lumi-habit-intent-test'
ZIRAN = ROOT / 'build/ziran-toolchain/bin/ziran'
KEYS = ('lumi_habit_patterns', 'lumi_habit_clauses', 'lumi_habit_words')

HABITS = [
    ('id-push', 'Push ups', False),
    ('id-rope', 'Jumping Rope', False),
    ('id-eat', 'Eating window', False),
    ('id-med', 'Meditation', False),
    ('id-yoga', 'Yoga', False),
    ('id-sleep', 'Sleep', False),
    ('id-run', 'Run', False),
    ('id-run-far', 'Run far', False),
    ('id-cold', 'Cold Shower', True),
    ('id-lieg', 'Liegestütze', False),
    ('id-flex', 'Flexiones', False),
    ('id-pomp', 'Pompes', False),
    ('id-fless', 'Flessioni', False),
    ('id-flexoes', 'Flexões', False),
    ('id-otzh', 'Отжимания', False),
    ('id-medru', 'Медитация', False),
    ('id-kliky', 'Kliky', False),
    ('id-lari', 'Lari pagi', False),
    ('id-ude', '腕立て伏せ', False),
    ('id-pal', '팔굽혀펴기', False),
    ('id-fuwo', '俯卧撑', False),
    ('id-ming', '冥想', False),
]
ROPE_QUESTIONS = ('[{"text":"How many I did?","answer":"number","good":"above_average"},'
                  '{"text":"Felt good?","answer":"yes_no","good":"yes"}]')


def call(tool, **arguments):
    return [tool, arguments]


def schedule(identifier, **arguments):
    return call('set_habit_schedule', id=identifier, **arguments)


def tracking(identifier, **arguments):
    return call('set_habit_tracking', id=identifier, **arguments)


def questions(identifier, *items):
    return call('set_habit_questions', id=identifier, questions=list(items))


# (language, phrase, existing questions, expected calls). None means no
# offline action at all; "ambiguous" and "exists" are answers without calls.
CASES = [
    ('en', 'add a habit push ups every day at 8', '[]', 'exists-update'),
    ('en', 'add a habit stretching every day at 8', '[]', [
        call('create_habit', name='Stretching'),
        schedule('$new', repeat='daily', notification=True, notification_hour=8)]),
    ('en', 'add a habbit walk on mondays and thursdays', '[]', [
        call('create_habit', name='Walk'),
        schedule('$new', repeat='weekly', weekdays=['mon', 'thu'])]),
    ('en', 'new habit read every 2 days', '[]', [
        call('create_habit', name='Read'),
        schedule('$new', repeat='daily', every=2)]),
    ('en', 'start a habit floss on weekdays at 9pm', '[]', [
        call('create_habit', name='Floss'),
        schedule('$new', repeat='weekly', weekdays=['mon', 'tue', 'wed', 'thu', 'fri'],
                 notification=True, notification_hour=21)]),
    ('en', 'create a new habit called drink water 8 times a day', '[]', [
        call('create_habit', name='Drink water'),
        tracking('$new', mode='count', target=8)]),
    ('en', 'add a habit journal', '[]', [call('create_habit', name='Journal')]),
    ('en', 'add a habit yoga', '[]', 'exists'),
    ('en', 'push ups 3 times a day', '[]', [tracking('id-push', mode='count', target=3)]),
    ('en', 'jumping rope should count to 100', '[]', [tracking('id-rope', mode='count', target=100)]),
    ('en', 'jumping rope should count to 0', '[]', [tracking('id-rope', mode='count', target=0)]),
    ('en', 'jumping rope should ask how many I did, higher is better', '[]', [
        questions('id-rope', dict(text='How many I did?', answer='number', good='above_average'))]),
    ('en', 'jumping rope should ask how many I did, at least 50', ROPE_QUESTIONS, [
        questions('id-rope', dict(text='How many I did?', answer='number', good='at_least', low=50),
                  dict(text='Felt good?', answer='yes_no', good='yes'))]),
    ('en', 'jumping rope should not ask felt good', ROPE_QUESTIONS, [
        questions('id-rope', dict(text='How many I did?', answer='number', good='above_average'))]),
    ('en', 'my eating window is good at most 8 hours', '[]', [
        tracking('id-eat', mode='span', good='at_most', high='8:00')]),
    ('en', 'eating window from start to end, at least 16h', '[]', [
        tracking('id-eat', mode='span', good='at_least', low='16:00')]),
    ('en', 'eating window between 6 and 8 hours', '[]', [
        tracking('id-eat', mode='span', good='between', low='6:00', high='8:00')]),
    ('en', 'eating window shorter is better', '[]', [
        tracking('id-eat', mode='span', good='below_average')]),
    ('en', 'sleep should ask what time I woke up, before 7:00', '[]', [
        questions('id-sleep', dict(text='What time I woke up?', answer='time', good='at_most', high='7:00'))]),
    ('en', 'meditation should ask if I felt calm, yes is good', '[]', [
        questions('id-med', dict(text='If I felt calm?', answer='yes_no', good='yes'))]),
    ('en', 'remind me to meditate at 7', '[]', [
        schedule('id-med', notification=True, notification_hour=7)]),
    ('en', 'remind me to stretch at 7am', '[]', [
        call('create_habit', name='Stretch'),
        schedule('$new', repeat='daily', notification=True, notification_hour=7)]),
    ('en', 'stop reminding me to do yoga', '[]', None),
    ('en', 'stop reminding me about yoga', '[]', [schedule('id-yoga', notification=False)]),
    ('en', 'yoga at 6pm', '[]', [schedule('id-yoga', notification=True, notification_hour=18)]),
    ('en', 'yoga every other day', '[]', [schedule('id-yoga', repeat='daily', every=2)]),
    ('en', 'rename push ups to press ups', '[]', [call('rename_habit', id='id-push', name='Press ups')]),
    ('en', 'pause yoga', '[]', [call('set_habit_active', id='id-yoga', active=False)]),
    ('en', 'resume cold shower', '[]', [call('set_habit_active', id='id-cold', active=True)]),
    ('en', 'resume yoga', '[]', None),
    ('en', 'delete the habit yoga', '[]', [call('delete_habit', id='id-yoga')]),
    ('en', 'delete habit cold shower', '[]', [call('delete_habit', id='id-cold')]),
    ('en', 'pause run far', '[]', [call('set_habit_active', id='id-run-far', active=False)]),
    ('en', 'pause run', '[]', [call('set_habit_active', id='id-run', active=False)]),
    # Near misses act on nothing.
    ('en', 'add a habit', '[]', None),
    ('en', 'push ups', '[]', None),
    ('en', 'remind me to meditate at 7:30', '[]', None),
    ('en', 'delete everything', '[]', None),
    ('en', 'rename yoga', '[]', None),
    ('en', 'yoga every 0 days', '[]', None),
    ('en', 'I want to feel better', '[]', None),
    ('en', 'add milk every day', '[]', None),
    ('en', 'push ups higher is better', '[]', None),
    ('en', 'sleep should ask if I slept well, before 7', '[]', None),
    ('en', 'pause cold shower', '[]', None),
    ('en', 'push ups 3 times a day and as a span', '[]', None),
    ('en', 'what is the weather', '[]', None),
    # Every language reads its own words, and English beside them.
    ('de', 'neue Gewohnheit Dehnen jeden Tag um 8 Uhr abends', '[]', [
        call('create_habit', name='Dehnen'),
        schedule('$new', repeat='daily', notification=True, notification_hour=20)]),
    ('de', 'Liegestütze dreimal am Tag', '[]', [tracking('id-lieg', mode='count', target=3)]),
    ('de', 'pausiere Liegestütze', '[]', [call('set_habit_active', id='id-lieg', active=False)]),
    ('de', 'Liegestütze soll fragen wie viele, je mehr, desto besser', '[]', [
        questions('id-lieg', dict(text='Wie viele?', answer='number', good='above_average'))]),
    ('de', 'add a habit read every day', '[]', [
        call('create_habit', name='Read'), schedule('$new', repeat='daily')]),
    ('de', 'Wie wird das Wetter?', '[]', None),
    ('es', 'añade un hábito leer los lunes y jueves a las 9', '[]', [
        call('create_habit', name='Leer'),
        schedule('$new', repeat='weekly', weekdays=['mon', 'thu'], notification=True, notification_hour=9)]),
    ('es', 'flexiones 20 veces al día', '[]', [tracking('id-flex', mode='count', target=20)]),
    ('es', 'borra el hábito flexiones', '[]', [call('delete_habit', id='id-flex')]),
    ('fr', 'nouvelle habitude marcher tous les jours à 7 heures', '[]', [
        call('create_habit', name='Marcher'),
        schedule('$new', repeat='daily', notification=True, notification_hour=7)]),
    ('fr', 'pompes au moins 30, plus c\'est mieux', '[]', None),
    ('fr', 'renomme pompes en tractions', '[]', [call('rename_habit', id='id-pomp', name='Tractions')]),
    ('it', 'nuova abitudine leggere ogni giorno alle 21', '[]', [
        call('create_habit', name='Leggere'),
        schedule('$new', repeat='daily', notification=True, notification_hour=21)]),
    ('it', 'flessioni 10 volte al giorno', '[]', [tracking('id-fless', mode='count', target=10)]),
    ('pt', 'novo hábito ler todos os dias às 8', '[]', [
        call('create_habit', name='Ler'),
        schedule('$new', repeat='daily', notification=True, notification_hour=8)]),
    ('pt', 'flexões 15 vezes por dia', '[]', [tracking('id-flexoes', mode='count', target=15)]),
    ('ru', 'добавь привычку чтение каждый день в 9', '[]', [
        call('create_habit', name='чтение'),
        schedule('$new', repeat='daily', notification=True, notification_hour=9)]),
    ('ru', 'отжимания 3 раза в день', '[]', [tracking('id-otzh', mode='count', target=3)]),
    ('ru', 'напоминай мне о медитации в 7', '[]', [
        schedule('id-medru', notification=True, notification_hour=7)]),
    ('cs', 'nový návyk čtení každý den v 8', '[]', [
        call('create_habit', name='čtení'),
        schedule('$new', repeat='daily', notification=True, notification_hour=8)]),
    ('cs', 'kliky třikrát denně', '[]', [tracking('id-kliky', mode='count', target=3)]),
    ('id', 'tambah kebiasaan membaca setiap hari jam 8', '[]', [
        call('create_habit', name='Membaca'),
        schedule('$new', repeat='daily', notification=True, notification_hour=8)]),
    ('id', 'jeda lari pagi', '[]', [call('set_habit_active', id='id-lari', active=False)]),
    ('ja', '毎日8時に読書の習慣を追加', '[]', [
        call('create_habit', name='読書'),
        schedule('$new', repeat='daily', notification=True, notification_hour=8)]),
    ('ja', '腕立て伏せを1日3回', '[]', [tracking('id-ude', mode='count', target=3)]),
    ('ja', '腕立て伏せを削除', '[]', [call('delete_habit', id='id-ude')]),
    ('ko', '매일 8시에 독서 습관 추가', '[]', [
        call('create_habit', name='독서'),
        schedule('$new', repeat='daily', notification=True, notification_hour=8)]),
    ('ko', '팔굽혀펴기는 하루 3번', '[]', [tracking('id-pal', mode='count', target=3)]),
    ('zh', '每天8点提醒我冥想', '[]', [
        schedule('id-ming', repeat='daily', notification=True, notification_hour=8)]),
    ('zh', '俯卧撑每天100次', '[]', [tracking('id-fuwo', mode='count', target=100)]),
    ('zh', '添加习惯阅读', '[]', [call('create_habit', name='阅读')]),
    ('zh', '今天天气怎么样', '[]', None),
]


def locale_values(language):
    locales = Path(os.environ.get('INBE_LOCALES_DIR', ROOT / 'locales'))
    text = (locales / (language + '.txt')).read_text(encoding='utf-8')
    values = {}
    for key in KEYS:
        match = re.search(r'^\[' + key + r'\]\n(.*?)\n---$', text, re.S | re.M)
        assert match, f'{language}.txt has no [{key}]'
        values[key] = match.group(1)
    return values


def ziran_text(value):
    assert 'LUMI_TEXT_END' not in value
    return '#string LUMI_TEXT_END\n' + value + '\nLUMI_TEXT_END'


def program(languages):
    lines = ['#import, file "../../apps/lumi/habit_intent.zi";',
             '#import, file "../../apps/lumi/habit_patterns.zi";', '']
    for language in languages:
        values = locale_values(language)
        for key in KEYS:
            lines.append(f'{language.upper()}_{key.upper()} :: {ziran_text(values[key])}')
        lines.append('')
    lines.append('#program_export')
    lines.append('Answer :: () -> s32 {')
    lines.append(f'    habits: [{len(HABITS)}]LumiHabitRef')
    for index, (identifier, title, paused) in enumerate(HABITS):
        lines.append(f'    habits[{index}] = LumiHabitRef.{{.id = "{identifier}", .title = "{title}", '
                     f'.paused = {"true" if paused else "false"}}}')
    lines.append('    english := LumiLanguage.{.patterns = EN_LUMI_HABIT_PATTERNS, '
                 '.clauses = EN_LUMI_HABIT_CLAUSES, .words = EN_LUMI_HABIT_WORDS}')
    lines.append('    calls: [LUMI_CALLS_MAX]LumiToolCall')
    for index, (language, phrase, existing, _) in enumerate(CASES):
        upper = language.upper()
        lines.append(f'    active{index} := LumiLanguage.{{.patterns = {upper}_LUMI_HABIT_PATTERNS, '
                     f'.clauses = {upper}_LUMI_HABIT_CLAUSES, .words = {upper}_LUMI_HABIT_WORDS}}')
        lines.append(f'    plan{index} := LumiHabitParse({json.dumps(phrase, ensure_ascii=False)}, '
                     f'active{index}, english, habits[:])')
        lines.append(f'    print("CASE {index} kind=% habit=% steps=%\\n", plan{index}.kind, plan{index}.habit, lumi_parse_steps)')
        lines.append(f'    count{index} := LumiHabitCalls(plan{index}, habits[:], {json.dumps(existing)}, calls[:])')
        lines.append(f'    for call: cast(s32)0..count{index} - 1 {{')
        lines.append('        print("CALL % %\\n", calls[call].name, calls[call].arguments)')
        lines.append('    }')
    lines.append('    return 42')
    lines.append('}')
    return '\n'.join(lines) + '\n'


def run():
    WORK.mkdir(parents=True, exist_ok=True)
    languages = sorted({case[0] for case in CASES} | {'en'})
    source = WORK / 'lumi_habit_cases.zi'
    source.write_text(program(languages), encoding='utf-8')
    env = {key: value for key, value in os.environ.items()
           if key not in ('DISPLAY', 'WAYLAND_DISPLAY', 'XAUTHORITY', 'DBUS_SESSION_BUS_ADDRESS')}
    subprocess.run([str(ZIRAN), 'bundle', '--root', str(WORK), '--module-path', str(ROOT / 'apps/lumi'),
                    '--entry', 'lumi_habit_cases:Answer', '-o', str(WORK / 'cases.zx'), str(source)],
                   check=True, env=env)
    output = subprocess.run([str(ZIRAN), 'run', str(WORK / 'cases.zx')], check=True,
                            capture_output=True, text=True, env=env).stdout
    results = {}
    current = None
    for line in output.splitlines():
        if line.startswith('CASE '):
            parts = line.split()
            current = int(parts[1])
            results[current] = dict(kind=int(parts[2].split('=')[1]), habit=int(parts[3].split('=')[1]), calls=[])
        elif line.startswith('CALL '):
            _, name, arguments = line.split(' ', 2)
            results[current]['calls'].append([name, json.loads(arguments)])
    failures = []
    for index, (language, phrase, _, expected) in enumerate(CASES):
        result = results.get(index)
        if result is None:
            failures.append(f'{language}: {phrase!r}: no result')
            continue
        if expected is None:
            if result['kind'] != 0 or result['calls']:
                failures.append(f'{language}: {phrase!r} should not act, got kind {result["kind"]} {result["calls"]}')
        elif expected == 'exists':
            if result['kind'] != 9:
                failures.append(f'{language}: {phrase!r} should say the habit exists, got {result}')
        elif expected == 'exists-update':
            if result['kind'] != 2:
                failures.append(f'{language}: {phrase!r} should update the existing habit, got {result}')
        elif expected == 'ambiguous':
            if result['habit'] != -2:
                failures.append(f'{language}: {phrase!r} should be ambiguous, got {result}')
        elif result['calls'] != expected:
            failures.append(f'{language}: {phrase!r}\n  expected {expected}\n  got      {result["calls"]}')
    if failures:
        print('\n'.join(failures), file=sys.stderr)
        print(f'{len(failures)} of {len(CASES)} Lumi habit phrases failed', file=sys.stderr)
        sys.exit(1)
    print(f'Lumi habit phrases: {len(CASES)} phrases in {len(languages)} languages map to their tool calls')


if __name__ == '__main__':
    run()
