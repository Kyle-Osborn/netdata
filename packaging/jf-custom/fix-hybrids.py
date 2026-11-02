#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fix-hybrids.py —— 修复旧版短词条在内长串内部替换产生的中英混血标题。
用于已累积打过补丁的 web 树（如宿主机就地补丁路径）；
全新重打包走 zh-dict.tsv 的完整原文词条，无需本脚本。
用法: fix-hybrids.py --web-dir <path>
"""
import argparse
import os
import re

PAIRS = [
    ("Top Nodes by 内存使用", "内存使用最高的节点"),
    ("Top Nodes by 磁盘空间", "磁盘空间使用最高的节点"),
    ("Top Nodes by 网络流量", "网络流量最高的节点"),
    ("Top Hosts by 内存使用", "内存使用最高的主机"),
    ("Top Containers by 内存使用", "内存使用最高的容器"),
    ("Top Containers by 网络流量", "网络流量最高的容器"),
    ("Top Devices by 网络流量", "网络流量最高的设备"),
    ("Top Mounts by 磁盘空间", "磁盘空间使用最高的挂载点"),
    ("Top CPU 核数 by Interrupts", "中断最多的 CPU 核心"),
    ("Top CPU 核数 by Softirqs", "软中断最多的 CPU 核心"),
    ("Top CPU 核数 by Softnets", "收包软处理最多的 CPU 核心"),
    ("Top CPU 核数 by Utilisation", "使用率最高的 CPU 核心"),
    ("Free 磁盘空间", "剩余磁盘空间"),
    ("Maximum 内存使用", "最大内存使用"),
    ("Maximum Unallocated Physical 磁盘空间", "最大未分配物理磁盘空间"),
    ("Total 网络流量", "网络总流量"),
    ("Top Partitions by 磁盘空间", "磁盘空间使用最高的分区"),
    ("Top Namespaces by 网络流量", "网络流量最高的命名空间"),
    ("Top VMs by 内存使用", "内存使用最高的虚拟机"),
    ("Total Live 磁盘空间 Used", "在线磁盘已用空间总量"),
    ("Total 磁盘空间 Consumed", "已占用磁盘空间总量"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--web-dir', required=True)
    args = ap.parse_args()
    web = args.web_dir
    total = files = 0
    for root, _d, fs in os.walk(web):
        for fn in fs:
            if not fn.endswith(('.js', '.html')) or fn.endswith(('.map', '.LICENSE.txt')):
                continue
            p = os.path.join(root, fn)
            try:
                s = open(p, encoding='utf-8').read()
            except UnicodeDecodeError:
                continue
            o = s
            n = 0
            for a, b in PAIRS:
                if a in s:
                    n += s.count(a)
                    s = s.replace(a, b)
            if s != o:
                open(p, 'w', encoding='utf-8').write(s)
                total += n
                files += 1
    print(f"混血修复: {total} 处, {files} 个文件")
    left = 0
    for root, _d, fs in os.walk(web):
        for fn in fs:
            if not fn.endswith('.js'):
                continue
            s = open(os.path.join(root, fn), encoding='utf-8', errors='replace').read()
            for m in re.finditer(r'title:"[A-Za-z][^"]*[一-鿿][^"]*"', s):
                t = m.group(0)
                if 'Netdata' not in t and 'CPU' not in t and 'PCIe' not in t \
                        and 'Intel' not in t and 'IPv' not in t and 'TCP' not in t \
                        and 'DNS' not in t and 'UPS' not in t and 'Docker' not in t \
                        and 'Agent' not in t and 'Slab' not in t and 'API' not in t \
                        and 'I/O' not in t and 'NTP' not in t and 'NFS' not in t \
                        and 'PSI' not in t and 'KSM' not in t and 'BAR1' not in t \
                        and 'Nginx' not in t and 'Apache' not in t and 'MySQL' not in t \
                        and 'Postgres' not in t and 'RAPL' not in t and 'IOPS' not in t:
                    print('残留:', t[:70])
                    left += 1
    print(f"残留混血 title: {left}")


if __name__ == '__main__':
    main()
