#!/usr/bin/env bash
# 本地批量构建 Redis 镜像（UOS / Kylin V11）
#
# 用法:
#   ./scripts/build-images.sh                          # 全部版本线 × 全部变体
#   ./scripts/build-images.sh --lines 8.8              # 只构建 8.8
#   ./scripts/build-images.sh --variants kylin         # 只构建 kylin 变体
#   ./scripts/build-images.sh --lines "8.8 8.10" --variants uos
#   IMAGE=registry.local/redis ./scripts/build-images.sh
#   PLATFORMS=linux/amd64,linux/arm64 PUSH=1 ./scripts/build-images.sh
#
# 环境变量:
#   IMAGE       镜像名前缀，默认 redis
#   PLATFORMS   为空则用普通 docker build；指定则用 buildx（多架构）
#   PUSH        1 = buildx 构建后推送
set -Eeuo pipefail

cd "$(dirname "$(readlink -f "$BASH_SOURCE")")/.."

IMAGE="${IMAGE:-redis}"
PLATFORMS="${PLATFORMS:-}"
PUSH="${PUSH:-0}"
VARIANTS_ARG="uos kylin"
LINES_ARG=""

while [ "$#" -gt 0 ]; do
	case "$1" in
		--lines)    LINES_ARG="${2:?--lines 需要参数}"; shift 2 ;;
		--variants) VARIANTS_ARG="${2:?--variants 需要参数}"; shift 2 ;;
		-h|--help)  sed -n '2,18p' "$0"; exit 0 ;;
		*) echo "未知参数: $1" >&2; exit 1 ;;
	esac
done

if [ -z "$LINES_ARG" ]; then
	LINES_ARG="$(find . -maxdepth 1 -type d -regex './[0-9]+\.[0-9]+' -printf '%f\n' | sort -V)"
fi

built=0
for line in $LINES_ARG; do
	for variant in $VARIANTS_ARG; do
		dir="$line/$variant"
		if [ ! -f "$dir/Dockerfile" ]; then
			echo "skip: $dir/Dockerfile 不存在"
			continue
		fi
		version="$(sed -nE 's/^ARG[[:space:]]+REDIS_VERSION=([^ #]+).*/\1/p' "$dir/Dockerfile" | tr -d '\r' | head -n1)"
		echo "==> 构建 $dir (Redis ${version:-unknown}) -> ${IMAGE}:${line}-${variant}"
		if [ -n "$PLATFORMS" ]; then
			out='--load'
			[ "$PUSH" = '1' ] && out='--push'
			docker buildx build --platform "$PLATFORMS" $out \
				-t "${IMAGE}:${line}-${variant}" -t "${IMAGE}:${version}-${variant}" \
				"$dir"
		else
			docker build -t "${IMAGE}:${line}-${variant}" -t "${IMAGE}:${version}-${variant}" "$dir"
		fi
		built=$((built + 1))
	done
done

echo "完成: 共构建 ${built} 个镜像"
