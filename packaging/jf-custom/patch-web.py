#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch-web.py —— Netdata v2.12.x dashboard 成品资源补丁器（品牌化 + 中文化 + 去云化）

对解包后的 usr/share/netdata/web/ 目录做三类补丁：
  1. 去云化：按官方 local-agent.html 的本地模式语义改写入口页
     （UI 包本地加载、关闭 PostHog 追踪、isLocal 直进看板跳过登录/认领）
  2. 品牌化：<title>、favicon.ico、netdata.svg 主 logo
  3. 中文化：按 zh-dict.csv 对 *.js/*.html 做字符串替换
  4. 运行时脚本：安装 v3/jf-zh-runtime.js（隐藏登录/AI Insights 按钮 +
     fetch 钩子翻译 agent 返回的图表标题/分组名），并注入各入口 HTML

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

# 去营销/动态标题补丁（对所有 *.js/*.html 全树字节替换，与词典同一 Walker）。
# 每个 0 命中都会在报告里预警（上游改版信号）。
MARKETING_PATCHES = [
    # JS 启动后的动态标题会盖掉品牌 <title>：
    #   document.title = data.hostname + ': Netdata Agent Console'
    (': Netdata Agent Console', ': 机房监控中心'),
    # GTM 营销标签。换成空载荷 data:/about:，不发起任何外联请求、控制台无 404 噪音；
    # GTM 一死其运行时注入的像素/对比站（facebook/reo/g2）全部消失。
    # 用裸域名前缀形态：同时覆盖整串 URL 写法与 minify 拼接写法（'...gtm.js?id='+i）
    ('https://www.googletagmanager.com/gtm.js', 'data:text/javascript,'),
    ('https://www.googletagmanager.com/ns.html', 'about:blank'),
    # 云端状态页外链（升级提示横幅上的 "Check status page" 按钮）
    ('https://status.netdata.cloud', 'about:blank'),
    # nightly(v2.12.0-375+) 新增的 v2.12.2 安全升级营销横幅：把版本门槛判断短路成 false。
    # v2.12.1 发布包无此模块，0 命中属预期（升级由我们自己的 jf 包管，不劳云端提醒）。
    ('return!!t&&(n&&t===b?', 'return!1&&(n&&t===b?'),
    # nightly 上 reo.dev 营销像素是独立的 <script> 标签（v2.12.1 里由 GTM 运行时注入，
    # GTM 一死即灭；nightly 需单独断链）。前缀对：URL 变成空载荷 data: URL，不发任何请求。
    ('https://static.reo.dev', 'data:text/javascript,'),
    # 云端注册表 iframe（registry-access.html，向 netdata 云上报/同步看板 GUID）。
    # 两种写法：字面量 URL（老写法）与运行时拼接 `data.registry + "/registry-access.html?x="`
    # （入口 HTML 内联脚本，host 来自 agent 的 registry 配置）。内网无云，全部断链。
    ('https://registry.my-netdata.io', 'about:blank#'),
    ('data.registry + "/registry-access.html?x="', '"about:blank#registry?x="'),
    # 云端 API 直连（本地模式下 UI 仍会调 accounts/me、license、channel、
    # user_agent_node_access 等；内网这些请求挂起会拖慢首屏，直连是云依赖）。
    # 指向本机未监听端口：连接即刻被拒（等价内网 DNS 失败但更快），URL 形态合法。
    ('https://app.netdata.cloud', 'https://127.0.0.1:2'),
    # Sentry 错误/会话上报（前端遥测，会把含内部主机名的报错发往 sentry.io）。
    # 两种形态：API 字面量与 DSN（https://<key>@o382276.../5210883，key 在前缀，
    # 前缀对罩不住，需单独配对；指向本机未监听端口保持 DSN 可解析、传输即刻失败）
    ('https://o382276.ingest.sentry.io', 'https://127.0.0.1:2'),
    ('@o382276.ingest.sentry.io/5210883', '@127.0.0.1:2/5210883'),
]

# 参与补丁的入口 HTML（相对 web 目录）
ENTRY_HTML = ['index.html', 'v3/index.html', 'v3/agent.html', 'v3/local-agent.html']

# sw.js 中和桩：安装即跳过等待、激活即清空全部缓存并注销自身。
# 原版 workbox SW 预缓存 876 个资源（含 index.html/chunk），而我们的补丁同名改内容、
# sw.js 字节不变 → 浏览器永不触发 SW 更新 → 升级后一直用旧界面。内网部署不需要离线缓存，直接废掉。
SW_STUB = '''/* JF 定制：禁用 dashboard service worker 预缓存。
   本文件安装后即清空全部缓存并注销自身，浏览器此后始终直连 agent 取最新界面。 */
self.addEventListener('install', function () { self.skipWaiting(); });
self.addEventListener('activate', function (e) {
  e.waitUntil((async function () {
    var keys = await caches.keys();
    await Promise.all(keys.map(function (k) { return caches.delete(k); }));
    await self.registration.unregister();
  })());
});
'''


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


def patch_string_pairs(web_dir, pairs, report, header):
    """对 web 目录下所有 *.js / *.html 应用 (old,new) 字节替换
    （不含 .map / LICENSE / 运行时脚本）。词典与去营销补丁共用本 Walker。"""
    counts = {old: 0 for old, _ in pairs}
    files_changed = 0
    for root, _dirs, files in os.walk(web_dir):
        for fn in files:
            if not (fn.endswith('.js') or fn.endswith('.html')):
                continue
            if fn.endswith('.LICENSE.txt') or fn.endswith('.map'):
                continue
            if fn == 'jf-zh-runtime.js':
                continue  # 自己装的中文化运行时脚本，不许被改动
            path = os.path.join(root, fn)
            try:
                data = open(path, encoding='utf-8').read()
            except UnicodeDecodeError:
                try:
                    data = open(path, encoding='utf-8', errors='replace').read()
                except OSError:
                    continue
            orig = data
            for old, new in pairs:
                if old in data:
                    counts[old] += data.count(old)
                    data = data.replace(old, new)
            if data != orig:
                open(path, 'w', encoding='utf-8').write(data)
                files_changed += 1
    total = sum(counts.values())
    report.append(f'[INFO] {header}：共 {total} 处，涉及 {files_changed} 个文件，条目 {len(pairs)} 条')
    zero = [old for old, c in counts.items() if c == 0]
    if zero:
        report.append(f'[WARN] {header} 0 命中 {len(zero)} 条（上游改版或锚点失效，需复核）:')
        for old in zero:
            report.append(f'        0-hit: {old}')
    return counts


def patch_dict_strings(web_dir, entries, report):
    """词典替换（zh-dict.tsv 条目）"""
    return patch_string_pairs(web_dir, entries, report, '词典替换')


def neutralize_sw(web_dir, report):
    """用自注销桩替换 v3/sw.js：浏览器检测到 sw.js 字节变化 → 触发更新 →
    新 SW 激活时清空旧预缓存并注销。老访客自动痊愈，此后界面升级不再被 SW 卡住。"""
    path = os.path.join(web_dir, 'v3', 'sw.js')
    if not os.path.exists(path):
        report.append('[WARN] v3/sw.js 不存在（上游改版？），跳过 SW 中和')
        return
    cur = open(path, encoding='utf-8', errors='replace').read()
    if 'JF 定制：禁用 dashboard service worker' in cur:
        report.append('[SKIP] v3/sw.js 已是中和桩')
        return
    open(path, 'w', encoding='utf-8').write(SW_STUB)
    report.append(f'[OK] v3/sw.js 置换为自注销桩 ({os.path.getsize(path)}B，原 {len(cur)}B)')


def install_runtime(web_dir, runtime_src, report):
    """安装 v3/jf-zh-runtime.js 并注入 <script> 到各入口 HTML。

    在词典 pass 之后调用（脚本自身不做词典替换）；
    幂等：HTML 中已有引用则只做路径形态校正。

    ★ 必须用绝对路径 /v3/jf-zh-runtime.js：SPA 深链（如 /spaces/ly/rooms/local/overview）
    由 agent 以同一张 index.html 应答，相对 src 会解析到 /spaces/.../v3/… → 404，
    整个运行时脚本不执行（按钮不隐藏、图表标题不翻译）。绝对路径对根入口、
    /v3/ 入口与任意深链一律正确（netdata 总在源站根下提供 web）。
    """
    if not runtime_src or not os.path.exists(runtime_src):
        report.append(f'[WARN] 运行时脚本缺失 ({runtime_src})，跳过注入')
        return
    dst = os.path.join(web_dir, 'v3', 'jf-zh-runtime.js')
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copyfile(runtime_src, dst)
    report.append(f'[OK] v3/jf-zh-runtime.js 安装 ({os.path.getsize(dst)}B)')
    tag = '<script src="/v3/jf-zh-runtime.js"></script>'
    for rel in ENTRY_HTML:
        path = os.path.join(web_dir, rel)
        if not os.path.exists(path):
            continue
        data = open(path, encoding='utf-8').read()
        if tag in data:
            report.append(f'[SKIP] {rel}: 运行时脚本已是绝对路径引用')
            continue
        if 'jf-zh-runtime.js' in data:  # 旧相对路径 → 迁移
            data = data.replace('<script src="v3/jf-zh-runtime.js"></script>', tag)
            data = data.replace('<script src="jf-zh-runtime.js"></script>', tag)
            if tag in data:
                open(path, 'w', encoding='utf-8').write(data)
                report.append(f'[FIX] {rel}: 相对路径引用 → /v3/jf-zh-runtime.js（深链 404 修复）')
            else:
                report.append(f'[WARN] {rel}: 存在 jf-zh-runtime.js 引用但形态未知，需人工检查')
            continue
        if '</title>' in data:
            data = data.replace('</title>', '</title>' + tag, 1)
        elif '<head>' in data:
            data = data.replace('<head>', '<head>' + tag, 1)
        else:
            report.append(f'[WARN] {rel}: 找不到注入锚点（无 </title>/<head>）')
            continue
        open(path, 'w', encoding='utf-8').write(data)
        report.append(f'[OK] {rel}: 注入 {tag}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--web-dir', required=True, help='解包后的 usr/share/netdata/web 目录')
    ap.add_argument('--dict', default=None, help='zh-dict.csv 路径')
    ap.add_argument('--assets', default=None, help='brand-assets 目录')
    ap.add_argument('--brand-name', default='机房监控中心')
    ap.add_argument('--runtime', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'jf-zh-runtime.js'),
                    help='jf-zh-runtime.js 路径（默认取本工具同目录）')
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
    patch_string_pairs(web_dir, MARKETING_PATCHES, report, '去营销/动态标题补丁')
    neutralize_sw(web_dir, report)
    install_runtime(web_dir, args.runtime, report)

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
