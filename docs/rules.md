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
| `SEC-046` | 🔵 | `source ./x.sh` | 点执行外部脚本 |
| `SEC-047` | 🟡 | `rsync --delete` | 覆盖删除 |
| `SEC-048` | 🔵 | `mktemp /tmp/fixed` | 固定临时路径 |
| `SEC-049` | 🔵 | `git config user/core/alias` | git 配置篡改 |
| `SEC-050` | 🟡 | `>> /etc/hosts` | hosts 文件修改 |
| `SEC-051` | 🟡 | `curl -o /tmp/x.sh` | 下载到 /tmp 后执行 |
| `SEC-052` | 🟡 | `pip install git+https://` | URL 安装依赖 |
| `SEC-053` | 🔵 | `export PATH=...` | PATH 环境变量覆盖 |
| `SEC-054` | 🔵 | `curl -d ... http://` | 数据外传 |
| `SEC-055` | 🟡 | `openssl -des/rc4/md5` | 弱加密 |
| `SEC-056` | 🟡 | `nc -l` / `ncat -l` | 端口监听后门 |
| `SEC-057` | 🟡 | `socat TCP-LISTEN` | 端口转发 |
| `SEC-058` | 🔵 | `base64 -d > file` | 解码写文件 |
| `SEC-059` | 🔴 | `dd of=/dev/sd` | 覆盖分区 |
| `SEC-060` | 🔵 | `history -c` | 清除命令历史 |
| `SEC-061` | 🔵 | `umask 000` | 权限放宽 |
| `SEC-062` | 🔵 | `ftp -p` | 明文凭据 |
| `SEC-063` | 🔵 | `scp user@host:` | 不可信主机 |
| `SEC-064` | 🟡 | `tee -a /etc/` | 追加系统文件 |
| `SEC-065` | 🟡 | `rmdir /` | 删除根目录 |
| `SEC-066` | 🔵 | `tmux new -s` | 隐藏会话 |
| `SEC-067` | 🔵 | `awk > /etc/` | 输出重定向系统文件 |
| `SEC-068` | 🟡 | `curl ... | bash` | 管道执行 |
| `SEC-069` | 🟡 | `git clone && cd && run` | 克隆后立即执行 |
| `SEC-070` | 🔵 | `make install` | 源码编译安装 |
| `SEC-071` | 🔵 | `telnet` | 明文连接 |
| `SEC-072` | 🟡 | `curl -o ~/.bashrc` | RC 文件远程覆盖 |
| `SEC-073` | 🔵 | `dbus-send` | 系统调用 |
| `SEC-074` | 🟡 | `mount ... /etc` | 覆盖系统目录 |
| `SEC-075` | 🔵 | `ulimit -c 0` | 移除限制 |
| `SEC-076` | 🟡 | `gdb -p` | 附加进程 |
| `SEC-077` | 🔵 | `strace -p` | 进程跟踪 |
| `SEC-078` | 🔵 | `lsof /etc/shadow` | 敏感文件查看 |
| `SEC-079` | 🟡 | `hexdump /dev/mem` | 内存转储 |
| `SEC-080` | 🟡 | `iptables -F` | 清空防火墙 |
| `SEC-086` | 🔵 | `encfs --reverse` | 加密绕过 |
| `SEC-087` | 🔵 | `socat TCP:host:port` | 反连 |
| `SEC-088` | 🔵 | `tcpdump -i -w` | 抓包 |
| `SEC-089` | 🟡 | `scapy send()` | 构造包 |
| `SEC-090` | 🔵 | `hostnamectl set-hostname` | 主机冒充 |
| `SEC-091` | 🟡 | `curl -k ... | bash` | 忽略证书管道执行 |
| `SEC-092` | 🟡 | `eval(input())` | Python 动态执行 |
| `SEC-093` | 🟡 | `ssh -R` | SSH 反向转发 |
| `SEC-094` | 🟡 | `find | xargs rm` | 批量删除 |
| `SEC-095` | 🔵 | `tar -C /` | 绝对路径覆盖 |
| `SEC-096` | 🔴 | `curl | sudo sh` | 高危管道执行 |
| `SEC-097` | 🟡 | `pickle.loads(exec)` | 反序列化执行 |
| `SEC-098` | 🔵 | `git submodule --recursive` | 递归子模块 |
| `SEC-099` | 🟡 | `chmod u+s` | suid 后门 |
| `SEC-100` | 🟡 | `shutdown/reboot/halt` | 系统关机重启 |
| `SEC-101` | 🔵 | `curl -F file=@` | 文件上传外传 |
| `SEC-102` | 🟡 | `wget ... | bash` | 管道执行 |
| `SEC-103` | 🔵 | `ssh-keygen -f` | 生成密钥后门 |
| `SEC-104` | 🔴 | `nc -e` | 远程 shell |
| `SEC-105` | 🟡 | `/dev/tcp/` | TCP 后门 |
| `SEC-106` | 🔵 | `cryptsetup luksFormat` | 加密覆盖 |
| `SEC-107` | 🔵 | `zerotier-cli join` | 远程组网 |
| `SEC-108` | 🔵 | `ip link set address` | MAC 伪造 |
| `SEC-109` | 🔴 | `sshpass -p` | 明文密码 |
| `SEC-110` | 🟡 | `expect send password` | 密码脚本 |
| `SEC-111` | 🟡 | `ProxyCommand bash` | SSH 代理命令注入 |
| `SEC-112` | 🟡 | `LD_PRELOAD=` | 库劫持 |
| `SEC-113` | 🔵 | `PYTHONPATH=` | Python 路径劫持 |
| `SEC-114` | 🔵 | `NODE_OPTIONS=` | Node 注入 |
| `SEC-115` | 🔵 | `JAVA_TOOL_OPTIONS=` | Java 注入 |
| `SEC-116` | 🟡 | `LD_LIBRARY_PATH=` | 库路径劫持 |
| `SEC-117` | 🔵 | `GODEBUG/GOGC=` | Go 运行时注入 |
| `SEC-118` | 🔵 | `py_compile.compile()` | 字节码注入 |
| `SEC-119` | 🟡 | `require($env/process.env)` | 动态加载 |
| `SEC-120` | 🟡 | `yaml.load FullLoader` | 不安全反序列化 |
| `SEC-121` | 🔵 | `openssl pkcs12 -export` | 私钥导出 |
| `SEC-122` | 🟡 | `certutil -urlcache` | 下载执行 |
| `SEC-123` | 🟡 | `powershell -enc` / `IEX()` | 编码执行 |
| `SEC-124` | 🟡 | `bitsadmin /transfer` | 传输工具 |
| `SEC-125` | 🔴 | `mshta http/javascript` | 脚本执行 |
| `SEC-126` | 🟡 | `curl -o /etc/init.d/` | 下载到启动目录 |
| `SEC-127` | 🟡 | `apt --no-check-certificate` | 绕过证书校验 |
| `SEC-128` | 🔵 | `gradle -e/--init-script` | 动态执行 |
| `SEC-129` | 🔵 | `mvn -Dmaven.repo.remote` | 远程仓库 |
| `SEC-130` | 🟡 | `npm exec` | 脚本执行 |
| `SEC-131` | 🟡 | `docker run --pid/net=host` | 容器逃逸 |
| `SEC-132` | 🟡 | `kubectl --as=system:admin` | 权限提升 |
| `SEC-133` | 🔵 | `terraform destroy` | 基础设施破坏 |
| `SEC-134` | 🔵 | `ansible --skip-tags=security` | 跳过安全 |
| `SEC-135` | 🟡 | `systemctl stop firewalld` | 禁用防火墙 |
| `SEC-136` | 🔵 | `docker load -i` | 镜像加载 |
| `SEC-137` | 🟡 | `docker exec chroot` | 容器逃逸 |
| `SEC-138` | 🔵 | `ctr images import` | containerd 导入 |
| `SEC-139` | 🔵 | `kubeadm reset` | 集群重置 |
| `SEC-140` | 🔵 | `helm template --set $(...)` | 模板命令注入 |
| `SEC-141` | 🔵 | `serverless deploy --stage=prod` | 部署后门 |
| `SEC-142` | 🔵 | `cloudformation --parameter-overrides` | 参数注入 |
| `SEC-143` | 🟡 | `aws ... --minimum-password-length 0-5` | 弱密码策略 |
| `SEC-144` | 🟡 | `gcloud firewall-rules --allow all` | 防火墙全开 |
| `SEC-145` | 🔵 | `az storage blob upload --auth-mode key` | 密钥上传 |
| `SEC-146` | 🟡 | `etcdctl get /registry/secrets` | 密钥访问 |
| `SEC-147` | 🟡 | `vault seal disable` | 密封禁用 |
| `SEC-148` | 🔵 | `consul kv put --token` | 配置篡改 |
| `SEC-149` | 🟡 | `zkCli deleteall /` | 数据删除 |
| `SEC-150` | 🟡 | `redis-cli CONFIG SET dir` | 配置修改 |
| `SEC-151` | 🔴 | `mongo db.dropDatabase()` | 删除数据库 |
| `SEC-152` | 🔴 | `psql DROP TABLE` | 删除表 |
| `SEC-153` | 🔴 | `mysql DROP DATABASE` | 删除库 |
| `SEC-154` | 🟡 | `sqlite3 DELETE FROM` | 清空数据 |
| `SEC-155` | 🟡 | `curl -X DELETE _all` | 删除索引 |
