#!/bin/bash
# patch-conf.sh —— 包内配置层去云化/离线加固（作用于解包后的包树根目录）
# 用法: patch-conf.sh <包树根目录>   （目录内含 ./etc ./usr 等官方包结构）
set -euo pipefail

TREE="${1:?用法: patch-conf.sh <解包后的包树根目录>}"

[ -d "$TREE/etc/netdata" ] || { echo "错误: $TREE/etc/netdata 不存在（包树结构不对？）" >&2; exit 1; }

# 1) 匿名遥测退出标记（官方机制：/etc/netdata/.opt-out-from-anonymous-statistics，
#    静态安装时 /etc/netdata 软链到 /opt/netdata/etc/netdata，故放进包树即可）
touch "$TREE/etc/netdata/.opt-out-from-anonymous-statistics"
echo "[OK] 遥测退出标记: etc/netdata/.opt-out-from-anonymous-statistics"

# 2) 禁用 agent 自动更新（静态包默认"安装但不启用"updater，这里配置层再加一道）
if [ ! -f "$TREE/etc/netdata/netdata.conf" ]; then
  cat > "$TREE/etc/netdata/netdata.conf" <<'EOF'
# 机房监控定制版默认配置（netdata.conf 缺省项均走内置默认值）
# 如需调整: /opt/netdata/etc/netdata/edit-config netdata.conf
[agent_update]
    enable = no
EOF
  echo "[OK] 写入 etc/netdata/netdata.conf（agent_update 禁用）"
else
  echo "[SKIP] netdata.conf 已存在，未改动"
fi

# 3) 禁用云端注册表（agent 默认向 registry.my-netdata.io 注册/同步看板 GUID，
#    浏览器侧会起隐藏 iframe 上报 hostname+machine_guid；内网去云化直接关闭。
#    幂等追加：仅当 netdata.conf 尚无 [registry] 段时补写）
CONF="$TREE/etc/netdata/netdata.conf"
if ! grep -q '^\[registry\]' "$CONF" 2>/dev/null; then
  cat >> "$CONF" <<'EOF'

# JF 定制：内网部署禁用云端注册表（去云化）
[registry]
    enabled = no
EOF
  echo "[OK] netdata.conf 追加 [registry] enabled = no"
else
  echo "[SKIP] netdata.conf 已有 [registry] 段"
fi

# 4) updater 脚本置换为退出 0 的桩（防御纵深：即使被 cron/timer 意外启用也不出网）
UPDATER="$TREE/usr/libexec/netdata/netdata-updater.sh"
if [ -f "$UPDATER" ]; then
  cat > "$UPDATER" <<'EOF'
#!/bin/bash
# JF 定制版：内网部署禁用在线自动更新。
# 如需升级，请使用官方/定制离线安装包手动执行。
echo "netdata-updater: disabled by JF custom build (offline deployment)" >&2
exit 0
EOF
  chmod +x "$UPDATER"
  echo "[OK] updater 已置换为离线桩: usr/libexec/netdata/netdata-updater.sh"
else
  echo "[WARN] 未找到 $UPDATER（静态包结构变化？）"
fi
