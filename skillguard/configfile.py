"""配置文件加载：支持 skillguard.yml / skillguard.yaml / skillguard.toml。

配置文件用于团队统一质量规则与阈值，可放置于：
1. `--config` 显式指定路径
2. 当前目录自动发现（skillguard.yml → skillguard.yaml → skillguard.toml）
3. Skill 目录内（.skillguard.yml）

示例 skillguard.yml：

    threshold: 75
    test_timeout: 120
    skip_safety: false
    rules:
      - SEC-001
      - SEC-005
    report_format: markdown
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import Config

CONFIG_FILENAMES = ("skillguard.yml", "skillguard.yaml", "skillguard.toml", ".skillguard.yml")


def _load_yaml(path: Path) -> dict[str, Any]:
    import yaml

    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        # 值域错误而非类型错误：这是配置内容问题，用 ValueError 语义更清晰
        raise ValueError(f"配置文件 {path} 顶层必须是映射（键值对）")  # noqa: TRY004
    return data


def _load_toml(path: Path) -> dict[str, Any]:
    try:
        import tomllib  # Python 3.11+
    except ImportError:  # pragma: no cover - Python 3.10
        try:
            import tomli as tomllib
        except ImportError as exc:  # pragma: no cover
            raise ValueError("加载 TOML 配置需要 tomli（Python 3.11 以下）: pip install tomli") from exc
    with path.open("rb") as f:
        data = tomllib.load(f)
    if not isinstance(data, dict):
        # 同上：值域错误
        raise ValueError(f"配置文件 {path} 顶层必须是表（键值对）")  # noqa: TRY004
    return data


def load_config_file(path: Path) -> dict[str, Any]:
    """加载单个配置文件，返回原始 dict。"""
    if not path.is_file():
        raise ValueError(f"配置文件不存在: {path}")
    suffix = path.suffix.lower()
    if suffix == ".toml":
        return _load_toml(path)
    if suffix in (".yml", ".yaml"):
        return _load_yaml(path)
    raise ValueError(f"不支持的配置文件格式: {suffix}（支持 .yml/.yaml/.toml）")


def find_config_file(start: Path | None = None) -> Path | None:
    """在当前目录（含父目录链）中自动发现配置文件。"""
    base = Path(start or Path.cwd()).resolve()
    for candidate in (base, *base.parents):
        for name in CONFIG_FILENAMES:
            p = candidate / name
            if p.is_file():
                return p
    return None


def _normalize_rules(raw: Any) -> tuple[str, ...]:
    if raw is None:
        return ()
    if isinstance(raw, list):
        return tuple(str(r) for r in raw if str(r).strip())
    if isinstance(raw, str):
        return tuple(r.strip() for r in raw.split(",") if r.strip())
    raise ValueError("rules 必须是字符串列表或逗号分隔字符串")


def config_from_dict(data: dict[str, Any], defaults: Config | None = None) -> Config:
    """从配置文件 dict 构建 Config（未指定字段用默认值）。"""
    base = defaults or Config()
    kwargs: dict[str, Any] = {}
    field_map = {
        "skill_dir": "skill_dir",
        "test_timeout": "test_timeout",
        "skip_safety": "skip_safety",
        "report_format": "report_format",
        "threshold": "threshold",
        "report_output": "report_output",
    }
    for key, attr in field_map.items():
        if key in data and data[key] is not None:
            kwargs[attr] = data[key]
    if "rules" in data:
        kwargs["rules"] = _normalize_rules(data["rules"])
    if "run_tests" in data:
        kwargs["run_tests"] = bool(data["run_tests"])
    return base.with_overrides(**kwargs)


def build_config(skill_dir: str = ".", config_path: str | None = None) -> Config:
    """构建 Config：合并配置文件与命令行参数。

    优先级：显式 --config > 自动发现配置文件 > 命令行默认值。
    """
    base = Config(skill_dir=skill_dir)

    # 1. 显式指定配置文件
    if config_path:
        return config_from_dict(load_config_file(Path(config_path).resolve()), base)

    # 2. 自动发现（当前目录 → Skill 目录）
    cwd = Path.cwd()
    discovered = find_config_file(cwd)
    if discovered is None:
        discovered = find_config_file(Path(skill_dir))
    if discovered is not None:
        return config_from_dict(load_config_file(discovered), base)

    return base


def config_to_dict(config: Config) -> dict[str, Any]:
    """将 Config 序列化为配置文件 dict（用于生成模板）。"""
    return {
        "skill_dir": config.skill_dir,
        "threshold": config.threshold,
        "test_timeout": config.test_timeout,
        "skip_safety": config.skip_safety,
        "run_tests": config.run_tests,
        "report_format": config.report_format,
        "rules": list(config.rules),
    }
