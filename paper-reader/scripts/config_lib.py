"""
paper-reader 的可移植性核心。

所有路径 / 密钥 / 二进制均通过“环境变量 -> 本地配置 -> 机器级配置 -> 自动探测”
的解析链得到，脚本本身不包含任何绝对路径或机器特定假设。这样同一份代码在
任意机器、任意 Agent 客户端下都能直接运行。
"""

import json
import os
import re
import shutil
import unicodedata
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent

MACHINE_CONFIG_PATH = Path(os.path.expanduser("~/.config/paper-reader/config.json"))
LOCAL_CONFIG_PATH = SKILL_DIR / "config.local.json"
EXAMPLE_CONFIG_PATH = SKILL_DIR / "config.example.json"

DEFAULT_LLM_BASE_URL = "https://api.deepseek.com/v1"
DEFAULT_LLM_MODEL = "deepseek-chat"

PLACEHOLDER_VALUES = {"", "YOUR_API_KEY_HERE", "sk-xxx", "changeme"}

MINERU_BIN_CANDIDATES = [
    "/opt/homebrew/anaconda3/envs/pdfparse/bin/magic-pdf",
    "/opt/homebrew/anaconda3/bin/magic-pdf",
    "/opt/homebrew/Caskroom/miniforge/base/bin/magic-pdf",
    "/opt/homebrew/bin/magic-pdf",
    os.path.expanduser("~/anaconda3/envs/pdfparse/bin/magic-pdf"),
    os.path.expanduser("~/miniconda3/envs/pdfparse/bin/magic-pdf"),
    os.path.expanduser("~/miniforge3/envs/pdfparse/bin/magic-pdf"),
    os.path.expanduser("~/miniconda3/bin/magic-pdf"),
    os.path.expanduser("~/miniforge3/bin/magic-pdf"),
    os.path.expanduser("~/.local/bin/magic-pdf"),
    "/usr/local/bin/magic-pdf",
]

MARKER_BIN_CANDIDATES = [
    "/opt/homebrew/anaconda3/envs/pdfparse/bin/marker_single",
    "/opt/homebrew/anaconda3/bin/marker_single",
    "/opt/homebrew/Caskroom/miniforge/base/bin/marker_single",
    "/opt/homebrew/bin/marker_single",
    os.path.expanduser("~/anaconda3/envs/pdfparse/bin/marker_single"),
    os.path.expanduser("~/miniconda3/envs/pdfparse/bin/marker_single"),
    os.path.expanduser("~/miniforge3/envs/pdfparse/bin/marker_single"),
    os.path.expanduser("~/miniconda3/bin/marker_single"),
    os.path.expanduser("~/miniforge3/bin/marker_single"),
    os.path.expanduser("~/.local/bin/marker_single"),
    "/usr/local/bin/marker_single",
]

# 顶层目录中与"分类"无关的基础设施目录, 供 get_general_categories 排除
INFRA_DIR_BLOCKLIST = {
    "assets", "extracted", "scratch", "_archive", "90_Meta", "VIMPO",
    ".obsidian", ".git", ".cursor", ".joycode", ".understand-anything",
}


class ConfigError(RuntimeError):
    pass


def _load_json(path: Path):
    if not path or not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _deep_merge(base: dict, override: dict) -> dict:
    result = dict(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def find_git_root(start: Path) -> Path:
    """从 start 向上查找最近的 .git 目录, 找不到则返回 start 本身。"""
    current = Path(start).resolve()
    for parent in [current, *current.parents]:
        if (parent / ".git").exists():
            return parent
    return current


def load_config(explicit_path: str = None) -> dict:
    """
    合并顺序(后者覆盖前者): config.example.json(结构默认值, 无密钥)
    < 机器级 ~/.config/paper-reader/config.json < 技能本地 config.local.json
    < 显式传入的 --config 路径。
    环境变量不在此处合并, 由 get_llm_settings / get_vault_path 在使用时覆盖,
    保证"环境变量优先级最高"。
    """
    config = _load_json(EXAMPLE_CONFIG_PATH)
    config = _deep_merge(config, _load_json(MACHINE_CONFIG_PATH))
    config = _deep_merge(config, _load_json(LOCAL_CONFIG_PATH))
    if explicit_path:
        config = _deep_merge(config, _load_json(Path(explicit_path)))
    return config


def get_vault_path(config: dict) -> Path:
    """
    解析链: 环境变量 NOTES_VAULT -> config['obsidian_vault']
    -> 自动探测本技能所在仓库的 git 根目录 -> 当前工作目录。
    """
    candidates = [
        os.environ.get("NOTES_VAULT"),
        (config or {}).get("obsidian_vault"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).expanduser().exists():
            return Path(candidate).expanduser().resolve()

    git_root = find_git_root(SKILL_DIR)
    if git_root.exists():
        return git_root

    return Path.cwd()


def get_llm_settings(config: dict) -> dict:
    """
    解析链(每个字段独立): 环境变量(OPENAI_API_KEY 系列, 或部分机器上已配置的
    DEFAULT_LLM_* 系列作为兼容兜底) -> config.json -> 内置默认值。
    api_key 若仍是占位符则抛 ConfigError, 提示用户填写。
    """
    llm_config = (config or {}).get("llm", {}) or {}

    api_key = (
        os.environ.get("OPENAI_API_KEY")
        or os.environ.get("DEFAULT_LLM_API_KEY")
        or llm_config.get("api_key")
        or ""
    )
    base_url = (
        os.environ.get("LLM_BASE_URL")
        or os.environ.get("DEFAULT_LLM_BASE_URL")
        or llm_config.get("base_url")
        or DEFAULT_LLM_BASE_URL
    )
    model = (
        os.environ.get("LLM_MODEL")
        or os.environ.get("DEFAULT_LLM_MODEL_NAME")
        or llm_config.get("model")
        or DEFAULT_LLM_MODEL
    )

    if api_key.strip() in PLACEHOLDER_VALUES:
        raise ConfigError(
            "未找到有效的 LLM API Key。请设置环境变量 OPENAI_API_KEY, "
            f"或编辑 {LOCAL_CONFIG_PATH} (可从 config.example.json 复制) 填入 llm.api_key。"
        )

    base_url = _normalize_base_url(base_url)

    return {"api_key": api_key, "base_url": base_url, "model": model}


def _normalize_base_url(base_url: str) -> str:
    """
    某些环境里的 base_url(如兜底兼容的 DEFAULT_LLM_BASE_URL)是给"原始 HTTP
    调用"用的完整 chat/completions 端点; 而 openai SDK 的 base_url 需要是
    "根路径", SDK 自己会拼接 /chat/completions。这里做一次归一化, 避免
    出现 .../chat/completions/chat/completions 的双重拼接。
    """
    base_url = base_url.rstrip('/')
    for suffix in ('/chat/completions',):
        if base_url.endswith(suffix):
            return base_url[: -len(suffix)]
    return base_url


class LLMClient:
    """
    极简的 OpenAI 兼容 chat completions 客户端, 基于 `requests` 而非
    `openai` SDK(其底层 httpx 传输在部分内网/自建网关上会触发 502, 而
    `requests` 对同样的网关请求正常; 见 README 排查一节)。只依赖标准的
    `POST {base_url}/chat/completions` 协议, 兼容 DeepSeek / Kimi / 内网
    OpenAI 兼容网关等。
    """

    def __init__(self, api_key: str, base_url: str, model: str, timeout: int = 180):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.timeout = timeout

    def chat(self, messages: list, json_mode: bool = False, model: str = None) -> str:
        import requests

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {"model": model or self.model, "messages": messages}
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        response = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
        if json_mode and response.status_code >= 400:
            # 部分网关不支持 response_format 参数, 去掉后重试一次。
            payload.pop("response_format", None)
            response = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]


def get_openai_client(config: dict):
    """返回 (LLMClient 实例, model 名称), 供各脚本以统一方式发起 chat 请求。"""
    settings = get_llm_settings(config)
    client = LLMClient(api_key=settings["api_key"], base_url=settings["base_url"], model=settings["model"])
    return client, settings["model"]


def find_mineru_binary(config: dict = None) -> str:
    """
    探测顺序: PATH (mineru-kit/mineru/magic-pdf) -> config['mineru_bin'] -> 常见安装路径。
    找不到返回 None。
    """
    on_path = shutil.which("mineru-kit") or shutil.which("mineru") or shutil.which("magic-pdf")
    if on_path:
        return on_path

    configured = (config or {}).get("mineru_bin")
    if configured and Path(configured).exists():
        return configured

    for candidate in MINERU_BIN_CANDIDATES:
        if candidate and Path(candidate).exists():
            return candidate

    return None


def find_marker_binary(config: dict = None) -> str:
    """
    探测顺序: PATH (shutil.which) -> config['marker_bin'] -> 常见安装路径。
    找不到返回 None, 调用方需自行降级处理, 不应抛异常。
    """
    on_path = shutil.which("marker_single")
    if on_path:
        return on_path

    configured = (config or {}).get("marker_bin")
    if configured and Path(configured).exists():
        return configured

    for candidate in MARKER_BIN_CANDIDATES:
        if candidate and Path(candidate).exists():
            return candidate

    return None


def list_top_level_dirs(root: Path, exclude: set = None) -> list:
    root = Path(root)
    exclude = exclude or set()
    if not root.exists():
        return []
    dirs = []
    for item in sorted(os.listdir(root)):
        if item.startswith('.') or item in exclude:
            continue
        if os.path.isdir(root / item):
            dirs.append(item)
    return dirs


def get_general_categories(vault_path: Path) -> list:
    """普通网页/博客剪藏可选的分类(vault 顶层目录, 排除基础设施目录)。"""
    return list_top_level_dirs(vault_path, exclude=INFRA_DIR_BLOCKLIST)


def get_paper_categories(vault_path: Path, papers_subdir: str = "20_Papers") -> list:
    """论文深度解析可选的分类(20_Papers/ 下的子目录)。"""
    return list_top_level_dirs(Path(vault_path) / papers_subdir)


def slugify(text: str, max_words: int = 8) -> str:
    """把标题转成安全的英文小写 slug, 用作资产目录名 / 文件名基底。"""
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9\s-]", "", text).strip().lower()
    words = re.split(r"[\s_-]+", text)
    words = [w for w in words if w]
    slug = "_".join(words[:max_words])
    return slug or "untitled"


def sanitize_filename(text: str) -> str:
    """去掉文件名中不允许的字符, 用于保存 .md 文件。"""
    return re.sub(r'[\\/*?:"<>|]', "", text).strip()
