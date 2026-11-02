#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""对照运行实例两个数据源统计 jf-zh-runtime.js 词典覆盖率：
  /api/v1/charts    —— 单图表视图的标题/分组
  /api/v1/contexts  —— 指标树(SPA 深链 Metrics 页)的数据源，标题集合与 charts 不相交！
两者都必须 100%（by-design 例外：设备名/协议名/产品名/插件路径）。
用法: check-coverage.py <实例基址，如 http://127.0.0.1:19999> [jf-zh-runtime.js 路径]
"""
import json, re, sys, urllib.request

js = open(sys.argv[2] if len(sys.argv) > 2 else '/data1/jf-repack/tools/jf-zh-runtime.js', encoding='utf-8').read()

def parse_obj(name):
    m = re.search(r'var %s = \{(.*?)\n  \};' % name, js, re.S)
    if not m:
        m = re.search(r'var %s = \{(.*)\};' % name, js, re.S)
    body = m.group(1)
    return dict(re.findall(r'"((?:[^"\\]|\\.)*)"\s*:\s*"((?:[^"\\]|\\.)*)"', body))

D = parse_obj('D')
FAM = parse_obj('FAM')
# 规则体允许出现转义斜杠 \/；非贪婪到 "/,'" 为止
RULES = []
for pat, rep in re.findall(r"\[/(.*?)/,\s*'([^']*)'\]", js):
    RULES.append((re.compile(pat), rep.replace('$1', r'\1')))

def tr_base(s):
    if s in D:
        return D[s]
    for rx, rep in RULES:
        if rx.search(s):
            return rx.sub(rep, s)
    return None

def tr_title(s):
    r = tr_base(s)
    if r is not None:
        return r
    i = s.rfind(' (')
    if i > 0 and s.endswith(')'):
        r = tr_base(s[:i])
        if r is not None:
            return True  # 已译（值不重要）
    return None

base = sys.argv[1].rstrip('/')
report = []

for ep, getter in [
    ('/api/v1/charts', lambda d: d.get('charts', {}).items()),
    ('/api/v1/contexts', lambda d: d.get('contexts', {}).items()),
]:
    url = base + ep
    try:
        data = json.load(urllib.request.urlopen(url, timeout=20))
    except Exception as e:
        report.append(f'[{ep}] 拉取失败: {e}')
        continue
    total = miss = 0
    missing = {}
    fams = {}
    for _k, ch in getter(data):
        t = ch.get('title', '')
        total += 1
        if tr_title(t) is None:
            miss += 1
            missing[t] = missing.get(t, 0) + 1
        f = ch.get('family', '')
        if f and f not in FAM:
            fams[f] = fams.get(f, 0) + 1
    report.append(f'[{ep}] 条目 {total}  已译 {total-miss}  未译 {miss}  覆盖率 {100*(total-miss)/max(total,1):.1f}%')
    for t, n in sorted(missing.items(), key=lambda x: -x[1]):
        report.append(f'    {n:3d}×  {t}')
    report.append(f'    未译 family（分组名）: {len(fams)} 种: ' + ', '.join(sorted(fams)[:30]))

print('\n'.join(report))
