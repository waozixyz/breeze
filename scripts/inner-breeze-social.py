#!/usr/bin/env python3
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROFILE_DIR = ROOT / ".local" / "chromium-inner-breeze"
DEFAULT_DRAFT = ROOT / ".local" / "social-posts" / "latest-draft.txt"
DEFAULT_CONFIG = ROOT / "social-posts.local.json"
DEFAULT_RELEASE_REPO = "waozixyz/inbe"
DEFAULT_SITE_URL = "https://inbe.waozi.xyz/"
DEFAULT_X_COMPOSE_URL = "https://x.com/compose/post"
DEFAULT_X_DRAFT = ROOT / ".local" / "social-posts" / "latest-x-draft.txt"
DEFAULT_X_ATTACHMENTS = ROOT / ".local" / "social-posts" / "latest-x-attachments.txt"
DEFAULT_FEATURE_SCREENSHOTS = [
    ROOT / "build" / "screenshots" / "results" / "all-results-pages.png",
    ROOT / "build" / "screenshots" / "phone" / "06-habit-statistics-1080x1920.png",
]


def fail(message):
    print(f"inner-breeze-social: {message}", file=sys.stderr)
    return 1


def can_execute(path):
    return bool(path) and os.path.isfile(path) and os.access(path, os.X_OK)


def find_on_path(command):
    if not command:
        return ""
    if "/" in command:
        return command if can_execute(command) else ""
    return shutil.which(command) or ""


def resolve_browser(requested=""):
    candidates = [
        requested,
        os.environ.get("CHROMIUM_BIN", ""),
        os.environ.get("CHROME", ""),
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        "/snap/bin/chromium",
        "/opt/google/chrome/chrome",
        "chromium",
        "chromium-browser",
        "google-chrome",
        "google-chrome-stable",
        "chrome",
    ]
    tried = []
    for candidate in candidates:
        if not candidate or candidate in tried:
            continue
        tried.append(candidate)
        browser = find_on_path(candidate)
        if browser:
            return browser
    raise FileNotFoundError(f"Chrome/Chromium not found; tried {', '.join(tried)}")


def launch_chromium(args):
    browser = resolve_browser(args.browser)
    profile_dir = Path(args.profile_dir).expanduser().resolve()
    profile_dir.mkdir(parents=True, exist_ok=True)

    urls = args.url or [f"https://github.com/{DEFAULT_RELEASE_REPO}/releases/latest"]
    command = [
        browser,
        f"--user-data-dir={profile_dir}",
        "--profile-directory=Default",
        "--no-first-run",
        "--disable-default-apps",
        "--new-window",
        *urls,
    ]
    if args.remote_debugging_port:
        command.insert(-len(urls), f"--remote-debugging-port={args.remote_debugging_port}")

    process = subprocess.Popen(command)
    print(f"Chromium PID: {process.pid}")
    print(f"Profile: {profile_dir}")
    print("Log in to the posting accounts in this window, then leave it closed or open for later automation.")
    return 0


def read_latest_changelog(version):
    path = ROOT / "CHANGELOG.md"
    text = path.read_text(encoding="utf-8")
    heading = re.compile(r"^## \[(?P<version>[^\]]+)\] - (?P<date>\d{4}-\d{2}-\d{2})\s*$", re.MULTILINE)
    matches = list(heading.finditer(text))
    if not matches:
        raise ValueError("no version headings found in CHANGELOG.md")

    selected = None
    for index, match in enumerate(matches):
        if version and match.group("version") != version:
            continue
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        selected = (match, text[match.end():end])
        break

    if not selected:
        raise ValueError(f"version {version} not found in CHANGELOG.md")

    match, body = selected
    bullets = []
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            bullets.append(stripped[2:].strip())
    return match.group("version"), match.group("date"), bullets


def shorten(text, limit=170):
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip(" ,.;:") + "..."


def build_draft(args):
    version, release_date, bullets = read_latest_changelog(args.version)
    release_url = args.release_url or f"https://github.com/{DEFAULT_RELEASE_REPO}/releases/tag/v{version}"

    highlights = bullets[:3]
    lines = [
        f"Inner Breeze {version} is out.",
        "",
    ]
    for bullet in highlights:
        lines.append(f"- {shorten(bullet)}")
    lines.extend(["", f"Download: {release_url}", f"Website: {DEFAULT_SITE_URL}"])
    text = "\n".join(lines).strip() + "\n"

    out = Path(args.out).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(f"Wrote draft for {version} ({release_date}) to {out}")
    print()
    print(text, end="")
    return 0


def build_x_text(args):
    version, _, bullets = read_latest_changelog(args.version)
    release_url = args.release_url or f"https://github.com/{DEFAULT_RELEASE_REPO}/releases/tag/v{version}"

    text = (
        f"Inner Breeze {version} is out.\n\n"
        "New: results screen with mood check-in, mood trends in Habits, "
        "and Android bottom nav/keyboard fixes.\n\n"
        f"{release_url}"
    )
    if len(text) <= 280:
        return text

    highlights = [shorten(bullet, 70) for bullet in bullets[:2]]
    text = (
        f"Inner Breeze {version} is out.\n\n"
        f"{'; '.join(highlights)}\n\n"
        f"{release_url}"
    )
    if len(text) > 280:
        raise ValueError("generated X post text is longer than 280 characters")
    return text


def build_x_draft(args):
    text = build_x_text(args)
    out = Path(args.out).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text + "\n", encoding="utf-8")
    print(f"Wrote X draft to {out}")
    print()
    print(text)
    return 0


def write_x_bundle(args):
    text = load_x_post_text(args)
    if len(text) > 280:
        raise ValueError(f"X post text is {len(text)} characters; keep it at 280 or below")

    screenshots = resolve_screenshot_paths(args.screenshot) if args.screenshot else default_existing_screenshots()
    if args.require_screenshot and not screenshots:
        raise FileNotFoundError("no feature screenshots found; generate screenshots first or pass --screenshot")

    DEFAULT_X_DRAFT.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_X_DRAFT.write_text(text + "\n", encoding="utf-8")
    DEFAULT_X_ATTACHMENTS.write_text("".join(f"{path}\n" for path in screenshots), encoding="utf-8")
    return text, screenshots


def default_existing_screenshots():
    return [path for path in DEFAULT_FEATURE_SCREENSHOTS if path.exists()]


def resolve_screenshot_paths(paths):
    resolved = []
    for path_text in paths:
        path = Path(path_text).expanduser()
        if not path.is_absolute():
            path = ROOT / path
        path = path.resolve()
        if not path.is_file():
            raise FileNotFoundError(f"screenshot missing: {path}")
        resolved.append(path)
    return resolved


def load_post_text(args):
    if args.text:
        return args.text
    if args.text_file:
        return Path(args.text_file).expanduser().read_text(encoding="utf-8").strip()
    if DEFAULT_DRAFT.exists():
        return DEFAULT_DRAFT.read_text(encoding="utf-8").strip()
    version, _, _ = read_latest_changelog(args.version)
    draft_args = argparse.Namespace(
        version=version,
        release_url=args.release_url,
        out=str(DEFAULT_DRAFT),
    )
    build_draft(draft_args)
    return DEFAULT_DRAFT.read_text(encoding="utf-8").strip()


def load_x_post_text(args):
    if args.text:
        return args.text
    if args.text_file:
        return Path(args.text_file).expanduser().read_text(encoding="utf-8").strip()
    text = build_x_text(args)
    DEFAULT_X_DRAFT.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_X_DRAFT.write_text(text + "\n", encoding="utf-8")
    return text


def load_config(path):
    config_path = Path(path).expanduser().resolve()
    if not config_path.exists():
        raise FileNotFoundError(
            f"{config_path} does not exist. Copy config/social-posts.example.json to "
            "social-posts.local.json and fill in your target composer URLs/selectors."
        )
    with config_path.open("r", encoding="utf-8") as stream:
        data = json.load(stream)
    targets = data.get("targets")
    if not isinstance(targets, list) or not targets:
        raise ValueError(f"{config_path} must contain a non-empty targets list")
    return targets


def select_targets(targets, names):
    if not names:
        return targets
    wanted = set(names)
    selected = [target for target in targets if target.get("name") in wanted]
    missing = sorted(wanted - {target.get("name") for target in selected})
    if missing:
        raise ValueError(f"unknown target(s): {', '.join(missing)}")
    return selected


def selenium_post(args):
    if args.dry_run:
        print(load_post_text(args))
        print()
        print("Dry run: no browser automation ran.")
        return 0

    try:
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.keys import Keys
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.support.ui import WebDriverWait
    except ImportError as exc:
        raise ImportError("Install Selenium first: python3 -m pip install --user selenium") from exc

    text = load_post_text(args)
    targets = select_targets(load_config(args.config), args.target)

    profile_dir = Path(args.profile_dir).expanduser().resolve()
    profile_dir.mkdir(parents=True, exist_ok=True)

    options = webdriver.ChromeOptions()
    options.binary_location = resolve_browser(args.browser)
    options.add_argument(f"--user-data-dir={profile_dir}")
    options.add_argument("--profile-directory=Default")
    options.add_argument("--no-first-run")
    options.add_argument("--disable-default-apps")
    if args.headless:
        options.add_argument("--headless=new")

    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, args.timeout)
    try:
        for target in targets:
            name = target.get("name", "unnamed")
            url = target["url"]
            body_selector = target["body_selector"]
            submit_selector = target.get("submit_selector", "")

            print(f"Opening {name}: {url}")
            driver.get(url)
            body = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, body_selector)))
            body.click()
            body.send_keys(Keys.CONTROL, "a")
            body.send_keys(text)

            if args.submit:
                if not submit_selector:
                    raise ValueError(f"{name} has no submit_selector")
                submit = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, submit_selector)))
                submit.click()
                time.sleep(args.after_submit_delay)
                print(f"Submitted {name}")
            else:
                print(f"Filled {name}; not submitted. Re-run with --submit after checking the composer.")
    finally:
        if not args.keep_open:
            driver.quit()
    return 0


def x_manual(args):
    text, screenshots = write_x_bundle(args)
    print(text)
    if screenshots:
        print()
        for path in screenshots:
            print(f"attachment: {path}")
    print()
    print(f"Draft: {DEFAULT_X_DRAFT}")
    print(f"Attachments: {DEFAULT_X_ATTACHMENTS}")

    if args.dry_run:
        print("Dry run: did not open Chromium.")
        return 0

    launch_args = argparse.Namespace(
        browser=args.browser,
        profile_dir=args.profile_dir,
        url=[args.url],
        remote_debugging_port=0,
    )
    return launch_chromium(launch_args)
    return 0


def add_common_browser_args(parser):
    parser.add_argument("--profile-dir", default=str(DEFAULT_PROFILE_DIR), help="persistent Chromium user-data-dir")
    parser.add_argument("--browser", default="", help="Chrome/Chromium binary path or command")


def main(argv):
    parser = argparse.ArgumentParser(description="Inner Breeze release posting helper")
    subcommands = parser.add_subparsers(dest="command", required=True)

    login = subcommands.add_parser("login", help="launch Chromium with the dedicated Inner Breeze posting profile")
    add_common_browser_args(login)
    login.add_argument("--url", action="append", help="URL to open; may be repeated")
    login.add_argument("--remote-debugging-port", type=int, default=0)
    login.set_defaults(func=launch_chromium)

    draft = subcommands.add_parser("draft", help="write a release post draft from CHANGELOG.md")
    draft.add_argument("--version", default="", help="version from CHANGELOG.md; defaults to the newest entry")
    draft.add_argument("--release-url", default="", help="release URL; defaults to the GitHub tag URL")
    draft.add_argument("--out", default=str(DEFAULT_DRAFT), help="draft output path")
    draft.set_defaults(func=build_draft)

    x_draft = subcommands.add_parser("x-draft", help="write a short X release post from CHANGELOG.md")
    x_draft.add_argument("--version", default="", help="version from CHANGELOG.md; defaults to the newest entry")
    x_draft.add_argument("--release-url", default="", help="release URL; defaults to the GitHub tag URL")
    x_draft.add_argument("--out", default=str(DEFAULT_X_DRAFT), help="draft output path")
    x_draft.set_defaults(func=build_x_draft)

    post = subcommands.add_parser("post", help="fill configured social composers with the release post")
    add_common_browser_args(post)
    post.add_argument("--config", default=str(DEFAULT_CONFIG), help="local JSON target config")
    post.add_argument("--target", action="append", help="target name from config; may be repeated")
    post.add_argument("--version", default="", help="version to draft if no text is provided")
    post.add_argument("--release-url", default="", help="release URL used for generated text")
    post.add_argument("--text", default="", help="post text")
    post.add_argument("--text-file", default="", help="file containing post text")
    post.add_argument("--timeout", type=int, default=30)
    post.add_argument("--after-submit-delay", type=float, default=2.0)
    post.add_argument("--headless", action="store_true")
    post.add_argument("--keep-open", action="store_true")
    post.add_argument("--submit", action="store_true", help="click each configured submit button")
    post.add_argument("--dry-run", action="store_true", help="print the post text only")
    post.set_defaults(func=selenium_post)

    xpost = subcommands.add_parser("x-post", help="prepare the latest X release post and open the saved profile")
    add_common_browser_args(xpost)
    xpost.add_argument("--url", default=DEFAULT_X_COMPOSE_URL)
    xpost.add_argument("--version", default="", help="version from CHANGELOG.md; defaults to the newest entry")
    xpost.add_argument("--release-url", default="", help="release URL; defaults to the GitHub tag URL")
    xpost.add_argument("--text", default="", help="post text")
    xpost.add_argument("--text-file", default="", help="file containing post text")
    xpost.add_argument("--screenshot", action="append", help="screenshot path to attach; may be repeated")
    xpost.add_argument("--require-screenshot", action=argparse.BooleanOptionalAction, default=True)
    xpost.add_argument("--dry-run", action="store_true", help="print post text and attachments only")
    xpost.set_defaults(func=x_manual)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except Exception as exc:
        return fail(str(exc))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
