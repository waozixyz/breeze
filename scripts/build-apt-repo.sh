#!/bin/sh
# Build the signed APT repository for a published release under the site:
#   build-apt-repo.sh OUT_DIR VERSION
# APT_SIGNING_KEY holds the armored private key; its public half is
# packaging/linux/apt/breeze-archive-keyring.gpg. APT_DEB_DIR, when set,
# supplies the .deb files instead of downloading them from the release.

set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
root_dir=$(dirname -- "$script_dir")
keyring=${APT_KEYRING:-"$root_dir/packaging/linux/apt/breeze-archive-keyring.gpg"}
archs="amd64 arm64"

if [ "$#" -ne 2 ]; then
	printf 'Usage: %s OUT_DIR VERSION\n' "$0" >&2
	exit 2
fi
out_dir=$1
version=$2

if [ -z "${APT_SIGNING_KEY:-}" ]; then
	printf 'Error: APT_SIGNING_KEY is not set\n' >&2
	exit 1
fi
for tool in apt-ftparchive gpg gpgv; do
	if ! command -v "$tool" >/dev/null 2>&1; then
		printf 'Error: %s is required\n' "$tool" >&2
		exit 1
	fi
done

GNUPGHOME=$(mktemp -d)
export GNUPGHOME
trap 'rm -rf "$GNUPGHOME"' EXIT INT TERM

rm -rf "$out_dir"
pool="$out_dir/pool/main/i/inbe"
mkdir -p "$pool"
for arch in $archs; do
	deb="inbe_${version}_${arch}.deb"
	if [ -n "${APT_DEB_DIR:-}" ]; then
		cp "$APT_DEB_DIR/$deb" "$pool/$deb"
	else
		gh release download "v$version" --repo waozixyz/breeze --pattern "$deb" --dir "$pool"
	fi
	# A deb whose control fields disagree with its name would publish a wrong upgrade.
	fields=$(dpkg-deb -f "$pool/$deb" Package Version Architecture | tr '\n' ' ')
	if [ "$fields" != "Package: inbe Version: $version Architecture: $arch " ]; then
		printf 'Error: %s has control fields %s\n' "$deb" "$fields" >&2
		exit 1
	fi
done

dist="$out_dir/dists/stable"
for arch in $archs; do
	mkdir -p "$dist/main/binary-$arch"
	# Uncompressed only: the CDN may re-encode .gz responses.
	(cd "$out_dir" && apt-ftparchive --arch "$arch" packages pool) > "$dist/main/binary-$arch/Packages"
done

apt-ftparchive \
	-o APT::FTPArchive::Release::Origin="Waozi" \
	-o APT::FTPArchive::Release::Label="Inner Breeze" \
	-o APT::FTPArchive::Release::Suite="stable" \
	-o APT::FTPArchive::Release::Codename="stable" \
	-o APT::FTPArchive::Release::Architectures="$archs" \
	-o APT::FTPArchive::Release::Components="main" \
	-o APT::FTPArchive::Release::Description="Inner Breeze releases" \
	release "$dist" > "$GNUPGHOME/Release"
mv "$GNUPGHOME/Release" "$dist/Release"

printf '%s\n' "$APT_SIGNING_KEY" | gpg --batch --quiet --import
gpg --batch --yes --digest-algo SHA512 --clearsign --output "$dist/InRelease" "$dist/Release"
gpg --batch --yes --digest-algo SHA512 --armor --detach-sign --output "$dist/Release.gpg" "$dist/Release"

# Users trust only the committed keyring, so the signature must verify against it.
gpgv --keyring "$keyring" "$dist/InRelease" 2>/dev/null || {
	printf 'Error: APT_SIGNING_KEY does not match %s\n' "$keyring" >&2
	exit 1
}
gpgv --keyring "$keyring" "$dist/Release.gpg" "$dist/Release" 2>/dev/null

cp "$keyring" "$out_dir/breeze-archive-keyring.gpg"
cat > "$out_dir/inbe.sources" <<'EOF'
Types: deb
URIs: https://breeze.waozi.xyz/apt
Suites: stable
Components: main
Signed-By: /usr/share/keyrings/breeze-archive-keyring.gpg
EOF
printf 'APT repository for inbe %s written to %s\n' "$version" "$out_dir"
