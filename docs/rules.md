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
| `SEC-156` | 🟡 | `hive DROP TABLE` | 删除表 |
| `SEC-157` | 🔴 | `cqlsh DROP KEYSPACE` | 删除键空间 |
| `SEC-158` | 🟡 | `neo4j MATCH DELETE` | 清空图库 |
| `SEC-159` | 🟡 | `influx delete --measurement` | 删除测量 |
| `SEC-160` | 🟡 | `clickhouse DROP TABLE` | 删除表 |
| `SEC-161` | 🟡 | `kafka-topics --delete` | 删除主题 |
| `SEC-162` | 🟡 | `rabbitmqctl purge_queue` | 清空队列 |
| `SEC-163` | 🟡 | `curl -X DELETE /index` | 删除索引 |
| `SEC-164` | 🟡 | `solr delete -c` | 删除核心 |
| `SEC-165` | 🟡 | `ksql DROP STREAM` | 删除流 |
| `SEC-166` | 🔵 | `grafana-cli datasource` | 数据源篡改 |
| `SEC-167` | 🔵 | `promtool --enable-feature` | 配置注入 |
| `SEC-168` | 🟡 | `curl -X DELETE /loki` | 删除日志 |
| `SEC-169` | 🔵 | `curl -X DELETE /jaeger` | 删除追踪 |
| `SEC-170` | 🟡 | `curl -X DELETE /kibana` | 删除索引模式 |
| `SEC-171` | 🟡 | `consul services deregister` | 服务注销 |
| `SEC-172` | 🟡 | `etcdctl member remove` | 成员移除 |
| `SEC-173` | 🔵 | `nomad job stop` | 作业停止 |
| `SEC-174` | 🟡 | `vault delete secret` | 密钥删除 |
| `SEC-175` | 🟡 | `kcadm delete realms` | 领域删除 |
| `SEC-176` | 🟡 | `oc delete cluster` | OpenShift 集群删除 |
| `SEC-177` | 🟡 | `rancher clusters rm` | Rancher 集群删除 |
| `SEC-178` | 🟡 | `aws eks delete-cluster` | EKS 集群删除 |
| `SEC-179` | 🟡 | `gcloud clusters delete` | GKE 集群删除 |
| `SEC-180` | 🟡 | `az aks delete` | AKS 集群删除 |
| `SEC-181` | 🟡 | `flyway undo` | 迁移回滚 |
| `SEC-182` | 🟡 | `liquibase rollback` | 迁移回滚 |
| `SEC-183` | 🟡 | `alembic downgrade` | 迁移降级 |
| `SEC-184` | 🟡 | `migrate zero` | 迁移重置 |
| `SEC-185` | 🟡 | `prisma migrate reset` | 迁移重置 |
| `SEC-186` | 🟡 | `sequelize sync --force` | 强制同步 |
| `SEC-187` | 🔵 | `typeorm schema:sync` | 模式同步 |
| `SEC-188` | 🔵 | `knex migrate:rollback` | 迁移回滚 |
| `SEC-189` | 🟡 | `drizzle-kit push --force` | 强制推送 |
| `SEC-190` | 🟡 | `migrate-mongo reset` | 迁移重置 |
| `SEC-191` | 🟡 | `migrate -path ... drop` | 迁移删除 |
| `SEC-192` | 🔵 | `dbmate rollback` | 迁移回滚 |
| `SEC-193` | 🟡 | `atlas migrate reset` | 迁移重置 |
| `SEC-194` | 🟡 | `supabase db reset` | 数据库重置 |
| `SEC-195` | 🟡 | `firebase firestore:delete` | 数据清空 |
| `SEC-196` | 🟡 | `heroku apps:destroy` | 应用删除 |
| `SEC-197` | 🟡 | `vercel rm` | 项目删除 |
| `SEC-198` | 🟡 | `netlify sites:delete` | 站点删除 |
| `SEC-199` | 🟡 | `wrangler routes delete` | 域名删除 |
| `SEC-200` | 🟡 | `glab project delete` | 项目删除 |
| `SEC-201` | 🟡 | `gh repo delete` | 仓库删除 |
| `SEC-202` | 🟡 | `gh repo clone && rm -rf .git` | 内容删除 |
| `SEC-203` | 🟡 | `glab ci variable delete` | 变量删除 |
| `SEC-204` | 🟡 | `gh secret delete` | 密钥删除 |
| `SEC-205` | 🟡 | `bitbucket repo delete` | 仓库删除 |
| `SEC-206` | 🟡 | `npm unpublish` | 撤销发布 |
| `SEC-207` | 🔵 | `twine --skip-existing` | 跳过重复上传 |
| `SEC-208` | 🔵 | `docker push --all-tags` | 全标签推送 |
| `SEC-209` | 🔵 | `helm repo remove` | 仓库移除 |
| `SEC-210` | 🟡 | `cargo publish --allow-dirty` | 脏发布 |
| `SEC-211` | 🔵 | `goreleaser --skip-publish` | 跳过发布 |
| `SEC-212` | 🔵 | `sbt publish` | 发布 |
| `SEC-213` | 🔵 | `gradle publish` | 发布 |
| `SEC-214` | 🟡 | `mvn deploy -DskipTests` | 跳过测试部署 |
| `SEC-215` | 🔵 | `dotnet nuget --skip-duplicate` | 跳过重复推送 |
| `SEC-216` | 🔵 | `gem push` | 发布 |
| `SEC-217` | 🟡 | `pod trunk push` | 发布 |
| `SEC-218` | 🟡 | `flutter pub publish` | 发布 |
| `SEC-219` | 🔵 | `swift package publish` | 发布 |
| `SEC-220` | 🔵 | `anaconda upload` | 上传 |
| `SEC-221` | 🟡 | `pip --force-reinstall` | 强制重装 |
| `SEC-222` | 🟡 | `npm install --force` | 强制安装 |
| `SEC-223` | 🔵 | `gem install --force` | 强制安装 |
| `SEC-224` | 🔵 | `cargo install --force` | 强制安装 |
| `SEC-225` | 🔵 | `go get -u @latest` | 最新版获取 |
| `SEC-226` | 🟡 | `crontab -e` / `echo | crontab` | 定时任务注入 |
| `SEC-227` | 🔵 | `at HH:MM` | 定时任务 |
| `SEC-228` | 🔵 | `systemd-analyze verify` | 服务验证 |
| `SEC-229` | 🔵 | `update-rc.d defaults` | 启动脚本 |
| `SEC-230` | 🔵 | `launchctl load` | macOS 服务加载 |
| `SEC-231` | 🟡 | `>> /etc/rc.local` | 启动脚本注入 |
| `SEC-232` | 🟡 | `source <(curl ...)` | 远程加载 |
| `SEC-233` | 🟡 | `>> /etc/profile.d/` | 环境注入 |
| `SEC-234` | 🔵 | `>> /etc/motd` | 消息注入 |
| `SEC-235` | 🟡 | `>> ~/.bash_profile` | 登录脚本注入 |
| `SEC-236` | 🟡 | `>> ~/.zshrc` | zsh 注入 |
| `SEC-237` | 🟡 | `>> ~/.profile` | 登录脚本注入 |
| `SEC-238` | 🟡 | `>> config.fish` | fish 注入 |
| `SEC-239` | 🔵 | `>> ~/.bash_logout` | 注销脚本注入 |
| `SEC-240` | 🔴 | `>> ~/.ssh/authorized_keys` | SSH 后门 |
| `SEC-241` | 🟡 | `>> ~/.ssh/config` | SSH 配置篡改 |
| `SEC-242` | 🔴 | `>> /etc/sudoers` | 权限提升 |
| `SEC-243` | 🔴 | `chpasswd` / `>> /etc/passwd` | 凭据篡改 |
| `SEC-244` | 🟡 | `>> /etc/crontab` | 系统定时任务 |
| `SEC-245` | 🟡 | `>> /etc/systemd/system/*.service` | 服务创建 |
| `SEC-246` | 🔵 | `dconf write` | 桌面策略篡改 |
| `SEC-247` | 🔵 | `polkit-agent-helper-1` | 授权操作 |
| `SEC-248` | 🟡 | `aa-status --complaining` | AppArmor 弱化 |
| `SEC-249` | 🟡 | `setenforce 0` | SELinux 禁用 |
| `SEC-250` | 🟡 | `ufw disable` | 防火墙禁用 |
| `SEC-251` | 🟡 | `PermitRootLogin yes` | SSH 弱配置 |
| `SEC-252` | 🟡 | `>> /etc/pam.d/` | PAM 绕过 |
| `SEC-253` | 🟡 | `auditctl -e 0` | 审计禁用 |
| `SEC-254` | 🟡 | `systemctl stop fail2ban` | 防护停止 |
| `SEC-255` | 🔵 | `>> /etc/hosts.deny` | 访问控制修改 |
| `SEC-256` | 🟡 | `insmod` / `modprobe --force` | 内核模块加载 |
| `SEC-257` | 🔵 | `bpftool prog load` | eBPF 加载 |
| `SEC-258` | 🔵 | `mount -t cgroup` | cgroup 挂载 |
| `SEC-259` | 🟡 | `unshare --mount/--pid` | namespace 逃逸 |
| `SEC-260` | 🔵 | `io_uring` | 异步 IO |
| `SEC-261` | 🟡 | `keyctl add/unlink` | 密钥环操作 |
| `SEC-262` | 🟡 | `prctl PR_SET_SECCOMP 0` | seccomp 禁用 |
| `SEC-263` | 🟡 | `capsh --caps=cap_sys_admin` | 能力提升 |
| `SEC-264` | 🔵 | `ptrace attach` | 进程注入 |
| `SEC-265` | 🔵 | `mprotect PROT_EXEC` | 内存执行 |
| `SEC-266` | 🟡 | `cat /proc/*/mem` | 进程内存读取 |
| `SEC-267` | 🟡 | `dd if=/dev/sda` | 磁盘直接访问 |
| `SEC-268` | 🔵 | `mount -t debugfs` | 调试文件系统 |
| `SEC-269` | 🟡 | `> /sys/` | 内核参数写入 |
| `SEC-270` | 🟡 | `update-grub` / `grub-install --force` | 引导配置修改 |
| `SEC-271` | 🔵 | `bootctl set-efivar` | EFI 变量操作 |
| `SEC-272` | 🟡 | `>> /sys/firmware/efi/efivars` | UEFI 变量写入 |
| `SEC-273` | 🟡 | `dd of=/dev/sdX` | MBR 写入 |
| `SEC-274` | 🔵 | `dmidecode -s system-serial-number` | 硬件信息篡改 |
| `SEC-275` | 🟡 | `fwupd update --force` | 固件强制更新 |
| `SEC-276` | 🟡 | `rkhunter --disable` | Rootkit 检测禁用 |
| `SEC-277` | 🔵 | `chkrootkit --skip` | 检测跳过 |
| `SEC-278` | 🔵 | `lynis --skip-security` | 审计跳过 |
| `SEC-279` | 🟡 | `tripwire --update` | 完整性基线更新 |
| `SEC-280` | 🟡 | `aide --init` | 完整性初始化 |
| `SEC-281` | 🔴 | `cat /etc/shadow` | 密码哈希读取 |
| `SEC-282` | 🔴 | `cat /etc/gshadow` | 组密码读取 |
| `SEC-283` | 🔴 | `cat ~/.ssh/id_rsa` | SSH 私钥读取 |
| `SEC-284` | 🔴 | `export API_KEY/TOKEN=` | 凭据导出 |
| `SEC-285` | 🔵 | `history | grep pass/token` | 历史凭据搜索 |
| `SEC-286` | 🔴 | `cat .env` | 环境变量读取 |
| `SEC-287` | 🔴 | `cat ~/.docker/config.json` | Docker 凭据 |
| `SEC-288` | 🔴 | `cat ~/.aws/credentials` | AWS 凭据 |
| `SEC-289` | 🔴 | `cat gcloud credentials.db` | GCP 凭据 |
| `SEC-290` | 🔴 | `cat ~/.npmrc` | npm 凭据 |
| `SEC-291` | 🔴 | `cat ~/.git-credentials` | Git 凭据 |
| `SEC-292` | 🔴 | `cat ~/.kube/config` | K8s 配置 |
| `SEC-293` | 🟡 | `cat terraform.tfstate` | IaC 状态 |
| `SEC-294` | 🟡 | `kubectl get secret -o yaml` | 密钥导出 |
| `SEC-295` | 🟡 | `vault read secret` | 密钥读取 |
| `SEC-296` | 🔴 | `mysql://user:pass@` | 数据库连接串 |
| `SEC-297` | 🔴 | `redis-cli -a` | 明文密码 |
| `SEC-298` | 🔴 | `amqp://user:pass@` | 消息队列凭据 |
| `SEC-299` | 🟡 | `eyJ...` JWT | 硬编码令牌 |
| `SEC-300` | 🔴 | `ghp_...` | GitHub Token |
| `SEC-301` | 🔴 | `AKIA...` | AWS Access Key |
| `SEC-302` | 🔴 | `sk-...` | OpenAI 密钥 |
| `SEC-303` | 🔴 | `BEGIN PRIVATE KEY` | 私钥块 |
| `SEC-304` | 🔴 | `sk_live_...` | Stripe 密钥 |
| `SEC-305` | 🔴 | `api_key=...` | 通用密钥模式 |
| `SEC-306` | 🔵 | `curl -X POST ... -d` | 数据外传 |
| `SEC-307` | 🟡 | `dig | base64 | bash` | DNS 隧道 |
| `SEC-308` | 🟡 | `ping -p hex` | ICMP 隧道 |
| `SEC-309` | 🔵 | `nc host 53` | DNS 端口通道 |
| `SEC-310` | 🔵 | `socat dns:` | DNS 通道 |
| `SEC-311` | 🟡 | `bzip2 -c | nc` | 压缩管道外传 |
| `SEC-312` | 🟡 | `base64 -w0 | curl` | 编码外传 |
| `SEC-313` | 🟡 | `tar -czf - | nc` | 归档外传 |
| `SEC-314` | 🔵 | `.hidden_backup.sh` | 隐蔽文件名 |
| `SEC-315` | 🔵 | `photo.jpg.sh` | 双扩展名混淆 |
| `SEC-316` | 🔴 | `bash -i >& /dev/tcp/` | 反弹 shell |
| `SEC-317` | 🔴 | `nc -e` | 反弹 shell |
| `SEC-318` | 🔴 | `python socket connect` | 反弹 shell |
| `SEC-319` | 🔴 | `perl socket connect` | 反弹 shell |
| `SEC-320` | 🔴 | `pty.spawn` | 反弹 shell |
| `SEC-321` | 🔵 | `ssh -X/-Y` | X11 转发 |
| `SEC-322` | 🔵 | `ssh -A` | 代理转发 |
| `SEC-323` | 🟡 | `ssh -L` | 本地端口转发 |
| `SEC-324` | 🟡 | `ssh -D` | SOCKS 动态转发 |
| `SEC-325` | 🔵 | `x2goclient --session` | 远程桌面连接 |
| `SEC-326` | 🟡 | `nmap 内网段` | 内网扫描 |
| `SEC-327` | 🟡 | `masscan -p` | 端口扫描 |
| `SEC-328` | 🟡 | `arpspoof` | ARP 欺骗 |
| `SEC-329` | 🟡 | `mitmproxy` | MITM 攻击 |
| `SEC-330` | 🔵 | `tshark -i -w` | 流量抓包 |
| `SEC-331` | 🟡 | `searchsploit` | 漏洞利用搜索 |
| `SEC-332` | 🟡 | `linpeas` / `linenum` | 提权枚举 |
| `SEC-333` | 🟡 | `john --wordlist` / `hashcat` | 密码破解 |
| `SEC-334` | 🟡 | `responder -I` | 流量嗅探 |
| `SEC-335` | 🟡 | `chisel client` | 远程隧道 |
| `SEC-336` | 🟡 | `Cookies.sqlite` | 浏览器凭据窃取 |
| `SEC-337` | 🟡 | `xclip -o | curl` | 剪贴板窃取 |
| `SEC-338` | 🔵 | `xinput test` | 键盘记录 |
| `SEC-339` | 🔵 | `import -window` | 屏幕截图 |
| `SEC-340` | 🟡 | `fswebcam /dev/video0` | 摄像头访问 |
| `SEC-341` | 🟡 | `History.json | curl` | 浏览器历史窃取 |
| `SEC-342` | 🟡 | `cp ~/.ssh/id_rsa` | SSH 密钥复制 |
| `SEC-343` | 🟡 | `secret-tool` | 密钥环转储 |
| `SEC-344` | 🟡 | `gcore -k` | 进程内存转储 |
| `SEC-345` | 🟡 | `scp wallet.dat` | 加密钱包窃取 |
| `SEC-346` | 🔴 | `cat ~/.netrc` | 邮件凭据 |
| `SEC-347` | 🔴 | `cp key4.db` | 浏览器密码 |
| `SEC-348` | 🟡 | `cat client.ovpn` | VPN 凭据 |
| `SEC-349` | 🔴 | `cat .pgpass` | 数据库凭据 |
| `SEC-350` | 🔴 | `cat ~/.gnupg/private-keys-v1.d/` | GPG 私钥 |
| `SEC-351` | 🔵 | `aws s3 ls s3://` | S3 桶列举 |
| `SEC-352` | 🔵 | `aws s3 sync s3://` | S3 数据下载 |
| `SEC-353` | 🔵 | `gsutil cp gs://` | GCS 访问 |
| `SEC-354` | 🔵 | `az blob download` | Azure 下载 |
| `SEC-355` | 🔴 | `curl 169.254.169.254` | 云元数据窃取 |
| `SEC-356` | 🟡 | `system(${CMD})` | 环境变量执行 |
| `SEC-357` | 🔵 | `uname -a` / `os-release` | 系统信息收集 |
| `SEC-358` | 🔵 | `ip addr` / `ifconfig` | 网络侦察 |
| `SEC-359` | 🔵 | `cat /etc/passwd` | 用户枚举 |
| `SEC-360` | 🔵 | `ps aux` / `ps -ef` | 进程侦察 |
| `SEC-361` | 🔵 | `env` / `printenv` | 环境变量收集 |
| `SEC-362` | 🟡 | `grep -r password /etc` | 凭据搜索 |
| `SEC-363` | 🟡 | `cat ~/.bash_history` | 历史读取 |
| `SEC-364` | 🔵 | `ls ~/.ssh/` | SSH 配置收集 |
| `SEC-365` | 🟡 | `find / -name *secret*` | 密钥搜索 |
| `SEC-366` | 🔵 | `systemctl list-units` | 服务枚举 |
| `SEC-367` | 🔵 | `crontab -l` / `atq` | 计划任务枚举 |
| `SEC-368` | 🔵 | `mount -l` / `fstab` | 挂载侦察 |
| `SEC-369` | 🟡 | `sudo -l` | 权限侦察 |
| `SEC-370` | 🔵 | `find / -type f` | 文件系统遍历 |
| `SEC-371` | 🔵 | `cat /proc/version` | 内核信息 |
| `SEC-372` | 🔵 | `lsmod` | 模块枚举 |
| `SEC-373` | 🔵 | `route -n` | 路由收集 |
| `SEC-374` | 🔵 | `ss -tlnp` | 端口枚举 |
| `SEC-375` | 🔵 | `iptables -L` | 防火墙规则 |
| `SEC-376` | 🔵 | `cat /etc/resolv.conf` | DNS 侦察 |
| `SEC-377` | 🔵 | `arp -a` | ARP 缓存 |
| `SEC-378` | 🔵 | `hostname` | 主机信息 |
| `SEC-379` | 🟡 | `grep password /var/log` | 日志敏感信息 |
| `SEC-380` | 🔵 | `ls -la /tmp` | 临时文件侦察 |
| `SEC-381` | 🟡 | `cat ~/.bash_history | base64` | 历史转储 |
| `SEC-382` | 🔴 | `cat /etc/shadow | nc` | 凭据外传 |
| `SEC-383` | 🟡 | `mysqldump -p` | 数据库转储 |
| `SEC-384` | 🟡 | `tar .git | nc` | 源码外传 |
| `SEC-385` | 🟡 | `tar /etc | nc` | 配置外传 |
| `SEC-386` | 🔴 | `curl -o && bash` | 下载执行链 |
| `SEC-387` | 🟡 | `sshpass -p ... ssh` | 凭据复用 |
| `SEC-388` | 🟡 | `ssh -R` | 反向隧道 |
| `SEC-389` | 🟡 | `nohup ... &` | 隐蔽持久化 |
| `SEC-390` | 🟡 | `apt install netcat` | 恶意工具安装 |
| `SEC-391` | 🟡 | `for ... do curl` | 批量执行 |
| `SEC-392` | 🔴 | `export APISECRET=` | 凭据覆盖 |
| `SEC-393` | 🟡 | `dig 超长子域名` | DNS 隧道 |
| `SEC-394` | 🟡 | `eval $CMD` | 命令混淆 |
| `SEC-395` | 🟡 | `rm -rf /var/log` | 日志清理 |
| `SEC-396` | 🟡 | `export https_proxy=user:pass@` | 恶意代理 |
| `SEC-397` | 🟡 | `pip --index-url` | 供应链替换 |
| `SEC-398` | 🟡 | `export LD_PRELOAD=` | 环境篡改 |
| `SEC-399` | 🟡 | `crontab curl` | 定时回连 |
| `SEC-400` | 🔴 | `>> /etc/rc.local` | 启动项注入 |
| `SEC-401` | 🟡 | `docker run -v /etc/passwd` | 敏感挂载 |
| `SEC-402` | 🔴 | `docker run --privileged -v /` | 容器逃逸 |
| `SEC-403` | 🟡 | `docker pull evil/backdoor` | 恶意镜像 |
| `SEC-404` | 🔵 | `docker network connect` | 网络劫持 |
| `SEC-405` | 🟡 | `docker login -p` | 明文凭据 |
| `SEC-406` | 🟡 | `kubectl run --image=evil` | 恶意部署 |
| `SEC-407` | 🟡 | `kubectl apply privileged: true` | 特权容器 |
| `SEC-408` | 🟡 | `kubectl get secrets -o json` | 密钥导出 |
| `SEC-409` | 🟡 | `helm install --repo evil` | 恶意 chart |
| `SEC-410` | 🟡 | `kubectl --as=cluster-admin` | 权限提升 |
| `SEC-411` | 🟡 | `serverless deploy backdoor` | 恶意函数 |
| `SEC-412` | 🔴 | `export AWS_SECRET=` | 云凭据泄露 |
| `SEC-413` | 🟡 | `aws s3 delete` | 云资源删除 |
| `SEC-414` | 🟡 | `aws ... 0.0.0.0/0` | 安全组放开 |
| `SEC-415` | 🟡 | `s3api put-bucket-acl public-read` | 存储公开 |
| `SEC-416` | 🟡 | `>> .github/workflows/` | CI 脚本注入 |
| `SEC-417` | 🟡 | `curl ... $TOKEN` | CI 凭据外传 |
| `SEC-418` | 🟡 | `npm publish --unsafe-perm` | 构建投毒 |
| `SEC-419` | 🟡 | `curl x.py >> app.py` | 代码注入 |
| `SEC-420` | 🔵 | `npm install --no-lockfile` | 锁定绕过 |
| `SEC-421` | 🟡 | `bash -c ... base64` | 脚本混淆 |
| `SEC-422` | 🟡 | `chmod 777 ~/.ssh` | 凭据权限放宽 |
| `SEC-423` | 🔴 | `curl | sudo bash` | 特权管道执行 |
| `SEC-424` | 🟡 | `sudo python -c` | 提权滥用 |
| `SEC-425` | 🟡 | `cp evil /usr/local/bin/` | 进程替换 |
| `SEC-426` | 🔴 | `ln -s /etc/passwd` | 恶意符号链接 |
| `SEC-427` | 🔵 | `chattr +i` | 文件锁定 |
| `SEC-428` | 🔵 | `sysctl -w kernel.` | 内核参数篡改 |
| `SEC-429` | 🟡 | `cp evil /etc/systemd/system/` | 服务替换 |
| `SEC-430` | 🔴 | `useradd -o -u 0` | 后门用户 |
| `SEC-431` | 🟡 | `alias rm=shutdown` | 别名注入 |
| `SEC-432` | 🟡 | `PATH=/tmp:$PATH` | 路径劫持 |
| `SEC-433` | 🟡 | `cd() { ... }` | 函数覆盖 |
| `SEC-434` | 🔵 | `echo \x1b[` | 终端注入 |
| `SEC-435` | 🟡 | `trap rm EXIT` | 恶意 trap |
| `SEC-436` | 🟡 | `base64 -d | bash` | 解码执行 |
| `SEC-437` | 🔴 | `cat /etc/shadow | nc` | 凭据管道外传 |
| `SEC-438` | 🔴 | `aws s3 cp shadow` | 云同步外传 |
| `SEC-439` | 🟡 | `gdb -batch -c dump` | 调试器滥用 |
| `SEC-440` | 🟡 | `nmap -sS` | 隐蔽扫描 |
| `SEC-441` | 🔴 | `rm -rf /` | 根目录删除 |
| `SEC-442` | 🟡 | `mount --bind` | 挂载覆盖 |
| `SEC-443` | 🔵 | `sysctl kernel.hidepid` | 内核隐藏参数 |
| `SEC-444` | 🔴 | `shred /dev/sda` | 磁盘擦除 |
| `SEC-445` | 🔴 | `flashrom -w` | 固件写入 |
| `SEC-446` | 🟡 | `tar /etc | nc` | 配置外发 |
| `SEC-447` | 🟡 | `cp ~/.ssh /tmp/` | 凭据导出 |
| `SEC-448` | 🔵 | `rsync app.db` | 数据库复制 |
| `SEC-449` | 🟡 | `openssl -d secret.pem` | 凭据解密 |
| `SEC-450` | 🟡 | `curl -O && scp` | 传输链 |
| `SEC-451` | 🟡 | `crontab curl` | 定时回连 |
| `SEC-452` | 🟡 | `for ... do ssh` | SSH 批量 |
| `SEC-453` | 🟡 | `export BASH_ENV=` | 环境注入 |
| `SEC-454` | 🟡 | `curl -o x.tar.gz` | 隐蔽下载器 |
| `SEC-455` | 🔵 | `tar -d /` | 恶意自解压 |
| `SEC-456` | 🔴 | `curl http://evil/passwd.txt` | 凭据网页抓取 |
| `SEC-457` | 🔴 | `sudo rm/shutdown` | 特权破坏 |
| `SEC-458` | 🟡 | `tar /etc | base64` | 压缩外发 |
| `SEC-459` | 🔴 | `mkfs /dev/sd` | 磁盘格式化 |
| `SEC-460` | 🟡 | `insmod evil.ko` | 恶意模块加载 |
| `SEC-461` | 🟡 | `npm install browser-extension` | 恶意扩展 |
| `SEC-462` | 🟡 | `screen -x` | 会话窃取 |
| `SEC-463` | 🟡 | `cp evil.so /usr/lib/` | 库注入 |
| `SEC-464` | 🟡 | `cat /proc/*/environ` | 进程环境泄露 |
| `SEC-465` | 🔵 | `rm -f ~/.bash_history` | 历史清理 |
| `SEC-466` | 🟡 | `cat ~/.msmtprc` | 邮件凭据 |
| `SEC-467` | 🔴 | `cat chrome/Login` | 自动填充窃取 |
| `SEC-468` | 🔵 | `aws configure export` | 云配置导出 |
| `SEC-469` | 🟡 | `cat bash_sessions/` | 会话窃取 |
| `SEC-470` | 🔴 | `gpg --export-secret-keys` | 私钥导出 |
| `SEC-471` | 🔴 | `nsenter --mount /proc/*/ns/` | 命名空间逃逸 |
| `SEC-472` | 🔴 | `echo > cgroup.procs` | cgroup 逃逸 |
| `SEC-473` | 🟡 | `tc filter add egress` | eBPF 劫持 |
| `SEC-474` | 🟡 | `crictl exec --privileged` | 运行时提权 |
| `SEC-475` | 🟡 | `docker build --network=host` | 镜像投毒 |
| `SEC-476` | 🔵 | `curl pkg-amd64.tar.gz` | 多架构下载 |
| `SEC-477` | 🟡 | `modprobe -f` | 强制模块加载 |
| `SEC-478` | 🟡 | `fwupdmgr downgrade` | 固件回滚 |
| `SEC-479` | 🔵 | `systemctl acpid` | ACPI 操作 |
| `SEC-480` | 🟡 | `tpm2_clear` | TPM 操作 |
| `SEC-481` | 🟡 | `tar /etc | nc` | 系统备份外传 |
| `SEC-482` | 🔴 | `lvremove /dev/vg` | LVM 破坏 |
| `SEC-483` | 🔴 | `mdadm --stop` | RAID 破坏 |
| `SEC-484` | 🔵 | `strings /dev/` | 磁盘泄露 |
| `SEC-485` | 🔵 | `restic restore` | 系统还原 |
| `SEC-486` | 🟡 | `grub set root` | 引导修复绕过 |
| `SEC-487` | 🟡 | `efibootmgr --uninstall` | 安全启动禁用 |
| `SEC-488` | 🟡 | `grubby --add-kernel` | 内核命令行 |
| `SEC-489` | 🔵 | `dracut -f` | 引导重建 |
| `SEC-490` | 🟡 | `kexec -l` | 内核热加载 |
| `SEC-491` | 🟡 | `systemd-run --on-calendar` | 恶意计时器 |
| `SEC-492` | 🟡 | `auditctl -e 0` | 审计禁用 |
| `SEC-493` | 🟡 | `chcon -t httpd` | SELinux 上下文 |
| `SEC-494` | 🟡 | `ip netns delete` | 命名空间操作 |
| `SEC-495` | 🔵 | `renice -n -20` | CPU 优先级绕过 |
| `SEC-496` | 🔵 | `mosquitto_pub -t -m` | IoT 控制 |
| `SEC-497` | 🔵 | `ip link set down/up` | 网络设备配置 |
| `SEC-498` | 🟡 | `avahi-browse` | 多播发现 |
| `SEC-499` | 🟡 | `cat </dev/ttyS0` | 串口操作 |
| `SEC-500` | 🔵 | `lsusb | grep usb` | USB 设备枚举 |
| `SEC-501` | 🟡 | `echo | base64 -d | bash` | 混淆执行 |
| `SEC-502` | 🟡 | `socat UDP:host:port` | 自定义隧道 |
| `SEC-503` | 🟡 | `echo alias >> ~/.bashrc` | 别名持久化 |
| `SEC-504` | 🔴 | `chroot /bin/sh` | chroot 逃逸 |
| `SEC-505` | 🔵 | `env -i` | 环境清理 |
| `SEC-506` | 🟡 | `pip install torch` | AI 依赖投毒 |
| `SEC-507` | 🔴 | `export OPENAI_API_KEY=` | ML 凭据泄露 |
| `SEC-508` | 🟡 | `chroma delete` | 向量库删除 |
| `SEC-509` | 🟡 | `cat dataset.jsonl` | 训练数据窃取 |
| `SEC-510` | 🟡 | `rm -rf cache` | 推理缓存投毒 |
| `SEC-511` | 🔵 | `playwright --headless` | 浏览器自动化 |
| `SEC-512` | 🟡 | `tesseract img | curl` | OCR 数据窃取 |
| `SEC-513` | 🔵 | `xdotool key` | GUI 自动化 |
| `SEC-514` | 🟡 | `xclip -o | while` | 剪贴板监控 |
| `SEC-515` | 🔵 | `espeak | nc` | 辅助技术利用 |
| `SEC-516` | 🟡 | `arecord -d` | 音频窃取 |
| `SEC-517` | 🔵 | `geoiplookup` | 位置追踪 |
| `SEC-518` | 🟡 | `beef-xss` | 钓鱼工具 |
| `SEC-519` | 🔵 | `vncserver` | 远程控制 |
| `SEC-520` | 🔵 | `foremost /dev/sd` | 数据恢复滥用 |
| `SEC-521` | 🟡 | `patch /usr/src` | 内核补丁 |
| `SEC-522` | 🟡 | `chkrootkit --skip` | 安全工具绕过 |
| `SEC-523` | 🟡 | `nuclei -u` | 漏洞扫描器 |
| `SEC-524` | 🟡 | `hydra -l` | 凭据爆破 |
| `SEC-525` | 🟡 | `iptables -t nat PREROUTING` | 流量重定向 |
| `SEC-526` | 🟡 | `export X=$(curl ...)` | 配置注入 |
| `SEC-527` | 🟡 | `ssh -R` | 反向代理建立 |
| `SEC-528` | 🟡 | `cd /tmp && curl -o` | 工作目录下载 |
| `SEC-529` | 🔴 | `mimikatz` | 凭据转储 |
| `SEC-530` | 🟡 | `for ... do curl` | 批量下载链 |
| `SEC-531` | 🔵 | `obfuscate -o` | 掩码绕过 |
| `SEC-532` | 🔵 | `nm /usr/lib/modules` | 内核符号导出 |
| `SEC-533` | 🟡 | `openocd -c` | 硬件调试器 |
| `SEC-534` | 🔵 | `mount -o rw` | 读写挂载 |
| `SEC-535` | 🔵 | `perf -e --timeout` | 性能工具滥用 |
| `SEC-536` | 🟡 | `zip -e/-p` | 加密压缩投毒 |
| `SEC-537` | 🔵 | `ip netns exec` | 网络命名空间 |
| `SEC-538` | 🟡 | `find / -name *password*` | 文件扫描 |
| `SEC-539` | 🟡 | `insmod --force` | 签名绕过 |
| `SEC-540` | 🔵 | `timeshift create` | 快照操作 |
| `SEC-541` | 🔵 | `logger -p` | 日志投毒 |
| `SEC-542` | 🟡 | `>> /etc/pam.d/` | PAM 篡改 |
| `SEC-543` | 🔴 | `setfacl rwx /etc/passwd` | 系统文件 ACL |
| `SEC-544` | 🟡 | `umask 000` | 权限放宽 |
| `SEC-545` | 🔵 | `xmodmap -e` | 键盘映射 |
| `SEC-546` | 🔵 | `bluetoothctl connect` | 蓝牙操作 |
| `SEC-547` | 🔵 | `nfc-poll` | NFC 操作 |
| `SEC-548` | 🟡 | `aircrack-ng` | 无线渗透 |
| `SEC-549` | 🔵 | `adb shell` | 移动设备交互 |
| `SEC-550` | 🟡 | `binwalk -e` | 固件提取 |
| `SEC-551` | 🟡 | `firejail --noprofile` | 沙箱逃逸 |
| `SEC-552` | 🟡 | `docker commit` | 镜像替换 |
| `SEC-553` | 🟡 | `pip install malicious` | 依赖伪装 |
| `SEC-554` | 🔵 | `git checkout -- config` | 配置回滚 |
| `SEC-555` | 🟡 | `at now +` | 定时注入 |
| `SEC-556` | 🟡 | `echo >> ~/.bashrc` | 环境文件注入 |
| `SEC-557` | 🔴 | `echo >> /etc/sudoers` | sudo 持久化 |
| `SEC-558` | 🟡 | `trust anchor` | 证书安装 |
| `SEC-559` | 🟡 | `usermod -L` | 账户锁定 |
| `SEC-560` | 🔵 | `ibus restart` | IME 切换 |
| `SEC-561` | 🟡 | `rm /var/log/auth.log` | 审计日志清理 |
| `SEC-562` | 🔵 | `touch -d` | 时间戳篡改 |
| `SEC-563` | 🔵 | `timedatectl set-timezone` | 时区切换 |
| `SEC-564` | 🔵 | `export LANG=` | 语言覆盖 |
| `SEC-565` | 🟡 | `history -a /tmp` | 历史共享 |
| `SEC-566` | 🟡 | `mysqldump` / `pg_dump` | 数据转储 |
| `SEC-567` | 🟡 | `mount -o remount,rw /` | 只读绕过 |
| `SEC-568` | 🔵 | `lsblk -o` | 磁盘信息泄露 |
| `SEC-569` | 🟡 | `iptables -F` | 防火墙静默 |
| `SEC-570` | 🔵 | `ip addr add` | 网络配置 |
| `SEC-571` | 🟡 | `strace -e` | 系统调用跟踪 |
| `SEC-572` | 🟡 | `setsebool -P` | 安全策略覆盖 |
| `SEC-573` | 🟡 | `inotifywait -m` | 文件监控 |
| `SEC-574` | 🟡 | `tc mirred` | 流量镜像 |
| `SEC-575` | 🔵 | `openssl passwd` | 密码导出 |
| `SEC-576` | 🔵 | `pip install --no-deps` | 依赖锁定绕过 |
| `SEC-577` | 🟡 | `pip --extra-index-url` | 包源替换 |
| `SEC-578` | 🟡 | `export SSL_CERT_FILE=` | 证书覆盖 |
| `SEC-579` | 🔵 | `Set-ExecutionPolicy` | 脚本策略 |
| `SEC-580` | 🟡 | `alias pip=` | 包管理器别名 |
| `SEC-581` | 🟡 | `cp evil /usr/local/bin/` | 负载持久化 |
| `SEC-582` | 🔴 | `mv evil /bin/ls` | 系统命令替换 |
| `SEC-583` | 🔵 | `ulimit -c` | 核心转储利用 |
| `SEC-584` | 🟡 | `bwrap --share-net` | 沙箱网络逃逸 |
| `SEC-585` | 🟡 | `strace -S` | 系统调用替换 |
| `SEC-586` | 🟡 | `openssl enc file.txt` | 加密勒索模式 |
| `SEC-587` | 🟡 | `rename *.txt` | 批量改名 |
| `SEC-588` | 🔵 | `find / | grep` | 全盘扫描 |
| `SEC-589` | 🟡 | `sed -i app.conf` | 配置替换 |
| `SEC-590` | 🟡 | `rm -rf backup` | 备份删除 |
| `SEC-591` | 🟡 | `systemctl disable firewalld` | 服务自毁 |
| `SEC-592` | 🟡 | `rmmod selinux` | 安全模块卸载 |
| `SEC-593` | 🟡 | `nft delete table` | 网络策略静默 |
| `SEC-594` | 🟡 | `cp sudoers /tmp` | 配置导出 |
| `SEC-595` | 🟡 | `cat auth.log | nc` | 日志外传 |
| `SEC-596` | 🟡 | `curl typosquat.com` | 域名抢注 |
| `SEC-597` | 🟡 | `dig rebind` | DNS 重绑定 |
| `SEC-598` | 🔵 | `squid -p localhost` | 代理污染 |
| `SEC-599` | 🟡 | `chrome --no-sandbox` | 浏览器策略绕过 |
| `SEC-600` | 🟡 | `openssl s_client cert.pem` | 证书欺骗 |
| `SEC-606` | 🟡 | `oathtool -b` | MFA 绕过 |
| `SEC-607` | 🟡 | `curl client_credentials` | OAuth 滥用 |
| `SEC-608` | 🔵 | `klist --cache` | 联邦凭据 |
| `SEC-609` | 🟡 | `nc host:88` | 令牌转发 |
| `SEC-610` | 🟡 | `secret-tool read` | 身份存储导出 |
| `SEC-611` | 🟡 | `echo > /etc/hosts` | 系统数据篡改 |
| `SEC-612` | 🟡 | `aws --no-rotate` | 凭据轮换绕过 |
| `SEC-613` | 🟡 | `echo %0a` | 日志注入 |
| `SEC-614` | 🟡 | `restic prune` | 恢复篡改 |
| `SEC-615` | 🔵 | `ip link set speed` | 配置一致性破坏 |
