#!/bin/sh
# Hugging Face Space에 올릴 폴더를 만든다: 지금 커밋된 저장소 내용 + 데모 Dockerfile·Space 설명(README)을 루트에.
# 사용: sh deploy/demo/prepare_space.sh [만들 폴더, 기본 ../creditbridge-space]
set -e
cd "$(git rev-parse --show-toplevel)"
OUT="${1:-../creditbridge-space}"
rm -rf "$OUT"
mkdir -p "$OUT"
git archive HEAD | tar -x -C "$OUT"
cp deploy/demo/Dockerfile "$OUT/Dockerfile"
cp deploy/demo/SPACE_README.md "$OUT/README.md"
echo "준비 완료: $OUT"
echo "올리기: uvx --from huggingface_hub hf upload <허깅페이스아이디>/<Space이름> \"$OUT\" . --repo-type=space"
