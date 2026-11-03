"""Exercise production hosts with disposable signed accounts and local Daochi.

Run through build-queue. Starts its own private Xvfb and test-only backend;
never uses the desktop, installed app data, production nodes or purchases.
"""
import argparse
import contextlib
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import tempfile
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from ui_driver import UiDriver

ROOT = Path(__file__).resolve().parents[1]
PROJECTS = ROOT.parents[2]
BACKEND = PROJECTS / 'kryonlabs/daochi'
SCRUB = ('DISPLAY', 'WAYLAND_DISPLAY', 'XAUTHORITY', 'DBUS_SESSION_BUS_ADDRESS',
         'SESSION_MANAGER', 'GDK_DISPLAY')


def wait(predicate, label, timeout=40):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        result = predicate()
        if result:
            return result
        time.sleep(.1)
    raise AssertionError(label)


def stop(process):
    if process.poll() is None:
        process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app', choices=('breeze', 'shovey', 'wurm'), required=True)
    parser.add_argument('--binary', type=Path, required=True)
    parser.add_argument('--static-curl', action='store_true', help='Use explicitly test-linked Breeze host')
    args = parser.parse_args()
    assert not any(os.environ.get(key) for key in SCRUB), 'Inherited desktop environment'
    output = ROOT / 'work/referral-host' / ('ui-' + args.app)
    subprocess.run(['git', 'check-ignore', '-q', str(output)], cwd=ROOT, check=True)
    output.mkdir(parents=True, exist_ok=True)
    shim = output / 'referral-http-fixture.so'
    subprocess.run(['cc', '-shared', '-fPIC', '-O2', '-Wall', '-Wextra',
                    '-I' + str(ROOT / 'vendor-builds/linux/x86_64/inbe-curl/include'),
                    str(ROOT / 'tests/referral_http_fixture.c'), '-ldl', '-o', str(shim)], check=True)
    with contextlib.ExitStack() as stack:
        private = Path(stack.enter_context(tempfile.TemporaryDirectory(dir=output)))
        env = {key: value for key, value in os.environ.items() if key not in SCRUB}
        env.update(YUE_DESKTOP_RECOVERY='0', SDL_AUDIODRIVER='dummy', APP_NO_TRAY='1',
                   LIBGL_ALWAYS_SOFTWARE='1', LANG='en_US.UTF-8')
        for key in ('http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY'):
            env.pop(key, None)
        env['NO_PROXY'] = '*'
        # curl-only test shim changes transport after canonical-origin validation.
        # The actual client and signed request/auth logic remain production code.
        report = private / 'server.json'
        server_log = stack.enter_context((output / 'server.log').open('w'))
        server = subprocess.Popen([str(BACKEND / 'work/referral-fixture.test'),
            '-test.run', '^TestReferralBrowserFixture$', '-test.v', '-test.timeout=30m'],
            cwd=BACKEND, env=env | {'DAOCHI_REFERRAL_FIXTURE_REPORT': str(report)},
            stdout=server_log, stderr=subprocess.STDOUT)
        stack.callback(stop, server)
        wait(report.exists, 'fixture did not start')
        metadata = json.loads(report.read_text())
        assert metadata['synthetic'] and metadata['real_mldsa']
        assert metadata['url'].startswith('http://127.0.0.1:')

        def control(path, body=None):
            request = Request(metadata['url'] + '/fixture/' + path,
                data=json.dumps(body or {}).encode(), method='POST',
                headers={'X-Fixture-Key': metadata['control_key'], 'Content-Type': 'application/json'})
            try:
                with urlopen(request, timeout=20) as response:
                    return json.load(response)
            except HTTPError as error:
                raise AssertionError('fixture ' + path + ': ' + str(error.code) + ' ' +
                                     error.read(512).decode(errors='replace')) from None

        display_log = stack.enter_context((output / 'display.log').open('w'))
        display = subprocess.Popen(['Xvfb', '-noreset', '-displayfd', '1', '-screen', '0',
            '1000x1600x24', '-nolisten', 'tcp'], env=env, stdout=subprocess.PIPE, stderr=display_log)
        stack.callback(stop, display)
        number = display.stdout.readline().decode().strip()
        display.stdout.close()
        assert number.isdecimal()
        env['DISPLAY'] = ':' + number

        @contextlib.contextmanager
        def application(name):
            data = private / name
            data.mkdir(exist_ok=True)
            driver = UiDriver(data / 'driver')
            xdg = data / 'xdg'
            account = (xdg / 'wurm/profile' if args.app == 'wurm' else data / 'arcade/entity')
            account.mkdir(parents=True, exist_ok=True)
            prefs = account / 'entity.json'
            if not prefs.exists():
                prefs.write_text(json.dumps(dict(version=1, owner_id='', name='', intention='',
                    picture=0, theme=0, accent=0, material=0, controls=31, preferred=0,
                    nodes=['https://api.waozi.xyz'], extensions=[])))
            child_env = env | driver.environment() | dict(LD_PRELOAD='' if args.static_curl else str(shim),
                REFERRAL_TEST_URL=metadata['url'], XDG_DATA_HOME=str(xdg),
                HOME=str(data), ARCADE_DATA=str(data / 'arcade'), WURM_WINDOW='900x1500',
                APP_DATA_ROOT=str(data / 'breeze'), INBE_SCREENSHOT_DATA_ROOT=str(data / 'breeze'))
            if args.app == 'breeze':
                child_env['INBE_DEBUG_ROUTE'] = '1'
            log_path = output / (name + '.log')
            with log_path.open('w') as log:
                child = subprocess.Popen([str(args.binary.resolve())],
                    cwd=args.binary.resolve().parent if args.app == 'shovey' else
                    (PROJECTS / 'waozixyz/games/wurm' if args.app == 'wurm' else ROOT),
                    env=child_env, stdout=log, stderr=subprocess.STDOUT)
                driver.attach(child, log_path)
                try:
                    yield driver, account
                finally:
                    stop(child)

        def press(driver, **selector):
            # Scroll only the owned app's committed UI on this private display.
            for _ in range(18):
                if driver.find(visible=True, **selector):
                    driver.press(**selector)
                    return
                if args.app == 'shovey':
                    driver.pointer(240, 350, wheel=-6)
                else:
                    driver.pointer(450, 700, wheel=-6)
            visible = [(n.get('key'), n.get('label'), n.get('kind')) for n in driver.tree() if n.get('visible') and n.get('label')][:60]
            raise AssertionError('No visible widget: ' + repr(selector) + '; visible=' + repr(visible))

        def referrals(driver):
            if args.app == 'breeze':
                if driver.find(label='Not now', role='button', visible=True):
                    driver.press(label='Not now', role='button')
                driver.press(label='Apps', role='button')
                if driver.find(key=83110, visible=True):
                    driver.press(key=83110)
                    driver.wait_gone(key=83110)
                driver.wait_idle(frames=2, timeout=2)
                if driver.find(label="Don't allow", role='button', visible=True):
                    driver.press(label="Don't allow", role='button')
                    driver.wait_gone(label='App updates', kind='modal')
                profile = driver.wait(focus_id=6792, role='button')
                print('Breeze Profile control:', json.dumps({key: profile.get(key) for key in
                    ('key', 'enabled', 'visible', 'x', 'y', 'width', 'height', 'focus_id')}), flush=True)
                driver.wait_idle(frames=2, timeout=2)
                before = driver.send('tree')
                (output / 'profile-before-press.json').write_text(json.dumps(before))
                print('Breeze before Profile:', json.dumps({
                    'frame': before.get('frame'), 'count': len(before['nodes']),
                    'controls': [node for node in before['nodes']
                                 if node.get('index') in (8, 42) or node.get('focus_id') == 6792]}), flush=True)
                reply = driver.send('press', focus_id=6792, role='button', visible=True)
                (output / 'profile-press-reply.json').write_text(json.dumps(reply))
                print('Breeze Profile press:', json.dumps(reply), flush=True)
                try:
                    driver.wait(key=78030, visible=False)
                except AssertionError:
                    # This display was created above exclusively for this test.
                    # Capture the unresolved Apps input interception before signup.
                    from PIL import ImageGrab
                    ImageGrab.grab(xdisplay=env['DISPLAY']).save(output / 'profile-navigation.png')
                    (output / 'profile-navigation-tree.json').write_text(json.dumps(driver.tree()))
                    raise
            else:
                if driver.find(label='Not now', role='button'):
                    driver.press(label='Not now', role='button')
                press(driver, label='Shop', role='button')
                press(driver, label='Profile' if args.app == 'shovey' else 'Dew', role='button')
            press(driver, key=78030)
            driver.wait(key=78003)

        def create(driver, account):
            referrals(driver)
            press(driver, key=78005)
            press(driver, key=820)
            if args.app == 'breeze':
                database = account.parents[1] / 'breeze/inbe.db'
                def current_id():
                    if not database.exists():
                        return None
                    with contextlib.closing(sqlite3.connect(database.as_uri() + '?mode=ro', uri=True)) as db:
                        ids = db.execute("SELECT value FROM settings WHERE key='sync_public_id' AND length(value)=64").fetchall()
                    return ids[0][0] if len(ids) == 1 else None
                identity = wait(current_id, 'current Breeze host did not persist its created account')
                finish_signup(driver)
                return identity
            key = account / 'account.key'
            wait(key.exists, 'current host did not save its created account')
            text = key.read_text()
            # The fixture reads only the public identifier; never log key bytes.
            identifier = re.search(r'^(?:public_id|account_id)=([0-9a-f]{64})$', text, re.MULTILINE)
            if identifier:
                finish_signup(driver)
                return identifier.group(1)
            obj = json.loads(text)
            def owner(value):
                if isinstance(value, dict):
                    for name, item in value.items():
                        if name in ('public_id', 'account_id') and isinstance(item, str) and re.fullmatch('[0-9a-f]{64}', item):
                            return item
                    for item in value.values():
                        found = owner(item)
                        if found:
                            return found
                return None
            identity = owner(obj)
            assert identity, 'No public account identifier'
            finish_signup(driver)
            return identity

        def finish_signup(driver):
            # Creation saves before its backup offer reaches the next frame.
            # Wait for the real transition; an unconditional Back could leave
            # the shop while native signup is still completing.
            def return_to_referrals():
                if driver.find(key=78003):
                    return True
                if driver.find(label='Not now', role='button', visible=True):
                    driver.press(label='Not now', role='button')
                elif driver.find(key=78030, visible=True):
                    press(driver, key=78030)
                elif driver.find(contains='password', role='text_field') or driver.find(contains='Back up', visible=True):
                    # The production host forwards Back to Entity's backup
                    # page; it must not close the enclosing game shop.
                    driver.press(label='Back', role='button')
                return False
            try:
                wait(return_to_referrals, 'signup did not return to the referral review', 60)
            except AssertionError:
                visible = [(n.get('key'), n.get('label', '')[:128], n.get('kind'))
                           for n in driver.tree() if n.get('visible') and n.get('kind') != 'text_field'][:50]
                raise AssertionError('signup referral navigation; visible=' + repr(visible)) from None
            # The local key is saved before the signed node connection ends.
            # A real summary proves that this account is registered and the
            # current verified provider can authenticate before fixture setup.
            driver.wait(key=78010, timeout=60, visible=False)

        with application('inviter') as (driver, account):
            inviter = create(driver, account)
            invitation = control('seed', dict(account_id=inviter, count=1))['code']
        with application('friend') as (driver, account):
            friend = create(driver, account)
            assert friend != inviter
            assert not driver.find(key=78006), 'new account inherited a welcome receipt'
            assert not driver.find(key=78018), 'new account inherited a referrer'
            press(driver, key=107)
            driver.key('a', control=True)
            driver.type(invitation)
            press(driver, key=78024)
            assert not driver.find(key=78006), 'review accepted without confirmation'
            press(driver, key=78022)
            gift = wait(lambda: driver.find(key=78006), 'no immediate welcome confirmation', 60)
            assert re.search(r'\b20\b', gift[0].get('label', '')), 'welcome confirmation did not show 20 Dew'
            assert not driver.find(key=78024), 'successful claim still offered'
        # Another private device loads the same valid current account through
        # the real host loader. The global binding must survive process/device
        # changes and must not offer a second welcome claim.
        shutil.copytree(private / 'friend', private / 'friend-device',
                        ignore=shutil.ignore_patterns('driver'))
        with application('friend-device') as (driver, account):
            referrals(driver)
            wait(lambda: driver.find(key=78018), 'referrer binding missing on another device', 60)
            assert not driver.find(key=78024), 'second device offered another welcome claim'
        with application('inviter') as (driver, account):
            referrals(driver)
            wait(lambda: any(friend in node.get('label', '') for node in driver.tree()),
                 'nonpurchasing friend missing from inviter list', 60)
            person = next(node for node in driver.tree() if friend in node.get('label', ''))
            dates = driver.find(key=person['key'] + 1)
            assert any(re.search(r'\d{4}-\d{2}-\d{2}', row.get('label', '')) for row in dates), 'accepted friend has no acceptance date'
        control('stop')
        (output / 'result.json').write_text(json.dumps(dict(app=args.app,
            immediate_no_purchase=True, accepted_nonpurchaser=True, acceptance_date=True,
            second_device_binding=True, private_display=True)) + '\n')
        print(args.app + ': actual host signup, immediate gift and accepted nonpurchaser local UI test passed')


if __name__ == '__main__':
    main()
