#!/usr/bin/env bash
# Tailwind CSS standalone CLI로 frontend/tailwind/input.css → frontend/static/css/app.css 를 빌드한다.
# CLI 바이너리: https://github.com/tailwindlabs/tailwindcss/releases (v4.x) 를 ./bin/tailwindcss 에 두거나 TAILWIND로 경로 지정
set -euo pipefail
TAILWIND="${TAILWIND:-./bin/tailwindcss}"
"$TAILWIND" -i frontend/tailwind/input.css -o frontend/static/css/app.css --minify "$@"
