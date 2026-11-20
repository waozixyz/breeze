#!/usr/bin/env python3
"""Copy the currently published APT archive after checking its signatures and hashes."""

import hashlib
import re
import shutil
import subprocess
import sys
from pathlib import Path

ORIGIN = 'https://breeze.waozi.xyz/apt'
KEYRING = Path('packaging/linux/apt/breeze-archive-keyring.gpg').resolve()
DIST = 'dists/stable'


def download(destination, route):
    target = destination / route
    target.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(['curl', '-fsSL', '--retry', '3', '--max-time', '120',
                    f'{ORIGIN}/{route}', '-o', target], check=True)
    return target


def check_file(path, size, sha256):
    with path.open('rb') as stream:
        actual = hashlib.file_digest(stream, 'sha256').hexdigest()
    if path.stat().st_size != int(size) or actual != sha256:
        raise SystemExit(f'APT checksum differs for {path}')


def fields(paragraph):
    return dict(line.split(': ', 1) for line in paragraph.splitlines() if ': ' in line and not line.startswith(' '))


def main(destination):
    release = download(destination, f'{DIST}/Release')
    signature = download(destination, f'{DIST}/Release.gpg')
    inrelease = download(destination, f'{DIST}/InRelease')
    subprocess.run(['gpgv', '--keyring', KEYRING, signature, release], check=True)
    subprocess.run(['gpgv', '--keyring', KEYRING, inrelease], check=True)
    cleartext = inrelease.read_text().split('\n\n', 1)[1].split('-----BEGIN PGP SIGNATURE-----', 1)[0]
    if cleartext.rstrip() != release.read_text().rstrip():
        raise SystemExit('APT Release and InRelease describe different snapshots')
    checksums = release.read_text().split('\nSHA256:\n', 1)[1].split('\nSHA512:', 1)[0]
    indexed = {name: (size, digest) for digest, size, name in (line.split() for line in checksums.splitlines())}
    for architecture in ('amd64', 'arm64'):
        index = f'main/binary-{architecture}/Packages'
        packages = download(destination, f'{DIST}/{index}')
        check_file(packages, *indexed[index])
        for paragraph in packages.read_text().strip().split('\n\n'):
            package = fields(paragraph)
            route = package['Filename']
            if not re.fullmatch(rf'pool/main/i/inbe/inbe_[0-9]+\.[0-9]+\.[0-9]+_{architecture}\.deb', route):
                raise SystemExit('Unexpected APT package path')
            check_file(download(destination, route), package['Size'], package['SHA256'])
    shutil.copyfile(KEYRING, destination / 'breeze-archive-keyring.gpg')
    download(destination, 'inbe.sources')
    print('Preserved the verified live signed APT archive')


if __name__ == '__main__':
    main(Path(sys.argv[1]))
