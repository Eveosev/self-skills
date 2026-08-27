#!/usr/bin/env bash
# 从 HuggingFace / ModelScope 下载数据集，并通过 s3cmd sync 上传到内网可访问的 s3。
# 需先: conda activate base (已配置好 hf / modelscope / s3cmd)
set -euo pipefail

S3CFG="${S3CFG:-$HOME/Dev/s3.config}"
S3_BASE="${S3_BASE:-s3://payne/data}"
TMP_DIR="${TMP_DIR:-./_tmp_dl}"
DL_PROXY_DEFAULT="${DL_PROXY:-http://127.0.0.1:7890}"
SOURCE=""; REPO=""; DEST=""; KEEP=0; NO_UPLOAD=0; PROXY=""
declare -a INCLUDE=(); declare -a EXCLUDE=()

usage() {
  cat <<'EOF'
用法: pull_and_push.sh --source hf|modelscope --repo <id> [选项]

选项:
  --source hf|modelscope   数据集来源 (modelscope 可简写 ms)
  --repo <id>              数据集 id, 如 open-r1/DAPO-Math-17k-Processed
  --dest <name>            s3 子目录名 (缺省=repo 末段)
  --include <glob>         仅下载匹配文件 (可多次)
  --exclude <glob>         排除文件 (可多次)
  --proxy [url]           下载走本地代理 (缺省 http://127.0.0.1:7890, 仅作用于下载, 不影响 s3cmd)
  --no-upload             仅下载, 不上传 s3
  --keep                  保留本地临时目录 (调试用)
  -h, --help              显示帮助

环境变量: S3CFG(默认 ~/Dev/s3.config)  S3_BASE(默认 s3://payne/data)  TMP_DIR(默认 ./_tmp_dl)  DL_PROXY(--proxy 缺省值)

示例:
  bash scripts/pull_and_push.sh --source hf --repo open-r1/DAPO-Math-17k-Processed
  bash scripts/pull_and_push.sh --source modelscope --repo opencompass/AIME2025
EOF
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --source) SOURCE="$2"; shift 2;;
    --repo)   REPO="$2"; shift 2;;
    --dest)   DEST="$2"; shift 2;;
    --include) INCLUDE+=("$2"); shift 2;;
    --exclude) EXCLUDE+=("$2"); shift 2;;
    --proxy)
      if [[ $# -ge 2 && "$2" != --* ]]; then PROXY="$2"; shift 2; else PROXY="$DL_PROXY_DEFAULT"; shift; fi ;;
    --no-upload) NO_UPLOAD=1; shift;;
    --keep)   KEEP=1; shift;;
    -h|--help) usage;;
    *) echo "未知参数: $1"; usage;;
  esac
done

[[ -z "$SOURCE" || -z "$REPO" ]] && usage
DEST="${DEST:-$(basename "$REPO")}"
LOCAL_DIR="$TMP_DIR/$DEST"
mkdir -p "$LOCAL_DIR"

if [[ -n "$PROXY" ]]; then
  echo ">> 下载走代理: $PROXY (仅本步骤)"
  export http_proxy="$PROXY" https_proxy="$PROXY" all_proxy="$PROXY"
  # hf-mirror 当前会 308 跳回 huggingface.co, 走代理时直连原站更稳
  [[ "$SOURCE" == "hf" ]] && unset HF_ENDPOINT
fi

echo ">> [1/3] 下载 $REPO ($SOURCE) -> $LOCAL_DIR"
case "$SOURCE" in
  hf)
    args=(hf download "$REPO" --repo-type dataset --local-dir "$LOCAL_DIR")
    for p in ${INCLUDE[@]+"${INCLUDE[@]}"}; do args+=(--include "$p"); done
    for p in ${EXCLUDE[@]+"${EXCLUDE[@]}"}; do args+=(--exclude "$p"); done
    "${args[@]}" ;;
  modelscope|ms)
    args=(modelscope download --dataset "$REPO" --local_dir "$LOCAL_DIR")
    for p in ${INCLUDE[@]+"${INCLUDE[@]}"}; do args+=(--include "$p"); done
    for p in ${EXCLUDE[@]+"${EXCLUDE[@]}"}; do args+=(--exclude "$p"); done
    "${args[@]}" ;;
  *) echo "未知 source: $SOURCE (仅支持 hf / modelscope)"; exit 1;;
esac

# 清理代理, 避免影响内网 s3cmd
unset http_proxy https_proxy all_proxy 2>/dev/null || true

if [[ "$NO_UPLOAD" -eq 1 ]]; then
  echo ">> 已跳过上传 (--no-upload). 本地: $LOCAL_DIR"
  exit 0
fi

echo ">> [2/3] 上传 -> $S3_BASE/$DEST/"
s3cmd -c "$S3CFG" sync --exclude '.cache/*' --exclude '.msc' --exclude '.mv' \
  "$LOCAL_DIR/" "$S3_BASE/$DEST/"

echo ">> [3/3] 校验 s3 内容"
s3cmd -c "$S3CFG" ls "$S3_BASE/$DEST/"

if [[ "$KEEP" -eq 0 ]]; then
  rm -rf "$LOCAL_DIR"
  echo ">> 已清理本地临时目录 $LOCAL_DIR"
fi
echo ">> 完成: $S3_BASE/$DEST/"
