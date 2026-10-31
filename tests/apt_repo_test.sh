#!/bin/sh
# scripts/build-apt-repo.sh signs a repository apt accepts, and refuses a key
# that differs from the published keyring or a deb that differs from its name.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT INT TERM
version=9.8.7

fail() {
	printf 'apt repo test: %s\n' "$1" >&2
	exit 1
}

make_deb() {
	pkg=$work/pkg-$1
	mkdir -p -m 755 "$pkg/DEBIAN" "$pkg/usr/bin"
	printf '#!/bin/sh\n' > "$pkg/usr/bin/breeze"
	chmod 755 "$pkg/DEBIAN" "$pkg/usr/bin/breeze"
	printf 'Package: inbe\nVersion: %s\nArchitecture: %s\nMaintainer: Test <t@example.invalid>\nDescription: test\n' \
		"$2" "$1" > "$pkg/DEBIAN/control"
	dpkg-deb --root-owner-group --build "$pkg" "$work/debs/inbe_${version}_$1.deb" >/dev/null
}

new_key() {
	GNUPGHOME=$work/gpg-$1 && export GNUPGHOME
	mkdir -m 700 "$GNUPGHOME"
	gpg --batch --quiet --passphrase '' --quick-gen-key "test $1 <t@example.invalid>" rsa2048 sign never 2>/dev/null
	gpg --export > "$work/$1.gpg"
	gpg --armor --export-secret-keys
	unset GNUPGHOME
}

mkdir -p "$work/debs"
make_deb amd64 "$version"
make_deb arm64 "$version"
key=$(new_key good)
other=$(new_key other)

APT_DEB_DIR=$work/debs APT_KEYRING=$work/good.gpg APT_SIGNING_KEY=$key \
	sh "$root/scripts/build-apt-repo.sh" "$work/repo" "$version" >/dev/null
for path in dists/stable/InRelease dists/stable/Release.gpg breeze-archive-keyring.gpg inbe.sources \
	dists/stable/main/binary-amd64/Packages dists/stable/main/binary-arm64/Packages \
	pool/main/i/inbe/inbe_${version}_amd64.deb pool/main/i/inbe/inbe_${version}_arm64.deb; do
	[ -s "$work/repo/$path" ] || fail "missing $path"
done

if APT_DEB_DIR=$work/debs APT_KEYRING=$work/good.gpg APT_SIGNING_KEY=$other \
	sh "$root/scripts/build-apt-repo.sh" "$work/bad-key" "$version" 2>/dev/null; then
	fail "accepted a key that differs from the keyring"
fi

make_deb arm64 9.8.6
if APT_DEB_DIR=$work/debs APT_KEYRING=$work/good.gpg APT_SIGNING_KEY=$key \
	sh "$root/scripts/build-apt-repo.sh" "$work/bad-deb" "$version" 2>/dev/null; then
	fail "accepted a deb whose version differs from its name"
fi

# apt itself verifies the signature and finds the package, without root.
apt_dir=$work/apt
mkdir -p "$apt_dir/etc/sources.list.d" "$apt_dir/etc/preferences.d" "$apt_dir/state/lists/partial" \
	"$apt_dir/cache/archives/partial"
: > "$apt_dir/state/status"
sed -e "s#https://breeze.waozi.xyz/apt#file://$work/repo#" \
	-e "s#/usr/share/keyrings/breeze-archive-keyring.gpg#$work/good.gpg#" \
	"$work/repo/inbe.sources" > "$apt_dir/etc/sources.list.d/inbe.sources"
apt_opts="-o Dir::Etc=$apt_dir/etc -o Dir::Etc::sourcelist=/dev/null -o Dir::State=$apt_dir/state
	-o Dir::State::status=$apt_dir/state/status -o Dir::Cache=$apt_dir/cache -o Debug::NoLocking=1
	-o APT::Architecture=amd64"
# shellcheck disable=SC2086
apt-get $apt_opts update >"$work/apt-update.log" 2>&1 || { cat "$work/apt-update.log" >&2; fail "apt update failed"; }
grep -q -E '^(W|E):' "$work/apt-update.log" && { cat "$work/apt-update.log" >&2; fail "apt update warned"; }
# shellcheck disable=SC2086
candidate=$(apt-cache $apt_opts policy inbe | awk '/Candidate:/ { print $2 }')
[ "$candidate" = "$version" ] || fail "apt candidate is '$candidate', expected $version"
echo "apt repo test passed"
