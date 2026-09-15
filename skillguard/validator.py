"""静态校验引擎：结构、引用完整性、安全模式扫描。

规则 ID 约定：
- SRC-*  ：结构 (structure)
- REF-*  ：引用完整性 (reference)
- SEC-*  ：安全模式 (security)
- DOC-*  ：文档规范 (documentation)
"""

from __future__ import annotations

import re
from pathlib import Path

from .models import CheckResult, Severity, SkillInfo

# ----------------------------------------------------------------------
# 安全模式：高风险的命令/模式
# ----------------------------------------------------------------------
DANGEROUS_PATTERNS: list[tuple[str, str, Severity]] = [
    (
        "SEC-001",
        r"\brm\s+(-[a-zA-Z]*f[a-zA-Z]*\s+)+|rm\s+-rf\s+[/~]|rm\s+--?recursive",
        Severity.ERROR,
    ),
    ("SEC-002", r"\bmkfs\b|\bdd\s+if=.*of=/dev/", Severity.ERROR),
    ("SEC-003", r"\bchmod\s+777\b", Severity.WARNING),
    ("SEC-004", r"\bcurl\s+[^|]*\|[^|]*sh\b|\bwget\s+[^|]*\|[^|]*sh\b", Severity.WARNING),
    ("SEC-005", r"['\"]?api[_-]?key['\"]?\s*[:=]\s*['\"][A-Za-z0-9_\-]{16,}['\"]", Severity.ERROR),
    ("SEC-006", r"token\s*=\s*['\"][A-Za-z0-9_\-]{20,}['\"]", Severity.WARNING),
    ("SEC-007", r"\bgit\s+push\s+--force\b", Severity.WARNING),
    ("SEC-008", r"\beval\s+['\"]?\$?\(", Severity.ERROR),
    ("SEC-009", r"\bsudo\b", Severity.INFO),
    # 云平台凭据（AWS/Azure/GCP/阿里云）
    ("SEC-010", r"AKIA[0-9A-Z]{16}", Severity.ERROR),  # AWS Access Key ID
    ("SEC-011", r"(aws_secret_access_key|AZURE_CLIENT_SECRET|GOOGLE_API_KEY|ALIBABA_CLOUD_ACCESS_KEY_SECRET)\s*[:=]\s*['\"][^'\"]{16,}['\"]", Severity.ERROR),
    # 路径遍历
    ("SEC-012", r"\.\./\.\./\.\./", Severity.WARNING),
    # 下载并执行（非管道形式）
    ("SEC-013", r"\b(?:wget|curl)\s+.*\s+-o\s+\S+\.(?:sh|py|exe|bat)\b", Severity.WARNING),
    # 环境变量导出密钥（疑似密钥经 env 传递）
    ("SEC-014", r"\bexport\s+(?:API_KEY|SECRET|TOKEN)\s*=", Severity.INFO),
    # base64 编码的疑似凭据（常见混淆手段）
    ("SEC-015", r"base64\s+['\"][A-Za-z0-9+/=]{32,}['\"]", Severity.INFO),
    # GitHub Personal Access Token
    ("SEC-016", r"gh[pousr]_[A-Za-z0-9]{36,}", Severity.ERROR),
    # 私钥泄露（RSA/ED25519/OpenSSH 私钥内容）
    ("SEC-017", r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----", Severity.ERROR),
    # 危险重定向（>/dev/null 忽略错误继续执行）
    ("SEC-018", r"(?:2>&1\s*>\s*/dev/null|>\s*/dev/null\s*2>&1)", Severity.INFO),
    # NPM 供应链风险：直接执行 registry 脚本
    ("SEC-019", r"\bnpx\s+[A-Za-z0-9_\-]+\s+--yes\b|\bnpm\s+(?:i|install)\s+-g\b", Severity.WARNING),
    # 危险权限提升（su/doas 替代 sudo）
    ("SEC-020", r"\b(?:su\s+-|doas\s+)", Severity.INFO),
    # Redis/DB 高危命令（flushdb/flushall/drop database）
    ("SEC-021", r"\b(?:FLUSHALL|FLUSHDB|DROP\s+DATABASE)\b", Severity.ERROR),
    # 危险 curl 选项（-k 跳过证书校验 / --insecure）
    ("SEC-022", r"\bcurl\s+(?:-k\b|--insecure\b)|(?:-k\b|--insecure\b)\s+(?:https?://)", Severity.WARNING),
    # 从远程 URL 导入模块/执行（Python imp/importlib + url）
    ("SEC-023", r"\b(?:imp|importlib)\.[a-z_]+\(['\"]?https?://", Severity.WARNING),
    # 危险 git 操作（reset --hard / checkout . 丢弃未提交修改）
    ("SEC-024", r"\bgit\s+(?:reset\s+--hard|checkout\s+\.)\b", Severity.WARNING),
    # 上传用户数据到公开服务（curl/wget POST/PUT 带文件）
    ("SEC-025", r"\b(?:curl|wget)\s+.*?-(?:X\s*)?(?:POST|PUT)\s+.*?(?:@[\w./-]+|-F\s)", Severity.INFO),
    ("SEC-026", r"\b(?:system|exec|popen)\(\s*['\"]\$?\{\w+\}", Severity.WARNING),
    # cron 远程下载执行
    ("SEC-027", r"\bcron\b.*(?:curl|wget)", Severity.WARNING),
    # 混淆数据解码
    ("SEC-028", r"(?:echo|printf)\s+['\"][0-9a-fA-F]{40,}['\"]\s*\|\s*(?:xxd|hexdump)", Severity.INFO),
    # sed 就地破坏性编辑
    ("SEC-029", r"\bsed\s+-i\b.*\bd\b|\bsed\s+-i\b.*\bc\b", Severity.INFO),
    # ln 强制符号链接覆盖
    ("SEC-030", r"\bln\s+-sf\b|\bln\s+--symbolic\s+--force\b", Severity.WARNING),
    # 解压 zip-slip 风险
    ("SEC-031", r"\btar\s+-x.*\.tar.*\.gz", Severity.INFO),
    # SSH 禁用主机密钥校验
    ("SEC-032", r"StrictHostKeyChecking\s*(?:=|\s+)no|UserKnownHostsFile\s*/dev/null", Severity.WARNING),
    # Docker 特权模式/根挂载
    ("SEC-033", r"docker\s+run.*--privileged|docker\s+run.*-v\s+/:", Severity.WARNING),
    # pickle/yaml 不安全反序列化
    ("SEC-034", r"pickle\.loads?\(|yaml\.load\(.*Loader=[^)]*UnsafeLoader", Severity.WARNING),
    # Bash IFS 劫持
    ("SEC-035", r"\bIFS\s*=|\bunset\s+IFS\b", Severity.INFO),
    # 递归 chown/chmod 777（权限滥用）
    ("SEC-036", r"\bchown\s+-R\b|\bchmod\s+-R\s+777\b", Severity.WARNING),
    # systemd 单元远程下载
    ("SEC-037", r"\bcurl.*/etc/systemd/system|\bwget.*/etc/systemd/system", Severity.WARNING),
    # find -delete 批量删除
    ("SEC-038", r"\bfind\s+.*\s+-delete\b", Severity.WARNING),
    # nohup 后台隐藏执行
    ("SEC-039", r"\bnohup\s+.*&\s*$", Severity.INFO),
    # Shell RC 注入持久化
    ("SEC-040", r"echo\s+.*>>\s*(?:~?/)?\.(?:bashrc|zshrc|profile)", Severity.WARNING),
    # git 子模块远程代码
    ("SEC-041", r"\bsubmodule\s+add\b", Severity.INFO),
    # setuid/setgid 权限位
    ("SEC-042", r"\bchmod\s+(?:[0-7]?[42][0-7]{3})\b", Severity.WARNING),
    # awk 内命令执行
    ("SEC-043", r"\bawk\s+.*system\(", Severity.WARNING),
    # tee 写系统文件
    ("SEC-044", r"\btee\s+/etc/|\btee\s+/usr/", Severity.WARNING),
    # ln 覆盖系统库
    ("SEC-045", r"\bln\s+.*lib(?:64)?\b", Severity.INFO),
    # source/点执行外部脚本
    ("SEC-046", r"\bsource\s+[^ ]+\.sh|\b\.\s+[^ ]+\.sh", Severity.INFO),
    # rsync 覆盖删除
    ("SEC-047", r"\brsync\s+.*--delete\b", Severity.WARNING),
    # mktemp 固定路径（不可预测）
    ("SEC-048", r"\bmktemp\s+/tmp/[A-Za-z0-9_]+\b", Severity.INFO),
    # git config 篡改
    ("SEC-049", r"\bgit\s+config\s+(?:user|core|alias)\.", Severity.INFO),
    # hosts 文件修改
    ("SEC-050", r">>\s*/etc/hosts|echo\s+.*\s*>>\s*/etc/hosts", Severity.WARNING),
    # curl 下载到 /tmp 后执行
    ("SEC-051", r"(?:curl|wget)\s+.*\s+-o\s+/tmp/.*\.(?:sh|py)", Severity.WARNING),
    # pip install 从 URL
    ("SEC-052", r"pip\s+install\s+(?:https?|git)\S+", Severity.WARNING),
    # PATH 环境变量覆盖
    ("SEC-053", r"\bPATH=\S*:\S*\b|\bexport\s+PATH=", Severity.INFO),
    # curl POST 数据外传
    ("SEC-054", r"\b(?:curl|wget)\b[^\n]*(?:-d|--data)[^\n]*(?:https?://)", Severity.INFO),
    # openssl 弱加密
    ("SEC-055", r"openssl\s+.*-(?:des|rc4|md5)\d*\b", Severity.WARNING),
    # nc/ncat 端口监听（后门）
    ("SEC-056", r"\bnc\s+-l|\bncat\s+-l", Severity.WARNING),
    # socat 端口转发
    ("SEC-057", r"\bsocat\s+TCP-LISTEN", Severity.WARNING),
    # base64 解码写文件
    ("SEC-058", r"base64\s+-d.*\s*>\s*\.?/?[A-Za-z0-9_]+", Severity.INFO),
    # dd 覆盖分区
    ("SEC-059", r"\bdd\s+if=\S+\s+of=/dev/sd", Severity.ERROR),
    # 历史命令清除（掩盖操作）
    ("SEC-060", r"history\s+-c|unset\s+HISTFILE", Severity.INFO),
    # umask 放宽权限
    ("SEC-061", r"\bumask\s+(?:0|0[0-7][0-7])\b", Severity.INFO),
    # FTP 明文凭据
    ("SEC-062", r"\bftp\s+.*-p\b|\buser\s+[\w.-]+\s+[\w.-]+\s*\n.*\bftp", Severity.INFO),
    # SCP 从不可信主机
    ("SEC-063", r"\bscp\s+.*@(?:[\w.-]+:)", Severity.INFO),
    # tee 追加系统文件
    ("SEC-064", r"\btee\s+-a\s+/etc/", Severity.WARNING),
    # rmdir 根目录
    ("SEC-065", r"\brmdir\s+/", Severity.WARNING),
]

# 引用完整性：常见的本地文件/脚本引用模式
_REFERENCE_PATTERNS = [
    re.compile(r"`?\.?/?(?:scripts|bin|tools)/[A-Za-z0-9_\-./]+`?"),
    re.compile(r"`?[A-Za-z0-9_\-]+\.(?:sh|py|js|ts|rb|pl)`?"),
]

_ENTRY_NAMES = ("SKILL.md", "skill.md")


def _find_entry(skill_dir: Path) -> Path | None:
    """独立发现入口文件（不依赖 SkillInfo.entrypoint，增强健壮性）。"""
    for name in _ENTRY_NAMES:
        p = skill_dir / name
        if p.is_file():
            return p
    return None


def run_static_checks(skill_dir: Path, skill: SkillInfo, skip_safety: bool = False) -> list[CheckResult]:
    """执行全部静态检查（内置 + 已注册的自定义规则），返回按严重级排序的结果。"""
    results: list[CheckResult] = []
    results.extend(_structure_checks(skill_dir, skill))
    results.extend(_reference_checks(skill_dir, skill))
    if not skip_safety:
        results.extend(_safety_checks(skill_dir))
    # 自定义规则（插件系统）
    from .rules import registry

    results.extend(registry.run_custom(skill_dir, skill))
    results.sort(key=lambda r: (r.severity.value != Severity.ERROR.value, r.severity.value))
    return results


# ----------------------------------------------------------------------
# 结构检查
# ----------------------------------------------------------------------
def _structure_checks(skill_dir: Path, skill: SkillInfo) -> list[CheckResult]:
    results: list[CheckResult] = []

    # SRC-001：入口文件存在
    entry = _find_entry(skill_dir)
    if entry is None:
        results.append(
            CheckResult("SRC-001", Severity.ERROR, "缺少 SKILL.md 入口文件", file=skill_dir.name)
        )
        return results

    # SRC-002：有名称
    if not skill.name:
        results.append(CheckResult("SRC-002", Severity.ERROR, "SKILL.md 缺少 name 元数据", file=entry.name))

    # SRC-003：有描述
    if not skill.description:
        results.append(CheckResult("SRC-003", Severity.WARNING, "SKILL.md 缺少 description（AI 无法理解用途）", file=entry.name))

    # SRC-004：脚本目录存在性
    scripts_dir = skill_dir / "scripts"
    if scripts_dir.is_dir():
        non_script = [p.name for p in scripts_dir.iterdir() if p.is_file() and p.suffix.lower() not in {
            ".sh", ".py", ".js", ".ts", ".mjs", ".cjs", ".rb", ".pl", ".md", ".txt", ".json", ".yaml", ".yml",
        }]
        if non_script:
            results.append(
                CheckResult(
                    "SRC-004",
                    Severity.INFO,
                    f"scripts/ 中存在非常规文件: {', '.join(non_script[:5])}",
                    file="scripts",
                )
            )

    # SRC-005：入口文件大小（过大说明不可维护）
    size = entry.stat().st_size if entry.is_file() else 0
    if size > 40_000:
        results.append(
            CheckResult("SRC-005", Severity.WARNING, f"SKILL.md 过大（{size} 字节），建议拆分为参考文档", file=entry.name)
        )
    elif size == 0:
        results.append(CheckResult("SRC-005", Severity.ERROR, "SKILL.md 为空文件", file=entry.name))

    return results


# ----------------------------------------------------------------------
# 引用完整性
# ----------------------------------------------------------------------
def _reference_checks(skill_dir: Path, skill: SkillInfo) -> list[CheckResult]:
    results: list[CheckResult] = []
    entry = _find_entry(skill_dir)
    if entry is None:
        return results

    text = entry.read_text(encoding="utf-8", errors="replace")
    existing_files = {p.name for p in skill_dir.rglob("*") if p.is_file()}

    for m in _REFERENCE_PATTERNS[0].finditer(text):
        raw = m.group(0).strip("`").lstrip("./")
        if not raw:
            continue
        ref_name = raw.split("/")[-1]
        if ref_name and ref_name not in existing_files:
            results.append(
                CheckResult(
                    "REF-001",
                    Severity.WARNING,
                    f"引用的本地脚本/文件可能不存在: {raw}",
                    file=entry.name,
                )
            )

    # REF-002：引用了脚本但脚本目录为空
    scripts_dir = skill_dir / "scripts"
    if "scripts" in text and scripts_dir.is_dir() and not any(scripts_dir.iterdir()):
        results.append(
            CheckResult("REF-002", Severity.WARNING, "SKILL.md 引用了 scripts/ 但目录为空", file=entry.name)
        )

    return results


# ----------------------------------------------------------------------
# 安全扫描
# ----------------------------------------------------------------------
def _safety_checks(skill_dir: Path) -> list[CheckResult]:
    results: list[CheckResult] = []
    text_files = [
        p
        for p in skill_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in {".md", ".sh", ".py", ".js", ".ts", ".txt", ".yaml", ".yml", ".json"}
    ]
    for path in text_files:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for rule_id, pattern, severity in DANGEROUS_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                results.append(
                    CheckResult(rule_id, severity, f"检测到危险模式: {pattern[:60]}", file=str(path.relative_to(skill_dir)))
                )
    return results
