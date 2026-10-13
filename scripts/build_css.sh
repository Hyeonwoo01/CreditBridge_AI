#!/usr/bin/env bash
# Tailwind CSS standalone CLI로 app/web/static/css/app.css를 빌드한다.
# CLI 바이너리: https://github.com/tailwindlabs/tailwindcss/releases (v4.x) 를 ./bin/tailwindcss 에 두거나 TAILWIND로 경로 지정
set -euo pipefail
TAILWIND="${TAILWIND:-./bin/tailwindcss}"
"$TAILWIND" -i app/web/static/css/input.css -o app/web/static/css/app.css --minify "$@"
