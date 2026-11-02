#!/bin/bash
# repack.sh —— Netdata 官方静态包(.gz.run) 定制重打包流水线
#
# 流程: 切开 makeself 头/负载 → 解包 → patch-web.py + patch-conf.sh →
#       重新 gzip tar → 重算 MD5/CRCsum/filesizes/totalsize + 品牌化 label → 拼回 .run
#
# 用法: repack.sh <官方netdata-*.gz.run> <输出.run> [工作目录]
# 环境变量:
#   BRAND  品牌名（默认 机房监控中心）
#   KEEP_WORK=1 保留工作目录（默认保留，便于排查/快速迭代）
set -euo pipefail

SRC_RUN="${1:?用法: repack.sh <官方.run> <输出.run> [工作目录]}"
OUT_RUN="${2:?用法: repack.sh <官方.run> <输出.run> [工作目录]}"
WORK="${3:-/data1/jf-repack/work/repack-$(date +%s)}"
TOOLS="$(cd "$(dirname "$0")" && pwd)"
BRAND="${BRAND:-机房监控中心}"

mkdir -p "$WORK"
SKIP=$(grep -a -m1 -oP '(?<=^skip=")[0-9]+' "$SRC_RUN")
[ -n "$SKIP" ] || { echo "错误: 在 $SRC_RUN 中找不到 makeself skip 行" >&2; exit 1; }
HEAD_BYTES=$(head -n "$SKIP" "$SRC_RUN" | wc -c)

HEADER="$WORK/header.sh"
PAYLOAD="$WORK/payload-official.tar.gz"
TREE="$WORK/tree"
NEWPAY="$WORK/payload-custom.tar.gz"

echo "== 1/6 切包 (skip=$SKIP, header=${HEAD_BYTES}B) =="
head -n "$SKIP" "$SRC_RUN" > "$HEADER"
tail -c +$((HEAD_BYTES + 1)) "$SRC_RUN" > "$PAYLOAD"

echo "== 2/6 解包 =="
rm -rf "$TREE"; mkdir -p "$TREE"
tar xzf "$PAYLOAD" -C "$TREE"

echo "== 3/6 web 补丁（品牌化+中文化+去云化） =="
python3 "$TOOLS/patch-web.py" \
  --web-dir "$TREE/usr/share/netdata/web" \
  --dict "$TOOLS/zh-dict.tsv" \
  --assets "$TOOLS/brand-assets" \
  --brand-name "$BRAND" \
  --report "$WORK/patch-report.txt"

echo "== 4/6 配置补丁（遥测退出/禁自动更新） =="
bash "$TOOLS/patch-conf.sh" "$TREE"

echo "== 5/6 重打包 tar（gzip -9, root/root） =="
tar cf - --owner=root --group=root -C "$TREE" . | gzip -9 > "$NEWPAY"
SIZE=$(stat -c %s "$NEWPAY")
MD5=$(md5sum "$NEWPAY" | cut -d' ' -f1)
CRC=$(cksum "$NEWPAY" | awk '{print $1}')
sed -i -E \
  -e "s/^filesizes=\"[0-9]+\"/filesizes=\"$SIZE\"/" \
  -e "s/^totalsize=\"[0-9]+\"/totalsize=\"$SIZE\"/" \
  -e "s/^MD5=\"[0-9a-f]*\"/MD5=\"$MD5\"/" \
  -e "s/^CRCsum=\"[0-9]+\"/CRCsum=\"$CRC\"/" \
  -e "s/^label=\"[^\"]*\"/label=\"$BRAND 安装程序\"/" \
  "$HEADER"
grep -E '^(label|filesizes|totalsize|MD5|CRCsum)=' "$HEADER"

echo "== 6/6 拼装 .run =="
cat "$HEADER" "$NEWPAY" > "$OUT_RUN"
chmod +x "$OUT_RUN"
echo "完成: $OUT_RUN  (payload $((SIZE/1024/1024))MB)"
echo "报告: $WORK/patch-report.txt   工作目录: $WORK"
