#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 1 ]; then
  echo "usage: $0 PACKAGE_FILE [EXTRA_PACKAGE ...]" >&2
  exit 2
fi

package_file="$1"
shift

if [ ! -f "$package_file" ]; then
  echo "package file not found: $package_file" >&2
  exit 2
fi

mapfile -t raw_packages < "$package_file"
packages=()
for package in "${raw_packages[@]}" "$@"; do
  if [ -z "$package" ] || [[ "$package" == \#* ]]; then
    continue
  fi
  packages+=("$package")
done

missing=()
for package in "${packages[@]}"; do
  if ! dpkg-query -W -f='${Status}\n' "$package" 2>/dev/null | grep -qx 'install ok installed'; then
    missing+=("$package")
  fi
done
if [ "${#missing[@]}" -eq 0 ]; then
  echo "All ${#packages[@]} requested apt packages are already installed; skipping apt-get."
  exit 0
fi

APT_CACHE_DIR="${APT_CACHE_DIR:-/tmp/apt-cache}"
apt_arch="$(dpkg --print-architecture)"
ubuntu_archive="https://archive.ubuntu.com/ubuntu"
if [ "$apt_arch" = "arm64" ]; then
  ubuntu_archive="http://ports.ubuntu.com/ubuntu-ports"
fi
codename="$(
  . /etc/os-release
  printf '%s' "${VERSION_CODENAME:-jammy}"
)"

# GitHub-hosted Ubuntu runners sometimes use an Azure mirrorlist that stalls.
# Pin Ubuntu packages to the canonical archive before running apt. arm64
# packages live on ports.ubuntu.com, not archive.ubuntu.com.
if [ -f /etc/apt/apt-mirrors.txt ]; then
  printf '%s\n' "$ubuntu_archive" | sudo tee /etc/apt/apt-mirrors.txt >/dev/null
fi

while IFS= read -r -d '' source_file; do
  sudo sed -i \
    -e "s|mirror+file:/etc/apt/apt-mirrors.txt|$ubuntu_archive|g" \
    -e "s|http://azure.archive.ubuntu.com/ubuntu|$ubuntu_archive|g" \
    -e "s|https://azure.archive.ubuntu.com/ubuntu|$ubuntu_archive|g" \
    -e "s|http://archive.ubuntu.com/ubuntu|$ubuntu_archive|g" \
    -e "s|https://archive.ubuntu.com/ubuntu|$ubuntu_archive|g" \
    -e "s|http://ports.ubuntu.com/ubuntu-ports|$ubuntu_archive|g" \
    -e "s|https://ports.ubuntu.com/ubuntu-ports|$ubuntu_archive|g" \
    "$source_file"
done < <(find /etc/apt -type f \( -name '*.list' -o -name '*.sources' \) -print0)

sudo tee /etc/apt/sources.list.d/ubuntu.sources >/dev/null <<EOF
Types: deb
URIs: $ubuntu_archive
Suites: $codename ${codename}-updates ${codename}-backports ${codename}-security
Components: main restricted universe multiverse
Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg
EOF

mkdir -p "$APT_CACHE_DIR/partial"
sudo rm -rf /var/lib/apt/lists/*
sudo apt-get \
  -o Acquire::Retries=3 \
  -o Acquire::http::Timeout=20 \
  -o Acquire::https::Timeout=20 \
  update
if [ "${#missing[@]}" -gt 0 ]; then
  sudo apt-get \
    -o Acquire::Retries=3 \
    -o Acquire::http::Timeout=20 \
    -o Acquire::https::Timeout=20 \
    -o Dir::Cache::archives="$APT_CACHE_DIR" \
    install -y "${missing[@]}"
fi
sudo chown -R "$USER:$USER" "$APT_CACHE_DIR"
