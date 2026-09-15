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
    # tmux/screen 隐藏会话
    ("SEC-066", r"\btmux\s+new\s+-s\b|\bscreen\s+-dmS\b", Severity.INFO),
    # awk 输出重定向系统文件
    ("SEC-067", r"\bawk\s+.*>[^|]*/etc/", Severity.INFO),
    # curl|bash 管道执行
    ("SEC-068", r"\bcurl\s+.*\|\s*bash\b|\bwget\s+.*\|\s*bash\b", Severity.WARNING),
    # git clone 后立即执行
    ("SEC-069", r"git\s+clone\s+\S+\s*&&\s*(?:cd|bash|sh)", Severity.WARNING),
    # 源码编译安装（隐藏恶意）
    ("SEC-070", r"(?:./configure\s*&&\s*make|make\s+install)", Severity.INFO),
    # telnet 明文连接
    ("SEC-071", r"\btelnet\s+", Severity.INFO),
    # rc 文件远程下载覆盖
    ("SEC-072", r"(?:curl|wget)\s+.*\s+-o\s+~?/\.(?:bashrc|zshrc|profile)", Severity.WARNING),
    # dbus 系统调用
    ("SEC-073", r"\bdbus-send\b", Severity.INFO),
    # mount 覆盖系统目录
    ("SEC-074", r"\bmount\s+.*\s/(?:etc|usr|bin|lib)\b", Severity.WARNING),
    # ulimit 移除限制
    ("SEC-075", r"\bulimit\s+-c\s+0\b", Severity.INFO),
    # gdb 附加进程
    ("SEC-076", r"\bgdb\s+-p\s+\d+", Severity.WARNING),
    # strace 跟踪
    ("SEC-077", r"\bstrace\s+-p\s+\d+", Severity.INFO),
    # lsof 敏感文件
    ("SEC-078", r"\blsof\s+/etc/shadow|\blsof\s+/dev/mem", Severity.INFO),
    # hexdump 内存
    ("SEC-079", r"\bhexdump\s+/dev/(?:mem|kmem)", Severity.WARNING),
    # iptables 清空
    ("SEC-080", r"\biptables\s+-F\b|\biptables\s+--flush\b", Severity.WARNING),
    # nmap 全端口扫描
    ("SEC-081", r"\bnmap\s+.*-p\s+1-65535", Severity.INFO),
    # metasploit 框架
    ("SEC-082", r"\bmsfconsole\b|\bmsfvenom\b", Severity.WARNING),
    # sqlmap 注入
    ("SEC-083", r"\bsqlmap\s+-u\s+", Severity.WARNING),
    # hydra 爆破
    ("SEC-084", r"\bhydra\s+-l\b|\bhydra\s+-L\b", Severity.WARNING),
    # wifi 破解
    ("SEC-085", r"\bwifite\b|\baircrack-ng\b", Severity.WARNING),
    # encfs 加密绕过
    ("SEC-086", r"\bencfs\s+.*--reverse", Severity.INFO),
    # socat 反连
    ("SEC-087", r"\bsocat\s+TCP:.*:\d+", Severity.INFO),
    # tcpdump 抓包
    ("SEC-088", r"\btcpdump\s+-i\s+.*-w\s+", Severity.INFO),
    # scapy 构造包
    ("SEC-089", r"\bscapy\b.*\bsend\(|\bscapy\b.*\bsr1\(", Severity.WARNING),
    # hostname 冒充
    ("SEC-090", r"\bhostnamectl\s+set-hostname\s+", Severity.INFO),
    # curl -k 忽略证书管道执行
    ("SEC-091", r"\bcurl\s+.*-k\s+.*\|\s*(?:bash|sh)", Severity.WARNING),
    # Python eval/exec input 执行
    ("SEC-092", r"\beval\(\s*input\(|\bexec\(\s*input\(", Severity.WARNING),
    # SSH 反向端口转发
    ("SEC-093", r"\bssh\s+-R\s+\d+:", Severity.WARNING),
    # xargs rm 批量删除
    ("SEC-094", r"\b(?:find|ls)\s+.*\|\s*xargs\s+rm", Severity.WARNING),
    # tar 绝对路径覆盖
    ("SEC-095", r"\btar\s+.*\s-C\s+/", Severity.INFO),
    # curl 管道 sudo sh（高危）
    ("SEC-096", r"\bcurl\s+.*\|\s*sudo\s+sh", Severity.ERROR),
    # pickle 反序列化执行
    ("SEC-097", r"\b(?:pickle|cPickle)\.loads?\(.*(?:exec|eval)", Severity.WARNING),
    # git 递归子模块
    ("SEC-098", r"\bgit\s+submodule\s+update\s+--recursive", Severity.INFO),
    # suid 后门
    ("SEC-099", r"\bchmod\s+u\+s\b|\bchmod\s+g\+s\b", Severity.WARNING),
    # 系统关机重启
    ("SEC-100", r"\b(?:shutdown|reboot|halt|poweroff)\s+-?(?:h|r|f|now)?\b", Severity.WARNING),
    # curl 文件上传外传
    ("SEC-101", r"\bcurl\b[^\n]*-F\s+file=@", Severity.INFO),
    # wget 管道执行
    ("SEC-102", r"\bwget\s+.*\|\s*(?:bash|sh)", Severity.WARNING),
    # ssh-keygen 生成后门密钥
    ("SEC-103", r"\bssh-keygen\s+-t\s+rsa.*-f", Severity.INFO),
    # nc -e 远程 shell
    ("SEC-104", r"\bnc\s+-e\s+\S+\s+\d+", Severity.ERROR),
    # /dev/tcp 后门
    ("SEC-105", r"/dev/tcp/[\d.]+/\d+", Severity.WARNING),
    # cryptsetup 加密覆盖
    ("SEC-106", r"\bcryptsetup\s+luksFormat\b", Severity.INFO),
    # zerotier 远程组网
    ("SEC-107", r"\bzerotier-cli\s+join\b", Severity.INFO),
    # ip 伪造 MAC
    ("SEC-108", r"\bip\s+link\s+set\s+.*address", Severity.INFO),
    # sshpass 明文密码
    ("SEC-109", r"\bsshpass\s+-p\s+", Severity.ERROR),
    # expect 密码脚本
    ("SEC-110", r"\bexpect\s+.*send.*password", Severity.WARNING),
    # SSH ProxyCommand 注入
    ("SEC-111", r"ProxyCommand\s+.*\b(?:bash|sh|nc|socat)", Severity.WARNING),
    # LD_PRELOAD 注入
    ("SEC-112", r"\bLD_PRELOAD=", Severity.WARNING),
    # PYTHONPATH 劫持
    ("SEC-113", r"\bPYTHONPATH=", Severity.INFO),
    # NODE_OPTIONS 注入
    ("SEC-114", r"\bNODE_OPTIONS=", Severity.INFO),
    # JAVA_TOOL_OPTIONS 注入
    ("SEC-115", r"\bJAVA_TOOL_OPTIONS=", Severity.INFO),
    # LD_LIBRARY_PATH 劫持
    ("SEC-116", r"\bLD_LIBRARY_PATH=", Severity.WARNING),
    # GODEBUG/GOGC 运行时注入
    ("SEC-117", r"\b(?:GODEBUG|GOGC)=", Severity.INFO),
    # py_compile 字节码注入
    ("SEC-118", r"\bpy_compile\.compile\(", Severity.INFO),
    # node require 动态加载
    ("SEC-119", r"\brequire\([^)]*(?:\$(?:env|process)|process\.env)", Severity.WARNING),
    # yaml 不安全反序列化
    ("SEC-120", r"yaml\.load\([^)]*Loader=[^)]*(?:Full|Unsafe)Loader", Severity.WARNING),
    # openssl pkcs12 私钥导出
    ("SEC-121", r"\bopenssl\b[^\n]*\bpkcs12\b[^\n]*-export", Severity.INFO),
    # certutil 下载执行
    ("SEC-122", r"\bcertutil\s+-urlcache\b", Severity.WARNING),
    # powershell 编码执行
    ("SEC-123", r"\bpowershell\s+.*-enc\b|\bIEX\(New-Object Net\.WebClient\)", Severity.WARNING),
    # bitsadmin 传输
    ("SEC-124", r"\bbitsadmin\s+/transfer\b", Severity.WARNING),
    # mshta 执行
    ("SEC-125", r"\bmshta\s+(?:http|javascript)", Severity.ERROR),
    # curl 下载到启动目录
    ("SEC-126", r"\bcurl\b[^\n]*-o\s+/etc/init.d/", Severity.WARNING),
    # apt 绕过证书校验
    ("SEC-127", r"\bapt\s+.*--no-check-certificate", Severity.WARNING),
    # gradle 动态执行
    ("SEC-128", r"\bgradle\s+.*-e\b|\bgradle\s+.*--init-script", Severity.INFO),
    # maven 远程仓库
    ("SEC-129", r"\bmvn\s+.*-Dmaven.repo.remote", Severity.INFO),
    # npm 脚本执行
    ("SEC-130", r"\bnpm\s+exec\s+", Severity.WARNING),
    # Docker 逃逸（pid/net=host）
    ("SEC-131", r"docker\s+run.*--pid=host|docker\s+run.*--net=host", Severity.WARNING),
    # kubectl 提权
    ("SEC-132", r"\bkubectl\s+.*\s--as=system:admin", Severity.WARNING),
    # terraform 破坏
    ("SEC-133", r"\bterraform\s+destroy\b", Severity.INFO),
    # ansible 跳过安全标签
    ("SEC-134", r"\bansible-playbook\s+.*--skip-tags=.*security", Severity.INFO),
    # systemctl 禁用防火墙
    ("SEC-135", r"\bsystemctl\s+(?:disable|stop)\s+(?:firewalld|ufw)", Severity.WARNING),
    # docker load 镜像
    ("SEC-136", r"\bdocker\s+load\s+-i\s+", Severity.INFO),
    # docker exec 逃逸
    ("SEC-137", r"\bdocker\s+exec\s+-it\s+.*\s+chroot", Severity.WARNING),
    # containerd 导入
    ("SEC-138", r"\bctr\s+images\s+import", Severity.INFO),
    # kubeadm reset
    ("SEC-139", r"\bkubeadm\s+reset\b", Severity.INFO),
    # helm 模板注入
    ("SEC-140", r"\bhelm\s+template\s+.*--set\s+.*\$\(", Severity.INFO),
    # serverless 部署
    ("SEC-141", r"\bserverless\s+deploy\s+.*--stage=prod", Severity.INFO),
    # cloudformation 参数注入
    ("SEC-142", r"\bcloudformation\s+deploy.*--parameter-overrides", Severity.INFO),
    # AWS 弱密码策略
    ("SEC-143", r"\baws\s+iam\s+update-account-password-policy.*--minimum-password-length\s+[0-5]", Severity.WARNING),
    # GCP 防火墙全开
    ("SEC-144", r"\bgcloud\s+compute\s+firewall-rules\s+create.*--allow\s+all", Severity.WARNING),
    # Azure 存储密钥上传
    ("SEC-145", r"\baz\s+storage\s+blob\s+upload.*--auth-mode\s+key", Severity.INFO),
    # etcd 密钥访问
    ("SEC-146", r"\betcdctl\s+get\s+/registry/secrets", Severity.WARNING),
    # vault 密封禁用
    ("SEC-147", r"\bvault\s+seal\s+disable", Severity.WARNING),
    # consul 配置篡改
    ("SEC-148", r"\bconsul\s+kv\s+put\s+.*--token", Severity.INFO),
    # zookeeper 数据删除
    ("SEC-149", r"\bzkCli\s+deleteall\s+/", Severity.WARNING),
    # redis 配置修改
    ("SEC-150", r"\bredis-cli\s+CONFIG\s+SET\s+(?:dir|dbfilename)", Severity.WARNING),
    # mongo 删除数据库
    ("SEC-151", r"\bmongo\s+.*--eval\s+.*db.dropDatabase", Severity.ERROR),
    # psql 删表
    ("SEC-152", r"\bpsql\s+.*-c\s+.*DROP\s+TABLE", Severity.ERROR),
    # mysql 删库
    ("SEC-153", r"\bmysql\s+.*-e\s+.*DROP\s+DATABASE", Severity.ERROR),
    # sqlite 清空
    ("SEC-154", r"\bsqlite3\s+.*DELETE\s+FROM\s+", Severity.WARNING),
    # elasticsearch 删索引
    ("SEC-155", r"\bcurl\b[^\n]*-X\s+DELETE\s+.*/_all", Severity.WARNING),
    # hive 删表
    ("SEC-156", r"\bhive\s+.*DROP\s+TABLE", Severity.WARNING),
    # cassandra 删键空间
    ("SEC-157", r"\bcqlsh\s+.*DROP\s+KEYSPACE", Severity.ERROR),
    # neo4j 清空库
    ("SEC-158", r"\bneo4j(?:-shell)?\s+.*MATCH.*DELETE", Severity.WARNING),
    # influx 删测量
    ("SEC-159", r"\binflux\s+delete\s+--measurement", Severity.WARNING),
    # clickhouse 删表
    ("SEC-160", r"\bclickhouse-client\s+.*DROP\s+TABLE", Severity.WARNING),
    # kafka 删主题
    ("SEC-161", r"\bkafka-topics\s+.*--delete", Severity.WARNING),
    # rabbitmq 清队列
    ("SEC-162", r"\brabbitmqctl\s+purge_queue", Severity.WARNING),
    # ES 删索引
    ("SEC-163", r"\bcurl\b[^\n]*-X\s+DELETE\s+.*/index", Severity.WARNING),
    # solr 删核心
    ("SEC-164", r"\bsolr\s+delete\s+-c\s+", Severity.WARNING),
    # ksql 删流
    ("SEC-165", r"\bksql\s+.*DROP\s+STREAM", Severity.WARNING),
    # grafana 数据源篡改
    ("SEC-166", r"\bgrafana-cli\s+.*datasource", Severity.INFO),
    # prometheus 配置注入
    ("SEC-167", r"\bpromtool\s+check\s+config.*--enable-feature", Severity.INFO),
    # loki 删日志
    ("SEC-168", r"\bcurl\b[^\n]*-X\s+DELETE\s+.*/loki", Severity.WARNING),
    # jaeger 删追踪
    ("SEC-169", r"\bcurl\b[^\n]*-X\s+DELETE\s+.*/jaeger", Severity.INFO),
    # kibana 删索引模式
    ("SEC-170", r"\bcurl\b[^\n]*-X\s+DELETE\s+.*/kibana", Severity.WARNING),
    # consul 服务注销
    ("SEC-171", r"\bconsul\s+services\s+deregister", Severity.WARNING),
    # etcd 成员移除
    ("SEC-172", r"\betcdctl\s+member\s+remove", Severity.WARNING),
    # nomad 作业停止
    ("SEC-173", r"\bnomad\s+job\s+stop", Severity.INFO),
    # vault 密钥删除
    ("SEC-174", r"\bvault\s+delete\s+secret", Severity.WARNING),
    # keycloak 领域删除
    ("SEC-175", r"\bkcadm\s+delete\s+realms", Severity.WARNING),
    # openshift 集群删除
    ("SEC-176", r"\boc\s+delete\s+cluster", Severity.WARNING),
    # rancher 集群删除
    ("SEC-177", r"\brancher\s+clusters\s+rm", Severity.WARNING),
    # eks 集群删除
    ("SEC-178", r"\baws\s+eks\s+delete-cluster", Severity.WARNING),
    # gke 集群删除
    ("SEC-179", r"\bgcloud\s+container\s+clusters\s+delete", Severity.WARNING),
    # aks 集群删除
    ("SEC-180", r"\baz\s+aks\s+delete", Severity.WARNING),
    # flyway 回滚
    ("SEC-181", r"\bflyway\s+undo\b", Severity.WARNING),
    # liquibase 回滚
    ("SEC-182", r"\bliquibase\s+rollback", Severity.WARNING),
    # alembic 降级
    ("SEC-183", r"\balembic\s+downgrade\b", Severity.WARNING),
    # django migrate 回滚
    ("SEC-184", r"\bmigrate\s+zero\b", Severity.WARNING),
    # prisma 重置
    ("SEC-185", r"\bprisma\s+migrate\s+reset\b", Severity.WARNING),
    # sequelize 强制同步
    ("SEC-186", r"\bsequelize\s+sync\s+.*--force", Severity.WARNING),
    # typeorm 模式同步
    ("SEC-187", r"\btypeorm\s+schema:sync", Severity.INFO),
    # knex 迁移回滚
    ("SEC-188", r"\bknex\s+migrate:rollback", Severity.INFO),
    # drizzle 强制推送
    ("SEC-189", r"\bdrizzle-kit\s+push.*--force", Severity.WARNING),
    # migrate-mongo 重置
    ("SEC-190", r"\bmigrate-mongo\s+reset", Severity.WARNING),
    # golang-migrate 删除
    ("SEC-191", r"\bmigrate\s+-path.*\sdrop", Severity.WARNING),
    # dbmate 回滚
    ("SEC-192", r"\bdbmate\s+rollback\b", Severity.INFO),
    # atlas 迁移重置
    ("SEC-193", r"\batlas\s+migrate\s+reset", Severity.WARNING),
    # supabase 重置
    ("SEC-194", r"\bsupabase\s+db\s+reset", Severity.WARNING),
    # firebase 清空
    ("SEC-195", r"\bfirebase\s+firestore:delete", Severity.WARNING),
    # heroku 应用删除
    ("SEC-196", r"\bheroku\s+apps:destroy", Severity.WARNING),
    # vercel 项目删除
    ("SEC-197", r"\bvercel\s+rm\s+", Severity.WARNING),
    # netlify 站点删除
    ("SEC-198", r"\bnetlify\s+sites:delete", Severity.WARNING),
    # cloudflare 域名删除
    ("SEC-199", r"\bwrangler\s+routes\s+delete|\bcloudflare\s+delete\s+zone", Severity.WARNING),
    # gitlab 项目删除
    ("SEC-200", r"\bglab\s+project\s+delete|\bgitlab\s+project\s+remove", Severity.WARNING),
    # gh repo 删除
    ("SEC-201", r"\bgh\s+repo\s+delete\b", Severity.WARNING),
    # gh 全部内容删除
    ("SEC-202", r"\bgh\s+repo\s+clone.*&&\s+rm\s+-rf.*\.git", Severity.WARNING),
    # glab 变量删除
    ("SEC-203", r"\bglab\s+ci\s+variable\s+delete", Severity.WARNING),
    # gh secret 删除
    ("SEC-204", r"\bgh\s+secret\s+delete\b", Severity.WARNING),
    # bitbucket 仓库删除
    ("SEC-205", r"\bbitbucket\s+repo\s+delete\b", Severity.WARNING),
    # npm 撤销发布
    ("SEC-206", r"\bnpm\s+unpublish\b", Severity.WARNING),
    # twine 跳过已存在上传
    ("SEC-207", r"\btwine\s+upload\s+--repository\s+.*--skip-existing", Severity.INFO),
    # docker 推送全部标签
    ("SEC-208", r"\bdocker\s+push\s+.*--all-tags", Severity.INFO),
    # helm 仓库移除
    ("SEC-209", r"\bhelm\s+repo\s+remove\b", Severity.INFO),
    # cargo 脏发布
    ("SEC-210", r"\bcargo\s+publish\s+--allow-dirty", Severity.WARNING),
    # goreleaser 发布
    ("SEC-211", r"\bgoreleaser\s+release\s+--skip-publish", Severity.INFO),
    # sbt 发布
    ("SEC-212", r"\bsbt\s+publish\b", Severity.INFO),
    # gradle 发布
    ("SEC-213", r"\bgradle\s+publish\b", Severity.INFO),
    # maven 跳过测试部署
    ("SEC-214", r"\bmvn\s+deploy\s+-DskipTests", Severity.WARNING),
    # nuget 跳过重复推送
    ("SEC-215", r"\bdotnet\s+nuget\s+push\s+.*--skip-duplicate", Severity.INFO),
    # gem 发布
    ("SEC-216", r"\bgem\s+push\b", Severity.INFO),
    # pod trunk 发布
    ("SEC-217", r"\bpod\s+trunk\s+push\b", Severity.WARNING),
    # flutter 发布
    ("SEC-218", r"\bflutter\s+pub\s+publish\b", Severity.WARNING),
    # swift 发布
    ("SEC-219", r"\bswift\s+package\s+publish\b", Severity.INFO),
    # conda 上传
    ("SEC-220", r"\banaconda\s+upload\b", Severity.INFO),
    # pip 强制重装
    ("SEC-221", r"\bpip\s+install\s+--force-reinstall", Severity.WARNING),
    # npm 强制安装
    ("SEC-222", r"\bnpm\s+install\s+--force\b", Severity.WARNING),
    # gem 强制安装
    ("SEC-223", r"\bgem\s+install\s+--force\b", Severity.INFO),
    # cargo 强制安装
    ("SEC-224", r"\bcargo\s+install\s+--force\b", Severity.INFO),
    # go get 最新版
    ("SEC-225", r"\bgo\s+get\s+-u\s+.*@latest", Severity.INFO),
    # crontab 注入
    ("SEC-226", r"\bcrontab\s+-e\b|echo\s+.*\s*\|\s*crontab", Severity.WARNING),
    # at 定时任务
    ("SEC-227", r"\bat\s+\d+[:.]\d+", Severity.INFO),
    # systemd timer 验证
    ("SEC-228", r"\bsystemd-analyze\s+verify", Severity.INFO),
    # init.d 脚本注入
    ("SEC-229", r"\bupdate-rc.d\s+.*defaults", Severity.INFO),
    # launchd 加载
    ("SEC-230", r"\blaunchctl\s+load\b", Severity.INFO),
    # rc.local 注入
    ("SEC-231", r">>\s*/etc/rc.local|echo\s+.*\s*>>\s*/etc/rc.local", Severity.WARNING),
    # bashrc 远程加载
    ("SEC-232", r"\bsource\s+<\(curl", Severity.WARNING),
    # profile.d 注入
    ("SEC-233", r">>\s*/etc/profile.d/", Severity.WARNING),
    # motd 注入
    ("SEC-234", r">>\s*/etc/motd|echo\s+.*\s*>>\s*/etc/motd", Severity.INFO),
    # bash_profile 注入
    ("SEC-235", r">>\s*~?/\.bash_profile", Severity.WARNING),
    # zshrc 注入
    ("SEC-236", r">>\s*~?/\.zshrc", Severity.WARNING),
    # profile 注入
    ("SEC-237", r">>\s*~?/\.profile", Severity.WARNING),
    # fish config 注入
    ("SEC-238", r">>\s*~?/\.config/fish/config.fish", Severity.WARNING),
    # bash_logout 注入
    ("SEC-239", r">>\s*~?/\.bash_logout", Severity.INFO),
    # SSH authorized_keys 追加
    ("SEC-240", r">>\s*~?/\.ssh/authorized_keys", Severity.ERROR),
    # ssh config 修改
    ("SEC-241", r">>\s*~?/\.ssh/config", Severity.WARNING),
    # sudoers 修改
    ("SEC-242", r">>\s*/etc/sudoers|echo\s+.*\s*>>\s*/etc/sudoers.d/", Severity.ERROR),
    # passwd/shadow 修改
    ("SEC-243", r"\bchpasswd\b|>>\s*/etc/passwd", Severity.ERROR),
    # crontab 系统级
    ("SEC-244", r">>\s*/etc/crontab", Severity.WARNING),
    # systemd 服务创建
    ("SEC-245", r">>\s*/etc/systemd/system/.*\.service", Severity.WARNING),
    # dconf 策略修改
    ("SEC-246", r"\bdconf\s+write\b", Severity.INFO),
    # polkit 操作
    ("SEC-247", r"\bpolkit-agent-helper-1\b", Severity.INFO),
    # apparmor 禁用
    ("SEC-248", r"\baa-status\s+--complaining|apparmor_parser\s+-R", Severity.WARNING),
    # selinux 禁用
    ("SEC-249", r"\bsetenforce\s+0\b|\bsetenforce\s+permissive", Severity.WARNING),
    # ufw 禁用
    ("SEC-250", r"\bufw\s+disable\b", Severity.WARNING),
    # sshd 弱配置
    ("SEC-251", r"PermitRootLogin\s+yes|PasswordAuthentication\s+no", Severity.WARNING),
    # pam 配置绕过
    ("SEC-252", r">>\s*/etc/pam.d/", Severity.WARNING),
    # auditd 禁用
    ("SEC-253", r"\bauditctl\s+-e\s+0\b", Severity.WARNING),
    # fail2ban 停止
    ("SEC-254", r"\bsystemctl\s+stop\s+fail2ban", Severity.WARNING),
    # hosts.deny 修改
    ("SEC-255", r">>\s*/etc/hosts.deny", Severity.INFO),
    # 内核模块加载
    ("SEC-256", r"\binsmod\b|\bmodprobe\s+.*--force", Severity.WARNING),
    # eBPF 程序加载
    ("SEC-257", r"\bbpftool\s+prog\s+load", Severity.INFO),
    # cgroup 挂载
    ("SEC-258", r"\bmount\s+-t\s+cgroup", Severity.INFO),
    # namespace 逃逸
    ("SEC-259", r"\bunshare\s+--mount\b|\bunshare\s+--pid\b", Severity.WARNING),
    # io_uring
    ("SEC-260", r"\bio_uring\s+", Severity.INFO),
    # keyring 密钥操作
    ("SEC-261", r"\bkeyctl\s+add\b|\bkeyctl\s+unlink\b", Severity.WARNING),
    # seccomp 禁用
    ("SEC-262", r"\bprctl\s+PR_SET_SECCOMP\s+0", Severity.WARNING),
    # capability 提升
    ("SEC-263", r"\bcapsh\s+--caps=\S*cap_sys_admin", Severity.WARNING),
    # ptrace 注入
    ("SEC-264", r"\bptrace\s+attach\b", Severity.INFO),
    # mprotect 执行
    ("SEC-265", r"\bmprotect\s+PROT_EXEC", Severity.INFO),
    # /proc 内存读取
    ("SEC-266", r"\bcat\s+/proc/\d+/mem|\bdd\s+if=/proc/\d+/mem", Severity.WARNING),
    # /dev 磁盘访问
    ("SEC-267", r"\bcat\s+/dev/sda\b|\bdd\s+if=/dev/sda\b", Severity.WARNING),
    # debugfs 挂载
    ("SEC-268", r"\bmount\s+-t\s+debugfs", Severity.INFO),
    # sysfs 写入
    ("SEC-269", r">\s*/sys/|echo\s+.*\s*\|\s*tee\s+/sys/", Severity.WARNING),
    # grub 修改
    ("SEC-270", r"\bupdate-grub\b|\bgrub-install\s+.*--force", Severity.WARNING),
    # bootctl EFI 变量
    ("SEC-271", r"\bbootctl\s+set-efivar\b", Severity.INFO),
    # UEFI 变量写入
    ("SEC-272", r">>\s*/sys/firmware/efi/efivars", Severity.WARNING),
    # MBR 写入
    ("SEC-273", r"\bdd\s+if=\S+\s+of=/dev/sd[a-z]\b", Severity.WARNING),
    # dmidecode 篡改
    ("SEC-274", r"\bdmidecode\s+-s\s+system-serial-number", Severity.INFO),
    # 固件更新
    ("SEC-275", r"\bfwupd\s+update\s+.*--force", Severity.WARNING),
    # rkhunter 禁用
    ("SEC-276", r"\brkhunter\s+--disable\b", Severity.WARNING),
    # chkrootkit 跳过
    ("SEC-277", r"\bchkrootkit\s+--skip\b", Severity.INFO),
    # lynis 跳过审计
    ("SEC-278", r"\blynis\s+audit\s+--skip-.*security", Severity.INFO),
    # tripwire 更新
    ("SEC-279", r"\btripwire\s+--update\b", Severity.WARNING),
    # aide 初始化
    ("SEC-280", r"\baide\s+--init\b", Severity.WARNING),
    # shadow 文件读取
    ("SEC-281", r"\bcat\s+/etc/shadow|\bless\s+/etc/shadow|\btail\s+/etc/shadow", Severity.ERROR),
    # gshadow 读取
    ("SEC-282", r"\bcat\s+/etc/gshadow|\bless\s+/etc/gshadow", Severity.ERROR),
    # SSH 私钥读取
    ("SEC-283", r"\bcat\s+~?/\.ssh/id_rsa|\bcat\s+~?/\.ssh/id_ed25519", Severity.ERROR),
    # 环境变量凭据导出
    ("SEC-284", r"\bexport\s+\w*\b(?:API_KEY|TOKEN|SECRET|PASSWORD)=", Severity.ERROR),
    # 历史命令凭据搜索
    ("SEC-285", r"\bhistory\s+\|\s*grep\s+-i\s+.*(?:pass|token|secret)", Severity.INFO),
    # .env 文件读取
    ("SEC-286", r"\bcat\s+\.env\b|\bsource\s+\.env\b", Severity.ERROR),
    # docker 凭据读取
    ("SEC-287", r"\bcat\s+~?/\.docker/config.json", Severity.ERROR),
    # aws 凭据读取
    ("SEC-288", r"\bcat\s+~?/\.aws/credentials", Severity.ERROR),
    # gcloud 凭据读取
    ("SEC-289", r"\bcat\s+~?/\.config/gcloud/credentials.db", Severity.ERROR),
    # npm 凭据读取
    ("SEC-290", r"\bcat\s+~?/\.npmrc", Severity.ERROR),
    # git 凭据读取
    ("SEC-291", r"\bcat\s+~?/\.git-credentials", Severity.ERROR),
    # kubeconfig 读取
    ("SEC-292", r"\bcat\s+~?/\.kube/config", Severity.ERROR),
    # terraform 状态读取
    ("SEC-293", r"\bcat\s+.*terraform.tfstate", Severity.WARNING),
    # kubectl secret 获取
    ("SEC-294", r"\bkubectl\s+get\s+secret.*-o\s+yaml", Severity.WARNING),
    # vault 读取
    ("SEC-295", r"\bvault\s+read\s+secret", Severity.WARNING),
    # 数据库连接字符串凭据
    ("SEC-296", r"(?:mysql|postgres|mongodb)://\w+:\w+@", Severity.ERROR),
    # redis 密码明文
    ("SEC-297", r"\bredis-cli\s+-a\s+\S+", Severity.ERROR),
    # amqp 凭据
    ("SEC-298", r"(?:amqp|amqps)://\w+:\w+@", Severity.ERROR),
    # JWT 硬编码
    ("SEC-299", r"\beyJ[A-Za-z0-9_-]{10,}\.\S+\.\S+", Severity.WARNING),
    # GitHub token 硬编码
    ("SEC-300", r"\bghp_[A-Za-z0-9]{30,}\b", Severity.ERROR),
    # AWS 密钥硬编码
    ("SEC-301", r"\bAKIA[0-9A-Z]{16}\b", Severity.ERROR),
    # OpenAI 密钥硬编码
    ("SEC-302", r"\bsk-[A-Za-z0-9]{20,}\b", Severity.ERROR),
    # 私钥块硬编码
    ("SEC-303", r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", Severity.ERROR),
    # Stripe 密钥
    ("SEC-304", r"\bsk_live_[A-Za-z0-9]{20,}\b", Severity.ERROR),
    # 通用密钥模式
    ("SEC-305", r"(?:api[_-]?key|secret|token)\s*[:=]\s*['\"]?[A-Za-z0-9+/=_-]{16,}['\"]?", Severity.ERROR),
    # curl POST 数据外传
    ("SEC-306", r"\bcurl\b[^\n]*-X\s+POST\s+[^\n]*https?://\S+\s+-d", Severity.INFO),
    # DNS 隧道
    ("SEC-307", r"\bdig\s+.*\|\s*base64\s+\|\s*bash", Severity.WARNING),
    # ICMP 隧道
    ("SEC-308", r"\bping\s+-p\s+[0-9a-f]+", Severity.WARNING),
    # nc 53 端口隐蔽通道
    ("SEC-309", r"\bnc\s+\S+\s+53\b", Severity.INFO),
    # socat DNS 通道
    ("SEC-310", r"\bsocat\s+.*dns:", Severity.INFO),
    # 压缩管道外传
    ("SEC-311", r"\bbzip2\s+-c\s+\S+\s+\|\s+nc", Severity.WARNING),
    # base64 外传
    ("SEC-312", r"\bbase64\s+-w0\s+\S+\s+\|\s+(?:nc|curl)", Severity.WARNING),
    # tar 管道外传
    ("SEC-313", r"\btar\s+-czf\s+-\s+\S+\s+\|\s+(?:nc|curl)", Severity.WARNING),
    # 隐蔽文件名
    ("SEC-314", r"\.(?:hidden|secret|private|backup|tmp)[\w_-]*\.(?:sh|py|txt)\b", Severity.INFO),
    # 双扩展名混淆
    ("SEC-315", r"\b\w+\.[A-Za-z0-9_]{2,5}\.(?:sh|py|exe|bat|cmd)\b", Severity.INFO),
    # bash /dev/tcp 反弹 shell
    ("SEC-316", r"bash -i >& /dev/tcp/|sh -i >& /dev/tcp/", Severity.ERROR),
    # nc -e 反弹 shell
    ("SEC-317", r"\bnc\s+\S+\s+\d+\s+-e\s+\S+", Severity.ERROR),
    # python 反弹 shell
    ("SEC-318", r"python(?:3)?\s+-c\s+.*socket.*connect", Severity.ERROR),
    # perl 反弹 shell
    ("SEC-319", r"\bperl\s+-e\s+.*socket.*connect", Severity.ERROR),
    # pty 反弹 shell
    ("SEC-320", r"python.*-c\s+import\s+pty.*spawn", Severity.ERROR),
    # SSH X11 转发
    ("SEC-321", r"\bssh\s+-X\b|\bssh\s+-Y\b", Severity.INFO),
    # SSH 代理转发
    ("SEC-322", r"\bssh\s+-A\b", Severity.INFO),
    # SSH 本地端口转发
    ("SEC-323", r"\bssh\s+-L\s+\d+:", Severity.WARNING),
    # SSH 动态转发（SOCKS）
    ("SEC-324", r"\bssh\s+-D\s+\d+", Severity.WARNING),
    # X2Go 连接
    ("SEC-325", r"\bx2goclient\s+--session", Severity.INFO),
    # 内网 nmap 扫描
    ("SEC-326", r"\bnmap\s+10\.|\bnmap\s+192\.168\.|\bnmap\s+172\.(?:1[6-9]|2[0-9]|3[01])\.", Severity.WARNING),
    # masscan 扫描
    ("SEC-327", r"\bmasscan\s+-p\s+", Severity.WARNING),
    # ARP 欺骗
    ("SEC-328", r"\barpspoof\b|\bbettercap\b.*\sarp", Severity.WARNING),
    # MITM 攻击
    ("SEC-329", r"\bmitmproxy\b|\bbettercap\b.*--mitm", Severity.WARNING),
    # tshark 抓包
    ("SEC-330", r"\btshark\s+-i\s+.*-w\s+", Severity.INFO),
    # 漏洞利用框架
    ("SEC-331", r"\bsearchsploit\s+", Severity.WARNING),
    # 提权工具
    ("SEC-332", r"\b(?:linpeas|linenum|linux-exploit-suggester)\b", Severity.WARNING),
    # 密码破解
    ("SEC-333", r"\bjohn\s+.*--wordlist|\bhashcat\s+-m\s+", Severity.WARNING),
    # 流量嗅探
    ("SEC-334", r"\bdnschef\b|\bresponder\b.*\s-I\s+", Severity.WARNING),
    # 远程控制工具
    ("SEC-335", r"\b(?:chisel|ligolo-ng|nps)\b.*\sclient", Severity.WARNING),
    # 浏览器凭据窃取
    ("SEC-336", r"\b(?:login_data|Cookies)\.sqlite|\bchrome\s+.*--headless.*--dump-dom", Severity.WARNING),
    # 剪贴板窃取
    ("SEC-337", r"\b(?:xclip|xsel)\s+-o\s+\|\s+(?:curl|nc)", Severity.WARNING),
    # 键盘记录
    ("SEC-338", r"\b(?:keylog|xinput)\s+test\s+", Severity.INFO),
    # 屏幕截图
    ("SEC-339", r"\b(?:import|scrot|gnome-screenshot)\s+.*-(?:w|window)\s+", Severity.INFO),
    # 摄像头访问
    ("SEC-340", r"\b(?:fswebcam|ffmpeg)\s+.*/dev/video0", Severity.WARNING),
    # 浏览器历史窃取
    ("SEC-341", r"\b(?:History|Bookmarks)\.json.*\s(?:curl|nc|scp)", Severity.WARNING),
    # SSH 密钥复制
    ("SEC-342", r"\bcp\s+~?/\.ssh/id_\w+\s+", Severity.WARNING),
    # gnome-keyring 转储
    ("SEC-343", r"\b(?:gnome-keyring|secret-tool)\s+\S+\s+\S+", Severity.WARNING),
    # 进程内存转储
    ("SEC-344", r"\bgcore\b[^\n]*-k\s+\d+", Severity.WARNING),
    # 加密钱包文件
    ("SEC-345", r"\b(?:scp|nc|curl)\s+\S*wallet\.dat|wallet\.dat.*\s(?:scp|nc|curl)", Severity.WARNING),
    # 邮件凭据读取
    ("SEC-346", r"\bcat\s+~?/\.msmtprc|\bcat\s+~?/\.netrc", Severity.ERROR),
    # 浏览器密码存储
    ("SEC-347", r"\b(?:cp|scp|curl)\s+\S*(?:key4\.db|logins\.json)|(?:key4\.db|logins\.json).*\s(?:cp|scp|curl)", Severity.ERROR),
    # VPN 配置凭据
    ("SEC-348", r"\bcat\s+.*\.ovpn|\bcat\s+.*wireguard.*conf", Severity.WARNING),
    # 数据库凭据文件
    ("SEC-349", r"\bcat\s+.*\.(?:pgpass|my\.cnf)", Severity.ERROR),
    # GPG 私钥目录
    ("SEC-350", r"\bcat\s+~?/\.gnupg/private-keys-v1\.d/", Severity.ERROR),
    # S3 桶列举
    ("SEC-351", r"\baws\s+s3\s+ls\s+s3://", Severity.INFO),
    # S3 桶同步下载
    ("SEC-352", r"\baws\s+s3\s+sync\s+s3://", Severity.INFO),
    # GCS 存储访问
    ("SEC-353", r"\bgsutil\s+cp\s+gs://", Severity.INFO),
    # Azure Blob 下载
    ("SEC-354", r"\baz\s+storage\s+blob\s+download", Severity.INFO),
    # 云实例元数据访问
    ("SEC-355", r"curl\s+.*169\.254\.169\.254|curl\s+.*metadata\.google\.internal", Severity.ERROR),
    # 环境变量命令执行
    ("SEC-356", r"\b(?:system|exec|popen)\(\s*[A-Za-z_]*\$\{?\w+\}?", Severity.WARNING),
    # 系统信息泄露收集
    ("SEC-357", r"\buname\s+-a\b|\bcat\s+/etc/os-release", Severity.INFO),
    # 网络信息收集
    ("SEC-358", r"\bip\s+addr\b|\bifconfig\s+\S*eth\d", Severity.INFO),
    # 用户枚举
    ("SEC-359", r"\bcat\s+/etc/passwd|\bgetent\s+passwd", Severity.INFO),
    # 进程枚举
    ("SEC-360", r"\bps\s+aux\b|\bps\s+-ef\b", Severity.INFO),
    # 环境变量凭据收集
    ("SEC-361", r"\benv\s*$|\bprintenv\b|\bset\s*$", Severity.INFO),
    # 凭据文件批量搜索
    ("SEC-362", r"\bgrep\s+-r\s+.*(?:password|secret|token)\s+/etc|\bgrep\s+-r\s+.*(?:password|secret|token)\s+~", Severity.WARNING),
    # 历史命令读取
    ("SEC-363", r"\bcat\s+~?/\.(?:bash_history|zsh_history)", Severity.WARNING),
    # SSH 配置批量收集
    ("SEC-364", r"\bcat\s+~?/\.ssh/id_\w+\.pub|\bls\s+~?/\.ssh/", Severity.INFO),
    # 密钥环搜索
    ("SEC-365", r"\bfind\s+/\s+-name\s+.*(?:credential|secret|token|key)\S*\s+2>/dev/null", Severity.WARNING),
    # 系统服务枚举
    ("SEC-366", r"\bsystemctl\s+list-units\b|\bservice\s+--status-all\b", Severity.INFO),
    # 计划任务枚举
    ("SEC-367", r"\bcrontab\s+-l\b|\batq\b", Severity.INFO),
    # 挂载信息收集
    ("SEC-368", r"\bmount\s*-l\b|\bcat\s+/etc/fstab", Severity.INFO),
    # sudo 配置侦察
    ("SEC-369", r"\bsudo\s+-l\b|\bcat\s+/etc/sudoers", Severity.WARNING),
    # 文件系统遍历
    ("SEC-370", r"\bls\s+-laR\s+/|\bfind\s+/\s+-type\s+f\s+2>/dev/null", Severity.INFO),
    # 内核与补丁信息
    ("SEC-371", r"\bcat\s+/proc/version|\buname\s+-r\b", Severity.INFO),
    # 内核模块枚举
    ("SEC-372", r"\blsmod\b|\bcat\s+/proc/modules", Severity.INFO),
    # 路由表收集
    ("SEC-373", r"\broute\s+-n\b|\bip\s+route\b", Severity.INFO),
    # 开放端口枚举
    ("SEC-374", r"\bss\s+-tlnp\b|\bnetstat\s+-tlnp\b", Severity.INFO),
    # 防火墙规则收集
    ("SEC-375", r"\biptables\s+-L\b|\bip6tables\s+-L\b", Severity.INFO),
    # DNS 配置侦察
    ("SEC-376", r"\bcat\s+/etc/resolv.conf|\bdig\s+.*\s+any\b", Severity.INFO),
    # ARP 缓存收集
    ("SEC-377", r"\barp\s+-a\b|\bip\s+neigh\b", Severity.INFO),
    # 主机名收集
    ("SEC-378", r"\bhostname\s*$|\bcat\s+/etc/hostname", Severity.INFO),
    # 日志敏感信息
    ("SEC-379", r"\bgrep\s+-i\s+.*(?:password|token)\s+/var/log", Severity.WARNING),
    # 临时文件侦察
    ("SEC-380", r"\bls\s+-la\s+/tmp|\bls\s+-la\s+/var/tmp", Severity.INFO),
    # 命令行历史转储
    ("SEC-381", r"\bcat\s+~?/\.bash_history\s*\|\s*base64", Severity.WARNING),
    # 凭据管道外传
    ("SEC-382", r"\bcat\s+/etc/shadow\s*\|\s*(?:nc|curl|scp)", Severity.ERROR),
    # 数据库凭据转储
    ("SEC-383", r"\bmysqldump\s+.*-p\S+|\bpg_dump\s+.*--password", Severity.WARNING),
    # 压缩源码外传
    ("SEC-384", r"\bzip2\s+-r\s+.*\s*\|\s*base64|\btar\s+-czf\s+.*\.git\s*\|\s*nc", Severity.WARNING),
    # 配置文件批量外传
    ("SEC-385", r"\b(?:tar|zip)\s+.*/etc\s*\|\s*(?:nc|curl|base64)", Severity.WARNING),
    # 恶意下载执行链
    ("SEC-386", r"\b(?:curl|wget)\s+.*\s*-o\s+\S+\s*&&\s*(?:bash|sh|chmod\s+\+x)", Severity.ERROR),
    # 凭据复用检测
    ("SEC-387", r"\bsshpass\s+-p\s+\S+\s+ssh|\bmysql\s+-u\s+root\s+-p\S+", Severity.WARNING),
    # 反向隧道建立
    ("SEC-388", r"\bssh\s+-R\s+\d+\s+\S+@\S+|\bssh\s+-NR\s+\d+", Severity.WARNING),
    # 隐蔽持久化
    ("SEC-389", r"\b(?:at|cron)\s+.*\s+2>/dev/null|\b(?:nohup|setsid)\s+.*\s+&\s*$", Severity.WARNING),
    # 恶意软件安装
    ("SEC-390", r"\b(?:apt|yum|dnf)\s+install\s+.*(?:netcat|ncat|socat|chisel)", Severity.WARNING),
    # 恶意脚本批量执行
    ("SEC-391", r"\bfor\s+\w+\s+in\s+.*;\s*do\s+.*\s*(?:curl|wget|nc)", Severity.WARNING),
    # 凭据环境变量覆盖
    ("SEC-392", r"\bexport\s+\w*(?:PASSWORD|PASSWD|APIKEY|APISECRET)\s*=", Severity.ERROR),
    # 隐蔽 DNS 外传
    ("SEC-393", r"\b(?:host|nslookup|dig)\s+[a-z0-9.-]{25,}\.", Severity.WARNING),
    # 命令混淆执行
    ("SEC-394", r"\b(?:eval|exec|source)\s+.*\$(?:[a-zA-Z0-9_]+|[^\s]+)", Severity.WARNING),
    # 日志清理
    ("SEC-395", r"\brm\s+-rf\s+(?:/var/log|\S*\.log)|\btruncate\s+-s\s+0\s+/var/log", Severity.WARNING),
    # 恶意代理设置
    ("SEC-396", r"\bexport\s+(?:http|https|all)_proxy\s*=\s*\S+@\S+", Severity.WARNING),
    # 供应链依赖替换
    ("SEC-397", r"\b(?:npm|pip|gem)\s+(?:install|add)\s+.*\s*--(?:registry|index-url)\s+\S+", Severity.WARNING),
    # 环境篡改检测
    ("SEC-398", r"\bexport\s+(?:LD_PRELOAD|LD_LIBRARY_PATH|PYTHONPATH|NODE_OPTIONS)\s*=", Severity.WARNING),
    # 恶意定时回连
    ("SEC-399", r"\b(?:crontab|at)\s+.*(?:curl|wget|nc)\s+\S+\s+\d+", Severity.WARNING),
    # 启动项注入
    ("SEC-400", r">>\s*/etc/rc.d/rc.local|>>\s*/etc/rc.local", Severity.ERROR),
    # 恶意容器创建
    ("SEC-401", r"\bdocker\s+run\s+[^\n]*-v\s+(?:/etc/passwd|/:/host)", Severity.WARNING),
    # 容器逃逸利用
    ("SEC-402", r"\bdocker\s+run\s+[^\n]*--privileged[^\n]*-v\s+/", Severity.ERROR),
    # 恶意镜像拉取
    ("SEC-403", r"\bdocker\s+pull\s+\S+/(?:backdoor|malware|evil)\b", Severity.WARNING),
    # 容器网络劫持
    ("SEC-404", r"\bdocker\s+network\s+connect\s+\S+\s+\S+", Severity.INFO),
    # 恶意注册表配置
    ("SEC-405", r"\bdocker\s+login\s+[^\n]*-p\s+\S+", Severity.WARNING),
    # Kubernetes 恶意部署
    ("SEC-406", r"\bkubectl\s+run\s+\S+\s+--image=\S+(?:backdoor|evil|malware)", Severity.WARNING),
    # K8s 特权容器
    ("SEC-407", r"\bkubectl\s+apply\s+[^\n]*privileged: true", Severity.WARNING),
    # K8s 密钥导出
    ("SEC-408", r"\bkubectl\s+get\s+secrets?\s+[^\n]*-o\s+(?:json|yaml)", Severity.WARNING),
    # Helm 恶意 chart
    ("SEC-409", r"\bhelm\s+install\s+\S+\s+\S+\s+--repo\s+\S*(?:evil|malware)\S*", Severity.WARNING),
    # K8s 权限提升
    ("SEC-410", r"\bkubectl\s+.*--as=cluster-admin|\bkubectl\s+.*--as=system:masters", Severity.WARNING),
    # 恶意云函数部署
    ("SEC-411", r"\b(?:serverless|sls)\s+deploy\s+[^\n]*(?:backdoor|evil)", Severity.WARNING),
    # 云凭据注入环境
    ("SEC-412", r"\bexport\s+(?:AWS_SECRET|AZURE_CLIENT_SECRET|GOOGLE_APPLICATION_CREDENTIALS)\s*=", Severity.ERROR),
    # 云资源删除
    ("SEC-413", r"\baws\s+(?:s3|ec2|rds)\s+delete\s+", Severity.WARNING),
    # 云安全组放开
    ("SEC-414", r"\baws\s+ec2\s+authorize-security-group-ingress\s+[^\n]*0\.0\.0\.0/0", Severity.WARNING),
    # 云存储公开
    ("SEC-415", r"\baws\s+s3api\s+put-bucket-acl\s+[^\n]*public-read", Severity.WARNING),
    # 恶意 CI 脚本注入
    ("SEC-416", r">>\s*(?:\.github/workflows/|\S*\.gitlab-ci\.yml|\S*\.circleci/config\.yml)", Severity.WARNING),
    # CI 凭据外传
    ("SEC-417", r"\b(?:curl|wget)\s+.*(?:\$|\$\{)(?:TOKEN|SECRET|PASSWORD)\b", Severity.WARNING),
    # 构建产物投毒
    ("SEC-418", r"\b(?:npm|pip|gem)\s+publish\s+[^\n]*-\s*(?:unsafe-perm|ignore-scripts)", Severity.WARNING),
    # 恶意代码注入源
    ("SEC-419", r"\b(?:curl|wget)\s+.*\s>>\s*\S+\.(?:py|js|sh|rb)", Severity.WARNING),
    # 依赖锁定绕过
    ("SEC-420", r"\b(?:npm|pip)\s+install\s+[^\n]*(?:--no-lockfile|--ignore-package-lock)", Severity.INFO),
    # 恶意脚本混淆执行
    ("SEC-421", r"\b(?:bash|sh)\s+-c\s+.*(?:base64|\\x[0-9a-f]{2})", Severity.WARNING),
    # 凭据文件 chmod
    ("SEC-422", r"\bchmod\s+777\s+~?/\.(?:ssh|aws|docker|gnupg)", Severity.WARNING),
    # 恶意安装脚本
    ("SEC-423", r"\b(?:curl|wget)\s+.*\|\s*sudo\s+(?:bash|sh|python)", Severity.ERROR),
    # 权限提升滥用
    ("SEC-424", r"\bsudo\s+(?:bash|sh|python|perl)\s+-c\s+", Severity.WARNING),
    # 隐蔽进程替换
    ("SEC-425", r"\bmv\s+\S+\s+/usr/bin/|\bcp\s+\S+\s+/usr/local/bin/", Severity.WARNING),
    # 恶意符号链接
    ("SEC-426", r"\bln\s+-s\s+/etc/passwd|\bln\s+-s\s+/etc/shadow", Severity.ERROR),
    # 隐蔽文件属性
    ("SEC-427", r"\bchattr\s+\+i\s+|\bchattr\s+\+a\s+", Severity.INFO),
    # 内核参数篡改
    ("SEC-428", r"\bsysctl\s+-w\s+.*(?:kernel|net)\.", Severity.INFO),
    # 服务配置替换
    ("SEC-429", r"\b(?:cp|mv)\s+\S+\s+/etc/systemd/system/", Severity.WARNING),
    # 用户添加后门
    ("SEC-430", r"\buseradd\s+.*-o\b|\buseradd\s+.*-u\s+0\b", Severity.ERROR),
    # 恶意别名注入
    ("SEC-431", r"\balias\s+\w+\s*=\s*(?:rm|shutdown|reboot|curl|wget)", Severity.WARNING),
    # 危险 PATH 前置
    ("SEC-432", r"\bPATH=\.:\$PATH|\bPATH=/tmp:\$PATH", Severity.WARNING),
    # 恶意函数覆盖
    ("SEC-433", r"\b(?:cd|ls|rm|cp|mv)\(\)\s*\{", Severity.WARNING),
    # 终端注入
    ("SEC-434", r"\b(?:echo|printf)\s+.*\x1b\[", Severity.INFO),
    # 恶意 trap
    ("SEC-435", r"\btrap\s+(?:rm|shutdown|curl|wget)", Severity.WARNING),
    # 恶意数据编码混淆
    ("SEC-436", r"\b(?:base64|xxd|hexdump)\s+-d\s+.*\|\s*(?:bash|sh)", Severity.WARNING),
    # 危险多行管道
    ("SEC-437", r"\b(?:cat|tail|head)\s+/etc/(?:passwd|shadow)\s*\|\s*(?:curl|nc)", Severity.ERROR),
    # 凭据云同步外传
    ("SEC-438", r"\b(?:aws|gcloud|az)\s+[^\n]*(?:s3|gs|blob)\s+cp\s+\S*(?:shadow|passwd|credential)", Severity.ERROR),
    # 恶意调试器
    ("SEC-439", r"\b(?:gdb|lldb)\s+[^\n]*-batch[^\n]*-c\s+[^\n]*(?:dump|attach)", Severity.WARNING),
    # 隐蔽网络扫描
    ("SEC-440", r"\b(?:nc|nmap)\s+[^\n]*(?:-sS|--scan-delay)\b", Severity.WARNING),
    # 恶意数据清理
    ("SEC-441", r"\brm\s+-rf\s+/|\brm\s+-rf\s+\*", Severity.ERROR),
    # 危险挂载覆盖
    ("SEC-442", r"\bmount\s+--bind\s+\S+\s+/|\bmount\s+-o\s+remount\s+rw\s+/", Severity.WARNING),
    # 恶意内核参数
    ("SEC-443", r"\b(?:echo|sysctl)\s+.*(?:/proc/sys/|kernel\.).*(?:hide|ignore)", Severity.INFO),
    # 磁盘擦除
    ("SEC-444", r"\bshred\s+.*(?:/dev/sd|/etc)|\bwipefs\s+.*/dev/sd", Severity.ERROR),
    # 恶意固件写入
    ("SEC-445", r"\bflashrom\s+-w\s+|\bdd\s+if=\S+\s+of=/dev/mtd", Severity.ERROR),
    # 恶意数据外发压缩
    ("SEC-446", r"\b(?:tar|zip|7z)\s+.*(?:/etc|/root|/home)\s*\|\s*(?:base64|nc|curl)", Severity.WARNING),
    # 凭据批量导出
    ("SEC-447", r"\b(?:cp|cat)\s+~?/\.(?:aws|ssh|docker)\S*\s+(?:/tmp|/var/tmp)", Severity.WARNING),
    # 恶意数据库复制
    ("SEC-448", r"\b(?:cp|rsync)\s+\S*\.(?:sqlite|db|sql)\s+\S+", Severity.INFO),
    # 危险凭据解密
    ("SEC-449", r"\b(?:openssl|gpg)\s+.*(?:-d|-decrypt)\s+.*\S+\.(?:key|pem|gpg)", Severity.WARNING),
    # 恶意文件传输链
    ("SEC-450", r"\b(?:curl|wget)\s+[^\n]*-O\s+\S+\s*&&\s*(?:nc|scp|ssh)", Severity.WARNING),
    # 恶意计划任务回连
    ("SEC-451", r"\b(?:crontab|at)\s+[^\n]*(?:curl|wget|nc)\s+\S+\s+\d+", Severity.WARNING),
    # 凭据复用 SSH 批量
    ("SEC-452", r"\bfor\s+\w+\s+in\s+.*;\s*do\s+ssh\s+\S+@\S+\s+\S+;\s*done", Severity.WARNING),
    # 恶意环境变量注入
    ("SEC-453", r"\bexport\s+(?:BASH_ENV|ENV|PROMPT_COMMAND)\s*=", Severity.WARNING),
    # 隐蔽下载器
    ("SEC-454", r"\b(?:curl|wget)\s+[^\n]*-o\s+\S+\.(?:tar\.gz|zip|rar)\b", Severity.WARNING),
    # 恶意自解压
    ("SEC-455", r"\b(?:unzip|tar)\s+.*\s-d\s+/|\bunzip2\s+.*\s-C\s+/", Severity.INFO),
    # 恶意网页抓取凭据
    ("SEC-456", r"\b(?:curl|wget)\s+[^\n]*(?:http|https)://[^\n]*(?:passwd|shadow|credential|secret)", Severity.ERROR),
    # 危险符号执行
    ("SEC-457", r"\bsudo\s+(?:rm|shutdown|mkfs|dd|shred)\s+", Severity.ERROR),
    # 恶意数据压缩外发
    ("SEC-458", r"\b(?:tar|zip|7z)\s+.*\s*(?:base64|openssl enc)\s*$", Severity.WARNING),
    # 危险磁盘操作
    ("SEC-459", r"\b(?:mkfs(?:\.\w+)?|fdisk|parted)\s+[^\n]*/dev/sd", Severity.ERROR),
    # 恶意内核模块编译
    ("SEC-460", r"\bmake\s+.*\s-C\s+/usr/src|\binsmod\s+.*\.ko\s*$", Severity.WARNING),
    # 恶意浏览器扩展安装
    ("SEC-461", r"\b(?:npm|npx)\s+install\s+.*(?:browser-extension|userscript)", Severity.WARNING),
    # 危险 screen 会话窃取
    ("SEC-462", r"\bscreen\s+-x\b|\bscreen\s+-r\s+\S+", Severity.WARNING),
    # 恶意共享库注入
    ("SEC-463", r"\b(?:cp|mv)\s+\S*\.so\s+/(?:lib|usr/lib|usr/local/lib)", Severity.WARNING),
    # 危险进程环境泄露
    ("SEC-464", r"\bcat\s+/proc/\d+/environ", Severity.WARNING),
    # 恶意命令历史清理
    ("SEC-465", r"\brm\s+-f\s+~?/\.(?:bash_history|zsh_history)", Severity.INFO),
    # 恶意邮件客户端配置
    ("SEC-466", r"\bcat\s+~?/\.msmtprc|\bcat\s+~?/\.mailrc", Severity.WARNING),
    # 浏览器自动填充窃取
    ("SEC-467", r"\bcat\s+~?/\.config/google-chrome/.*(?:Login|Web Data)", Severity.ERROR),
    # 恶意云配置导出
    ("SEC-468", r"\b(?:aws|az)\s+configure\s+[^\n]*(?:export|json|text)\s*$", Severity.INFO),
    # 危险会话文件窃取
    ("SEC-469", r"\bcat\s+~?/\.(?:bash_sessions|zsh_sessions)/", Severity.WARNING),
    # 恶意密钥环导出
    ("SEC-470", r"\bgpg\s+--export-secret-keys\s+\S+", Severity.ERROR),
    # 恶意容器逃逸利用
    ("SEC-471", r"\b(?:nsenter|setns)\s+--(?:mount|pid|net|uts|ipc)\s+/proc/\d+/ns/", Severity.ERROR),
    # 危险 cgroup 逃逸
    ("SEC-472", r"\bmkdir\s+/tmp/cgrp|\becho\s+\d+\s*>\s+/tmp/cgrp/cgroup\.procs", Severity.ERROR),
    # 恶意 eBPF 逃逸
    ("SEC-473", r"\b(?:bpftool|tc)\s+[^\n]*filter\s+add\s+[^\n]*(?:clsact|egress)", Severity.WARNING),
    # 危险运行时调试
    ("SEC-474", r"\bcrictl\s+exec\s+--privileged|\bctr\s+run\s+--privileged", Severity.WARNING),
    # 恶意容器镜像投毒
    ("SEC-475", r"\b(?:docker|podman)\s+build\s+[^\n]*(?:--network=host|--security-opt)", Severity.WARNING),
    # 恶意多架构下载
    ("SEC-476", r"\b(?:curl|wget)\s+[^\n]*(?:amd64|arm64|x86_64)\S*(?:tar|zip|bin)\b", Severity.INFO),
    # 危险内核模块强制加载
    ("SEC-477", r"\b(?:modprobe|insmod)\s+[^\n]*-f\b", Severity.WARNING),
    # 恶意固件回滚
    ("SEC-478", r"\b(?:fwupdmgr|fwupd)\s+(?:downgrade|reinstall)\s+", Severity.WARNING),
    # 危险 ACPI 操作
    ("SEC-479", r"\b(?:acpid|systemctl)\s+.*\s+acpid\.service", Severity.INFO),
    # 恶意 TPM 操作
    ("SEC-480", r"\b(?:tpm2_clear|tpm2_evictcontrol)\s+", Severity.WARNING),
    # 恶意系统备份外传
    ("SEC-481", r"\b(?:tar|zip|rsync)\s+[^\n]*(?:/etc|/home|/root)\s+[^\n]*(?:nc|curl|scp)", Severity.WARNING),
    # 危险 LVM 操作
    ("SEC-482", r"\b(?:lvremove|lvcreate)\s+[^\n]*/dev/\S*vg\S*/", Severity.ERROR),
    # 恶意 RAID 破坏
    ("SEC-483", r"\bmdadm\s+--(?:stop|zero-superblock|fail)\s+", Severity.ERROR),
    # 危险交换分区泄露
    ("SEC-484", r"\bstrings\s+/dev/|\bcat\s+/proc/swaps", Severity.INFO),
    # 恶意系统还原
    ("SEC-485", r"\b(?:restic|borg|timeshift)\s+restore\s+", Severity.INFO),
    # 恶意引导修复绕过
    ("SEC-486", r"\bgrub\s+set\s+root|\bgrub\s+insmod\s+", Severity.WARNING),
    # 危险 UEFI 安全启动禁用
    ("SEC-487", r"\b(?:efibootmgr|sbctl)\s+[^\n]*(?:--uninstall|--disable|remove)", Severity.WARNING),
    # 恶意内核命令行
    ("SEC-488", r"\b(?:grubby|kernel-install)\s+[^\n]*(?:--add-kernel|--args)", Severity.WARNING),
    # 危险 dracut 重建
    ("SEC-489", r"\bdracut\s+[^\n]*-f\b|\binitramfs\s+-u\b", Severity.INFO),
    # 恶意 kexec 加载
    ("SEC-490", r"\bkexec\s+-l\s+\S+", Severity.WARNING),
    # 恶意 systemd 计时器
    ("SEC-491", r"\b(?:systemd-run|systemctl)\s+[^\n]*--on-calendar|\b(?:systemd-run|systemctl)\s+[^\n]*--timer", Severity.WARNING),
    # 危险审计禁用
    ("SEC-492", r"\bauditctl\s+-e\s+0|\bauditctl\s+-D\b", Severity.WARNING),
    # 恶意 SELinux 上下文
    ("SEC-493", r"\bchcon\s+[^\n]*-t\s+[^\n]*(?:httpd|bin)|\brestorecon\s+[^\n]*-F\b", Severity.WARNING),
    # 危险命名空间操作
    ("SEC-494", r"\bip\s+netns\s+delete|\bunshare\s+--user\b", Severity.WARNING),
    # 恶意 CPU 限制绕过
    ("SEC-495", r"\bschedtool\s+.*\s-R\b|\brenice\s+-n\s+-20\b", Severity.INFO),
    # 恶意 IoT 设备控制
    ("SEC-496", r"\b(?:mosquitto_pub|mqtt)\s+[^\n]*-t\s+\S+\s+-m\s+", Severity.INFO),
    # 危险网络设备配置
    ("SEC-497", r"\b(?:ip|tc)\s+link\s+set\s+\S+\s+(?:down|up)\b", Severity.INFO),
    # 恶意多播发现
    ("SEC-498", r"\b(?:avahi-browse|mdns-scan|zmap)\s+", Severity.WARNING),
    # 危险串口操作
    ("SEC-499", r"\b(?:stty|screen)\s+.*\s/dev/tty\S*|\bcat\s+</dev/ttyS0", Severity.WARNING),
    # 恶意 USB 设备操作
    ("SEC-500", r"\b(?:dmesg|lsusb)\s+[^\n]*\|\s*grep\s+.*usb|\busbhid\s+-d\s+", Severity.INFO),
    # 恶意数据混淆执行
    ("SEC-501", r"\b(?:echo|printf)\s+.*\|\s*(?:base64|xxd)\s+-d\s*\|\s*(?:bash|sh|python)", Severity.WARNING),
    # 危险自定义协议隧道
    ("SEC-502", r"\b(?:socat|nc)\s+[^\n]*(?:UDP|TCP):\S+:\d+", Severity.WARNING),
    # 恶意别名持久化
    ("SEC-503", r"\becho\s+.*alias\s+.*>>\s*~?/\.(?:bashrc|zshrc)", Severity.WARNING),
    # 危险 chroot 逃逸
    ("SEC-504", r"\bchroot\s+\S+\s+/bin/sh|\bchroot\s+\S+\s+/bin/bash", Severity.ERROR),
    # 恶意环境清理
    ("SEC-505", r"\benv\s+-i\s+|\bexec\s+env\s+-i\s+", Severity.INFO),
    # 恶意 AI 模型数据投毒
    ("SEC-506", r"\b(?:pip|conda)\s+install\s+.*\S*(?:torch|tensorflow|transformers)\S*\s*$", Severity.WARNING),
    # 危险 ML 凭据
    ("SEC-507", r"\bexport\s+(?:HF_TOKEN|OPENAI_API_KEY|WANDB_API_KEY)\s*=", Severity.ERROR),
    # 恶意向量库操作
    ("SEC-508", r"\b(?:chroma|qdrant|weaviate)\s+[^\n]*delete\s+", Severity.WARNING),
    # 危险训练数据窃取
    ("SEC-509", r"\b(?:cat|tar)\s+.*\S*(?:dataset|train|labels)\S*\.(?:jsonl|csv|parquet)\s*$", Severity.WARNING),
    # 恶意推理缓存投毒
    ("SEC-510", r"\b(?:rm|mv)\s+.*\S*(?:cache|prompt_cache|kv_cache)", Severity.WARNING),
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
