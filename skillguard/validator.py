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
