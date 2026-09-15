# SkillGuard 质量规则参考

> 全部规则按前缀分类：`SRC`（结构）、`REF`（引用）、`SEC`（安全）、`DOC`（文档）。
> 严重级：🔴 error（必须修复）· 🟡 warning（建议修复）· 🔵 info（提示）

## 结构规则（SRC）

| 规则 | 严重级 | 说明 |
|------|--------|------|
| `SRC-001` | 🔴 | 缺少 SKILL.md / skill.md 入口文件 |
| `SRC-002` | 🔴 | SKILL.md 缺少 name 元数据 |
| `SRC-003` | 🟡 | 缺少 description（AI 无法理解用途） |
| `SRC-004` | 🔵 | scripts/ 存在非常规文件类型 |
| `SRC-005` | 🟡/🔴 | 入口文件过大（>40KB，建议拆分）或为空文件 |

## 引用完整性（REF）

| 规则 | 严重级 | 说明 |
|------|--------|------|
| `REF-001` | 🟡 | SKILL.md 引用的本地脚本/文件不存在 |
| `REF-002` | 🟡 | 引用了 scripts/ 但目录为空 |

## 安全规则（SEC）

| 规则 | 严重级 | 匹配模式 | 说明 |
|------|--------|----------|------|
| `SEC-001` | 🔴 | `rm -f`、`rm -rf /~`、`rm --recursive` | 破坏性删除 |
| `SEC-002` | 🔴 | `mkfs`、`dd if=...of=/dev/` | 磁盘级操作 |
| `SEC-003` | 🟡 | `chmod 777` | 权限过宽 |
| `SEC-004` | 🟡 | `curl\|sh`、`wget\|sh` | 远程管道执行 |
| `SEC-005` | 🔴 | `api_key` 后跟 16+ 位字符串 | 硬编码 API Key |
| `SEC-006` | 🟡 | `token` 后跟 20+ 位字符串 | 硬编码 Token |
| `SEC-007` | 🟡 | `git push --force` | 强制推送风险 |
| `SEC-008` | 🔴 | `eval $(...)` | 动态执行 |
| `SEC-009` | 🔵 | `sudo` | 权限提升操作 |
| `SEC-010` | 🔴 | `AKIA` + 16 位大写字母数字 | AWS Access Key ID |
| `SEC-011` | 🔴 | `aws_secret_access_key` / `AZURE_CLIENT_SECRET` / `GOOGLE_API_KEY` / 阿里云密钥 | 云平台凭据泄露 |
| `SEC-012` | 🟡 | `../../../` | 路径遍历 |
| `SEC-013` | 🟡 | `curl/wget -o *.sh/*.py/*.exe/*.bat` | 下载可执行文件 |
| `SEC-014` | 🔵 | `export API_KEY/SECRET/TOKEN=` | 环境变量导出密钥 |
| `SEC-015` | 🔵 | base64 编码 32+ 位字符串 | 疑似混淆凭据 |
| `SEC-016` | 🔴 | `ghp_`/`gho_` 等 GitHub Token | GitHub 个人访问令牌泄露 |
| `SEC-017` | 🔴 | `-----BEGIN ... PRIVATE KEY-----` | 私钥泄露（RSA/EC/OpenSSH） |
| `SEC-018` | 🔵 | `>/dev/null 2>&1` | 忽略错误继续执行 |
| `SEC-019` | 🟡 | `npx pkg --yes` / `npm i -g` | NPM 供应链执行风险 |
| `SEC-020` | 🔵 | `su -` / `doas` | 其他权限提升方式 |
| `SEC-021` | 🔴 | `FLUSHALL` / `FLUSHDB` / `DROP DATABASE` | 数据库高危命令 |
| `SEC-022` | 🟡 | `curl -k` / `--insecure` | 跳过证书校验 |
| `SEC-023` | 🟡 | `importlib.import_module(url)` | 远程模块导入 |
| `SEC-024` | 🟡 | `git reset --hard` / `checkout .` | 丢弃未提交修改 |
| `SEC-025` | 🔵 | `curl -F file=@path` POST/PUT | 上传文件到远程服务 |

## 评分权重

| 维度 | 权重 | 规则映射 |
|------|------|----------|
| 结构完整性 structure | 25% | SRC |
| 文档清晰度 documentation | 20% | DOC |
| 安全性 safety | 30% | SEC |
| 可维护性 maintainability | 15% | REF + CUS（自定义） + 脚本加分 |
| 实用性 usability | 10% | 缺失项扣分 + 测试加分 |

## 自定义规则（插件）

支持注册团队自定义检查规则，详见 [API 文档 - 插件系统](api.md#插件系统自定义规则)。

```python
from skillguard.rules import registry
from skillguard.models import CheckResult, Severity

registry.register("CUS", lambda d, s: [CheckResult("CUS-001", Severity.WARNING, "自定义")])
```

自定义前缀（如 `CUS`）的规则会并入**可维护性**维度评分，并与内置规则一同输出报告。

## 门禁判定

```
passed = (无 ERROR 检查) 且 (无失败测试) 且 (综合评分 ≥ threshold)
```

默认 `threshold = 60`，可通过 `--threshold` 调整。
| `SEC-026` | 🟡 | `system("${VAR}")` | 环境变量命令执行 |
| `SEC-027` | 🟡 | `cron` + `curl/wget` | 定时远程下载执行 |
| `SEC-028` | 🔵 | `echo hex | xxd` | 混淆数据解码 |
| `SEC-029` | 🔵 | `sed -i d/c` | 就地破坏性编辑 |
| `SEC-030` | 🟡 | `ln -sf` | 强制符号链接覆盖 |
| `SEC-031` | 🔵 | `tar -xzf` | 解压 zip-slip |
| `SEC-032` | 🟡 | `StrictHostKeyChecking no` | SSH 禁用主机校验 |
| `SEC-033` | 🟡 | `docker --privileged` | 特权容器 |
| `SEC-034` | 🟡 | `pickle.loads` | 不安全反序列化 |
| `SEC-035` | 🔵 | `IFS=` | Bash IFS 劫持 |
| `SEC-036` | 🟡 | `chown -R` / `chmod -R 777` | 递归权限滥用 |
| `SEC-037` | 🟡 | `curl → /etc/systemd/system` | systemd 单元下载 |
| `SEC-038` | 🟡 | `find -delete` | 批量删除 |
| `SEC-039` | 🔵 | `nohup ... &` | 后台隐藏执行 |
| `SEC-040` | 🟡 | `>> ~/.bashrc` | Shell RC 注入持久化 |
| `SEC-041` | 🔵 | `git submodule add` | 子模块远程代码 |
| `SEC-042` | 🟡 | `chmod 4xxx/2xxx` | setuid/setgid 权限位 |
| `SEC-043` | 🟡 | `awk system()` | awk 内命令执行 |
| `SEC-044` | 🟡 | `tee /etc/` | 写系统文件 |
| `SEC-045` | 🔵 | `ln lib` | 覆盖系统库 |
