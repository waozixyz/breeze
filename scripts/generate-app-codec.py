#!/usr/bin/env python3
"""Generate src/apps/app_codec.zi with Kryon's widget codec generator.

Kryon encodes its own widget records in its widget_codec module. This adds
the frames and rows Inner Breeze's apps exchange with their screens.
Pass --check to verify the file is current."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
KRYON = ROOT / 'build/packages/kryon'
KRYON_MODULES = ['session', 'geometry', 'drawing_props', 'text_props', 'image_props',
                 'button_props', 'control_props', 'text_input', 'text_input_props',
                 'scroll', 'scroll_props', 'semantic', 'text_align', 'checkbox_props',
                 'toggle_props', 'tab_bar_props', 'box_props', 'swipe_props']
APP_TYPES = ['diary_ui_types', 'inbe_ui_types', 'lists_ui_types', 'lumi_ui_types',
             'lumi_types', 'habits_ui_types', 'practice_ui_types']
ROOTS = ['DiaryUiFrame', 'InbeUiFrame', 'ListsUiFrame', 'ListsUiRow', 'ListsUiPerson', 'ListsUiRequest', 'LumiUiFrame',
         'LumiChatRow', 'LumiTask', 'LumiAction', 'LumiTools', 'LumiDonation',
         'HabitsUiFrame', 'HabitsShopFrame',
         'HabitsShopReward', 'HabitsShopActivity', 'HabitsListFrame', 'HabitsListRow',
         'HabitsListDay', 'HabitsDayFrame', 'HabitsDayEntry', 'HabitsDaySession',
         'HabitsEntryFrame', 'HabitsAnswer', 'HabitsEditFrame', 'HabitsEditQuestion',
         'HabitsEditPractice', 'HabitsStatsFrame', 'HabitsStatsChart', 'HabitsStatsPoint',
         'HabitsStatsRecent', 'HabitsStatsHold', 'HabitsStatsChange', 'PracticeHomeFrame',
         'PracticeHomeTab', 'PracticeManualFrame', 'PracticeSettingsFrame',
         'PracticeMusicTrack', 'PracticeNarrationChoice', 'PracticeCharacterChoice', 'PracticeResultsFrame',
         'PracticeResultRound', 'PracticeMeditationFrame', 'PracticePatternsFrame', 'PracticeWhmFrame',
         'PracticeMovementFrame', 'PracticeFigureRequest', 'PracticeCourseFrame', 'PracticeCourseRow']

command = [sys.executable, str(KRYON / 'scripts/generate-widget-codecs.py'),
           '--output', str(ROOT / 'src/apps/app_codec.zi'),
           '--uses', str(KRYON / 'src/backend/widget_codec.zi'),
           '--generated-by', 'scripts/generate-app-codec.py']
for module in KRYON_MODULES:
    command += ['--source', str(KRYON / 'src/ui' / (module + '.zi'))]
for name in APP_TYPES:
    command += ['--source', str(ROOT / ('apps/diary' if name == 'diary_ui_types' else 'src/apps') / (name + '.zi'))]
for root in ROOTS:
    command += ['--root', root]
for line in ['"std/bundle_host"', '"std/byte_text_linux"', '"hosted_values"', '"widget_codec"',
             *(f', file "../../apps/diary/{name}.zi";' if name == 'diary_ui_types' else f', file "{name}.zi";' for name in APP_TYPES), *(f'"{module}"' for module in KRYON_MODULES)]:
    command += ['--import', line]
command += sys.argv[1:]
sys.exit(subprocess.run(command).returncode)
