#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch-web.py —— Netdata v2.12.x dashboard 成品资源补丁器（品牌化 + 中文化 + 去云化）

对解包后的 usr/share/netdata/web/ 目录做三类补丁：
  1. 去云化：按官方 local-agent.html 的本地模式语义改写入口页
     （UI 包本地加载、关闭 PostHog 追踪、isLocal 直进看板跳过登录/认领）
  2. 品牌化：<title>、favicon.ico、netdata.svg 主 logo
  3. 中文化：按 zh-dict.csv 对 *.js/*.html 做字符串替换

特性：幂等（重复执行报告 already patched）；输出逐条替换计数报告；
      词典按长度降序应用（防 "cpu cores" 被 "cpu core" 先替换）。

用法:
  patch-web.py --web-dir <path> [--dict zh-dict.csv] [--assets brand-assets] \
               [--brand-name 机房监控中心] [--report report.txt]
"""
import argparse
import io
import os
import shutil
import sys

# 入口页去云化补丁（old → new）。语义来源：官方自带的 v3/local-agent.html
DE_CLOUD_PATCHES = [
    ('webpackPublicPath: "https://app.netdata.cloud" || (getBasename() + "/v3")',
     'webpackPublicPath: "" || (getBasename() + "/v3")'),
    ('tracking: !false', 'tracking: !true'),
    ('isLocal: false', 'isLocal: true'),
    # 追踪已关，再把 token 置空做双保险（空串为假值，posthog 不会初始化）
    ('posthogToken: "phc_hnhlqe6D2Q4IcQNrFItaqdXJAxQ8RcHkPAFAp74pubv"',
     'posthogToken: ""'),
]

# 参与补丁的入口 HTML（相对 web 目录）
ENTRY_HTML = ['index.html', 'v3/index.html', 'v3/agent.html', 'v3/local-agent.html']


def patch_entry_html(web_dir, brand_name, report):
    """入口页：去云化 + 标题品牌化"""
    title_old = '<title>Netdata</title>'
    title_new = f'<title>{brand_name}</title>'
    for rel in ENTRY_HTML:
        path = os.path.join(web_dir, rel)
        if not os.path.exists(path):
            report.append(f'[WARN] 入口页缺失: {rel}')
            continue
        data = open(path, encoding='utf-8').read()
        changed = False
        # 标题
        if title_old in data:
            data = data.replace(title_old, title_new)
            report.append(f'[OK] {rel}: <title> → {brand_name}')
            changed = True
        elif title_new in data:
            report.append(f'[SKIP] {rel}: 标题已品牌化')
        # 去云化字段
        for old, new in DE_CLOUD_PATCHES:
            if old in data:
                data = data.replace(old, new)
                report.append(f'[OK] {rel}: 去云化 {old.split(":")[0]}')
                changed = True
            elif new in data:
                report.append(f'[SKIP] {rel}: 已是本地模式 ({new.split(":")[0]})')
            else:
                report.append(f'[WARN] {rel}: 未找到字段 {old.split(":")[0]}（上游改版？）')
        if changed:
            open(path, 'w', encoding='utf-8').write(data)


def patch_assets(web_dir, assets_dir, report):
    """品牌素材：favicon.ico（由 fav32.png 生成）与主 logo netdata.svg"""
    if not assets_dir or not os.path.isdir(assets_dir):
        report.append('[WARN] 未提供 brand-assets 目录，跳过素材替换')
        return
    # favicon.ico
    fav_png = os.path.join(assets_dir, 'fav32.png')
    fav_ico = os.path.join(web_dir, 'v3', 'favicon.ico')
    if os.path.exists(fav_png) and os.path.exists(fav_ico):
        try:
            from PIL import Image
            img = Image.open(fav_png).convert('RGBA')
            img.save(fav_ico, format='ICO', sizes=[(16, 16), (32, 32), (48, 48)])
            report.append('[OK] v3/favicon.ico ← fav32.png (ICO 16/32/48)')
        except ImportError:
            report.append('[WARN] 无 PIL，直接复制 png 为 .ico（浏览器兼容性稍差）')
            shutil.copyfile(fav_png, fav_ico)
    else:
        report.append(f'[WARN] favicon 素材缺失 ({fav_png} 或 {fav_ico})')
    # 主 logo
    logo_src = os.path.join(assets_dir, 'logo.svg')
    logo_dst = os.path.join(web_dir, 'v3', 'static', 'img', 'logos', 'netdata.svg')
    if os.path.exists(logo_src) and os.path.exists(logo_dst):
        shutil.copyfile(logo_src, logo_dst)
        report.append('[OK] v3/static/img/logos/netdata.svg ← brand logo.svg')
    else:
        report.append(f'[WARN] logo 素材缺失 ({logo_src} 或 {logo_dst})')


def load_dict(dict_path):
    """TSV: en<TAB>zh 每行一条。en 可含锚点前缀（如 title:"Nodes"），原样字节替换。"""
    entries = []
    with open(dict_path, encoding='utf-8-sig') as f:
        for line in f:
            line = line.rstrip('\n')
            if not line or line.lstrip().startswith('#'):
                continue
            if '\t' not in line:
                continue
            en, zh = line.split('\t', 1)
            en, zh = en.strip(), zh.strip()
            if en and zh:
                entries.append((en, zh))
    # 长的先替换，避免子串先被吃掉
    entries.sort(key=lambda e: len(e[0]), reverse=True)
    return entries


def patch_dict_strings(web_dir, entries, report):
    """对 web 目录下所有 *.js / *.html 应用词典（不含 .map / LICENSE）"""
    counts = {en: 0 for en, _ in entries}
    files_changed = 0
    for root, _dirs, files in os.walk(web_dir):
        for fn in files:
            if not (fn.endswith('.js') or fn.endswith('.html')):
                continue
            if fn.endswith('.LICENSE.txt') or fn.endswith('.map'):
                continue
            path = os.path.join(root, fn)
            try:
                data = open(path, encoding='utf-8').read()
            except UnicodeDecodeError:
                try:
                    data = open(path, encoding='utf-8', errors='replace').read()
                except OSError:
                    continue
            orig = data
            for en, zh in entries:
                if en in data:
                    n = data.count(en)
                    data = data.replace(en, zh)
                    counts[en] += n
            if data != orig:
                open(path, 'w', encoding='utf-8').write(data)
                files_changed += 1
    total = sum(counts.values())
    report.append(f'[INFO] 词典替换：共 {total} 处，涉及 {files_changed} 个文件，词条 {len(entries)} 条')
    zero = [en for en, c in counts.items() if c == 0]
    if zero:
        report.append(f'[WARN] 0 命中词条 {len(zero)} 条（上游改版或锚点失效，需复核）:')
        for en in zero:
            report.append(f'        0-hit: {en}')
    return counts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--web-dir', required=True, help='解包后的 usr/share/netdata/web 目录')
    ap.add_argument('--dict', default=None, help='zh-dict.csv 路径')
    ap.add_argument('--assets', default=None, help='brand-assets 目录')
    ap.add_argument('--brand-name', default='机房监控中心')
    ap.add_argument('--report', default=None, help='报告输出文件')
    args = ap.parse_args()

    web_dir = os.path.abspath(args.web_dir)
    if not os.path.isdir(web_dir):
        sys.exit(f'web 目录不存在: {web_dir}')

    report = [f'=== patch-web 报告 ({web_dir}) ===']
    patch_entry_html(web_dir, args.brand_name, report)
    patch_assets(web_dir, args.assets, report)
    counts = {}
    if args.dict and os.path.exists(args.dict):
        entries = load_dict(args.dict)
        counts = patch_dict_strings(web_dir, entries, report)
    else:
        report.append('[WARN] 未提供词典，跳过中文化')

    text = '\n'.join(report)
    print(text)
    if args.report:
        with io.open(args.report, 'w', encoding='utf-8') as f:
            f.write(text + '\n')
            if counts:
                f.write('\n=== 词条命中明细 ===\n')
                for en, zh in sorted(entries, key=lambda e: -counts.get(e[0], 0)):
                    f.write(f'{counts.get(en, 0):4d}  {en}  →  {zh}\n')


if __name__ == '__main__':
    main()
