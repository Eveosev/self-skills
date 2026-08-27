---
name: dataset-to-s3
description: 从 HuggingFace 或 ModelScope 下载数据集，并通过 s3cmd 上传到内网可访问的 s3 (s3://payne/data)。当用户要求下载数据集、拉取 hf/modelscope 数据、或把数据集同步/上传到 s3 时使用。
---

# dataset-to-s3

在本机（可访问 HuggingFace / ModelScope，且已装 s3cmd）下载数据集并 `sync` 到 s3，
内网机器后续只需 `s3cmd` 从 s3 拉取，无需直连 HF/ModelScope。s3 在此充当中转站。

## 前置环境
- `conda activate base`（已配置好 `hf` / `modelscope` / `s3cmd`）
- s3cmd 配置文件：`~/Dev/s3.config`；目标桶：`s3://payne/data`
- **必须安装 `datasets` 包**：`pip install datasets`。否则 `modelscope download --dataset` 会报 `No module named 'datasets'`，并静默下载空目录（只生成 `.mv`/`._____temp`）。
- HuggingFace 需科学上网：本机 Clash 代理在 `http://127.0.0.1:7890`，下载 HF 时加 `--proxy`（见下）。

## 用法
```bash
# HuggingFace 需走代理 (--proxy 缺省 http://127.0.0.1:7890)
bash scripts/pull_and_push.sh --source hf         --repo <id> --proxy [--dest <name>]
# ModelScope 国内直连, 无需代理
bash scripts/pull_and_push.sh --source modelscope --repo <id> [--dest <name>]
```

## 参数
| 参数 | 说明 |
|---|---|
| `--source` | `hf` 或 `modelscope`（可简写 `ms`） |
| `--repo` | 数据集 id，如 `open-r1/DAPO-Math-17k-Processed` |
| `--dest` | s3 子目录名（缺省=repo 末段） |
| `--include` / `--exclude` | 只下/排除部分文件（glob，可多次） |
| `--proxy [url]` | 下载走本地代理（缺省 `http://127.0.0.1:7890`）。**仅作用于下载步骤，不影响内网 s3cmd** |
| `--no-upload` | 仅下载不上传（本地验证用） |
| `--keep` | 保留本地临时目录（调试用） |

可用环境变量覆盖默认值：`S3CFG`、`S3_BASE`、`TMP_DIR`。

## 流程
下载（hf/modelscope）→ 本地 `./_tmp_dl/<dest>/` → `s3cmd sync`（排除 `.cache/*` 等元数据）→ 回读 `s3cmd ls` 校验 → 清理本地临时目录。

## 内网机器取数
内网机器只需 s3cmd：
```bash
s3cmd -c ~/Dev/s3.config sync s3://payne/data/<name>/ ./<name>/
```

## 排查
- **ModelScope 下载出来是空目录**（只有 `.mv`/`._____temp`）：缺 `datasets` 包，`pip install datasets` 后重试。
- **HF 报 `Distant resource does not seem to be on huggingface.co` / 超时**：加 `--proxy`。注意 `hf-mirror.com` 目前会 `308` 跳回 `huggingface.co`，所以走代理直连原站比镜像更稳（脚本在 `--proxy` 时会自动 `unset HF_ENDPOINT`）。
- 上传失败：确认 `conda activate base`，且 `s3cmd -c ~/Dev/s3.config ls` 可用
- HF gated 数据集：`hf auth login` 后重试（或脚本内可扩展 `--token`）
- 磁盘不足：检查 `./_tmp_dl` 所在盘剩余空间，或用 `--include` 缩小下载范围

## 分发与移植
- 真身随本仓库通过 git 传输；本机使用走软链：
  ```bash
  ln -s <repo>/dataset-to-s3 ~/.cursor/skills/dataset-to-s3
  ```
- 核心逻辑全在 `scripts/pull_and_push.sh`，任何 Agent 框架（Codex / Antigravity 等）可直接 `bash` 调用；引用本 `SKILL.md` 或软链本目录即可。
