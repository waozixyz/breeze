#!/bin/sh

set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
root_dir=$(dirname -- "$script_dir")
out_dir="$root_dir/build/site"
web_dir="$root_dir/build/dist/web"
kryon_dir=${KRYON_DIR:-"$root_dir/build/packages/kryon"}

require_path() {
	if [ ! -e "$1" ]; then
		printf 'Error: required path missing: %s\n' "$1" >&2
		exit 1
	fi
}

copy_path() {
	src=$1
	dst=$2
	require_path "$src"
	mkdir -p "$(dirname -- "$dst")"
	cp -R "$src" "$dst"
}

copy_dir_contents() {
	src=$1
	dst=$2
	require_path "$src"
	mkdir -p "$dst"
	cp -R "$src"/. "$dst"/
}

sync_shared_web_icons() {
	sync_script="$kryon_dir/scripts/sync-icons.sh"
	require_path "$sync_script"
	sh "$sync_script" "$root_dir/web-assets/icons" platforms language tiles
}

expand_template_file() {
	src=$1
	dst=$2
	version=$3
	asset_version=$4
	mkdir -p "$(dirname -- "$dst")"
	sed \
		-e "s#\\\${version}#$version#g" \
		-e "s#\\\${asset_version}#$asset_version#g" \
		"$src" > "$dst"
}

copy_template_file() {
	template_src=$1
	template_dst=$2
	template_version=$3
	template_asset_version=$4

	case ${template_src##*.} in
		html|htm|txt|xml|json|css|js)
			expand_template_file "$template_src" "$template_dst" "$template_version" "$template_asset_version"
			;;
		*)
			copy_path "$template_src" "$template_dst"
			;;
	esac
}

copy_template_dir() {
	template_src_dir=$1
	template_dst_dir=$2
	template_version=$3
	template_asset_version=$4

	require_path "$template_src_dir"
	find "$template_src_dir" -type d -print | while IFS= read -r dir_path; do
		rel=${dir_path#"$template_src_dir"}
		mkdir -p "$template_dst_dir$rel"
	done
	find "$template_src_dir" -type f -print | while IFS= read -r file_path; do
		rel=${file_path#"$template_src_dir"/}
		copy_template_file "$file_path" "$template_dst_dir/$rel" "$template_version" "$template_asset_version"
	done
}

write_site_imports() {
	asset_version=$1
	: > "$out_dir/style.css"
	{
		printf "@import url('/css/base.css?v=%s');\n" "$asset_version"
		printf "@import url('/css/components.css?v=%s');\n" "$asset_version"
		printf "@import url('/theme.css?v=%s');\n" "$asset_version"
	} >> "$out_dir/style.css"
}

write_web_app_csp_html() {
	src=$1
	dst=$2
	cache_version=$(date +%s)
	csp="default-src 'self' data: blob:; connect-src 'self' https: wss: http: ws:; script-src 'self' 'unsafe-eval' 'unsafe-inline' https://telegram.org; style-src 'self' 'unsafe-inline'; worker-src 'self' 'unsafe-eval' 'unsafe-inline' data: blob:; frame-src https:; img-src data: https:; media-src https:; object-src 'none'"
	meta="<meta http-equiv=\"Content-Security-Policy\" content=\"$csp\">"

	awk -v meta="$meta" -v version="$cache_version" '
		{
			gsub(/src="index\.js(\?v=[0-9A-Za-z._-]+)?"/, "src=\"index.js?v=" version "\"")
			if ($0 ~ /<meta http-equiv="Content-Security-Policy"/) {
				if (!done) print meta
				done = 1
				next
			}
			print
			if (!done && !inserted && $0 ~ /<meta charset="[^"]+"/) {
				print "    " meta
				inserted = 1
				done = 1
			}
			if (!done && $0 ~ /<\/head>/) {
				print "    " meta
				done = 1
			}
		}
	' "$src" > "$dst"
}

write_telegram_web_app_html() {
	src=$1
	dst=$2
	awk '
		BEGIN {
			viewport = "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, shrink-to-fit=no, viewport-fit=cover\">"
			css = "      html, body {\n        width: 100%;\n        height: 100%;\n        min-height: 100%;\n        overflow: hidden;\n        position: fixed;\n        inset: 0;\n        user-select: none;\n        -webkit-user-select: none;\n        -webkit-tap-highlight-color: transparent;\n        overscroll-behavior: none;\n        touch-action: none;\n      }\n\n      body {\n        background-color: var(--tg-theme-bg-color, #181818);\n        color: var(--tg-theme-text-color, #ffffff);\n      }\n\n      canvas,\n      canvas.emscripten {\n        display: block;\n        width: 100vw !important;\n        height: 100vh !important;\n        height: 100dvh !important;\n        touch-action: none;\n      }"
			script = "    <script src=\"https://telegram.org/js/telegram-web-app.js\"></script>\n    <script src=\"telegram-bridge.js\"></script>\n    <script>\n      (function() {\n        var tg = window.Telegram && window.Telegram.WebApp;\n        if (tg) {\n          tg.ready();\n          tg.expand();\n          if (tg.disableVerticalSwipes) tg.disableVerticalSwipes();\n          if (tg.setBackgroundColor) {\n            tg.setBackgroundColor((tg.themeParams && tg.themeParams.bg_color) || '\\''#181818'\\'');\n          }\n          if (tg.setHeaderColor) {\n            tg.setHeaderColor((tg.themeParams && tg.themeParams.bg_color) || '\\''#181818'\\'');\n          }\n        }\n\n        document.addEventListener('\\''touchmove'\\'', function(event) {\n          event.preventDefault();\n        }, { passive: false });\n\n        document.addEventListener('\\''gesturestart'\\'', function(event) {\n          event.preventDefault();\n        });\n      })();\n    </script>"
		}
		{
			if ($0 ~ /<meta name="viewport"/) {
				print "\t" viewport
				viewport_done = 1
				next
			}
			if (!viewport_done && $0 ~ /<\/head>/) {
				print "\t" viewport
				viewport_done = 1
			}
			if ($0 ~ /<\/style>/) {
				print css
				css_done = 1
			}
			if (!css_done && $0 ~ /<\/head>/) {
				print "<style>" css "\n    </style>"
				css_done = 1
			}
			if (!script_done && $0 ~ /<script>/) {
				print script
				script_done = 1
			}
			if (!script_done && $0 ~ /<\/body>/) {
				print script
				script_done = 1
			}
			print
		}
	' "$src" > "$dst"
}

require_output() {
	path=$1
	case "$path" in
		build/web/index.wasm|build/web/index.data|build/telegram/index.wasm|build/telegram/index.data)
			if [ -f "$out_dir/$path.gz" ] || [ -f "$out_dir/$path.parts.json" ]; then
				return
			fi
			;;
	esac
	if [ ! -e "$out_dir/$path" ]; then
		printf 'Error: required output missing: %s\n' "$path" >&2
		exit 1
	fi
}

version=$(python3 "$root_dir/scripts/check-version.py" --print-version) || {
	printf 'Error: could not read app version from %s\n' "$root_dir/src/core/version.h" >&2
	exit 1
}
release_version=${SITE_RELEASE_VERSION:-$version}
python3 -c 'import re, sys; assert re.fullmatch(r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)", sys.argv[1]), "Invalid download release version"' "$release_version"
asset_version=${SITE_ASSET_VERSION:-}
if [ -z "$asset_version" ]; then
	if git -C "$root_dir" diff --quiet --ignore-submodules HEAD -- 2>/dev/null; then
		asset_version=$(git -C "$root_dir" rev-parse --short HEAD 2>/dev/null || date +%s)
	else
		asset_version=$(date +%s)
	fi
fi

rm -rf "$out_dir"
mkdir -p "$out_dir"

copy_dir_contents "$script_dir/css" "$out_dir/css"
copy_path "$script_dir/themes/inbe.css" "$out_dir/theme.css"
write_site_imports "$asset_version"
copy_template_dir "$script_dir/static" "$out_dir" "$version" "$asset_version"
expand_template_file "$script_dir/index.html" "$out_dir/index.html" "$release_version" "$asset_version"
mkdir -p "$out_dir/legacy-converter"
cp "$out_dir/legacy-converter.html" "$out_dir/legacy-converter/index.html"

sync_shared_web_icons
copy_dir_contents "$root_dir/web-assets" "$out_dir/web-assets"
# Keep the released app's audio URL available alongside the current archive name.
copy_path "$out_dir/web-assets/dl/breathing-meditation-audio-v1.zip" "$out_dir/web-assets/dl/inbe-meditation-audio-v1.zip"
copy_dir_contents "$root_dir/site-icons" "$out_dir/site-icons"

copy_dir_contents "$web_dir" "$out_dir/build/web"
write_web_app_csp_html "$out_dir/build/web/index.html" "$out_dir/build/web/index.html.tmp"
mv "$out_dir/build/web/index.html.tmp" "$out_dir/build/web/index.html"

copy_dir_contents "$out_dir/build/web" "$out_dir/build/telegram"
copy_path "$root_dir/site/telegram-bridge.js" "$out_dir/build/telegram/telegram-bridge.js"
write_telegram_web_app_html "$out_dir/build/telegram/index.html" "$out_dir/build/telegram/index.html.tmp"
mv "$out_dir/build/telegram/index.html.tmp" "$out_dir/build/telegram/index.html"

# The worker streams compressed pieces at the original browser asset URLs.
python3 "$root_dir/scripts/prepare-site-assets.py" "$out_dir"

for path in \
	index.html \
	privacy.html \
	delete-account.html \
	delete-account/index.html \
	legacy-converter.html \
	legacy-converter/index.html \
	manifest.json \
	_headers \
	robots.txt \
	sitemap.xml \
	og.png \
	web-assets/dl/inbe-meditation-audio-v1.zip \
	web-assets/icons/inbe.png \
	web-assets/icons/github.png \
	web-assets/icons/itch.png \
	web-assets/icons/appimage.png \
	web-assets/icons/flatpak.png \
	web-assets/icons/snap.png \
	build/web/index.html \
	build/web/index.js \
	build/web/index.wasm \
	build/telegram/index.html \
	build/telegram/index.js \
	build/telegram/index.wasm \
	site-icons/favicon-32x32.png \
	css/base.css \
	css/components.css \
	theme.css
do
	require_output "$path"
done

# External preload packages are required only when the generated loader uses them.
for app in web telegram; do
	if grep -Fq 'index.data' "$out_dir/build/$app/index.js"; then
		require_output "build/$app/index.data"
	fi
done

printf 'built Inbe site at %s\n' "$out_dir"
