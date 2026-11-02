# jf-custom —— Netdata v2.12.1 机房监控定制重打包工具链

对官方 Netdata 静态安装包（`.gz.run`）做**品牌化 + 界面中文化 + 去云化离线加固**的重打包流水线。
不重编译 agent，二进制与官方包完全一致（已 md5 逐文件核对），风险最小。

## 定制内容

| 类别 | 内容 |
|---|---|
| 品牌化 | `<title>` → 机房监控中心；favicon.ico；主 logo（netdata.svg ← brand-assets/logo.svg）；安装器 label |
| 中文化（静态） | `zh-dict.tsv` 词典对 dashboard v3 成品 JS/HTML 做字符串替换（v1 覆盖主导航/告警/节点/常用操作约 200 词条） |
| 中文化（运行时） | `v3/jf-zh-runtime.js` 注入各入口页：① 隐藏登录与 AI Insights 按钮（CSS）；② fetch 钩子把 agent API（/api/v1/charts、/api/v1/contexts、/api/v3/q）返回的英文图表标题/分组成员名按词典译成中文（标题 "Base (chart-id)" 译基础名保留 chart id） |
| 去云化 UI | 入口页改为官方 local-agent.html 的本地模式语义：UI 包本地加载（不访 app.netdata.cloud）、`isLocal:true` 直进看板（跳过登录/认领向导）、关闭 PostHog 行为追踪并置空 token |
| 去云化配置 | 内置遥测退出标记 `.opt-out-from-anonymous-statistics`；`netdata.conf` 禁用 agent 自动更新；updater 脚本置换为离线桩 |

## 用法

```bash
# x86_64
bash repack.sh /path/netdata-x86_64-v2.12.1.gz.run /path/netdata-x86_64-v2.12.1-jf2.gz.run [工作目录]
# aarch64
bash repack.sh /path/netdata-aarch64-v2.12.1.gz.run /path/netdata-aarch64-v2.12.1-jf2.gz.run [工作目录]

# 自定义品牌名
BRAND="某某监控" bash repack.sh ...
```

产物在指定输出路径；补丁报告在 `<工作目录>/patch-report.txt`（含逐词条命中数与 0 命中告警）。

## 文件说明

- `repack.sh` —— 流水线入口：切 makeself 头/负载 → 解包 → 打补丁 → gzip -9 重打包 → 重算 `MD5/CRCsum/filesizes/totalsize` 头字段 → 拼回 `.run`
- `patch-web.py` —— web 资源补丁器（去云化 + 品牌 + 静态词典 + 运行时脚本注入），幂等，可单独用于快速迭代：
  `python3 patch-web.py --web-dir <运行实例的web目录> --dict zh-dict.tsv --assets brand-assets`
- `zh-dict.tsv` —— 中英词典（TSV）。规则见文件头注释；**单词必须带属性锚点**（`title:"Nodes"` 这种），严禁裸替换单词（会撞功能代码，如 `"Home"` 是键盘 key 判断）
- `jf-zh-runtime.js` —— 运行时脚本（隐藏云入口按钮 + agent 数据标题翻译），装到 `v3/jf-zh-runtime.js` 并注入各入口 HTML。agent 侧词典就维护在本文件的 `D`（标题/标签）与 `FAM`（分组）对象里；`RULES` 是前缀规则（Job Manager 内部指标模式翻译）
- `patch-conf.sh` —— 配置层加固（遥测标记/netdata.conf/updater 桩）
- `brand-assets/` —— 品牌素材（logo.svg、fav32.png 生成 favicon.ico 等），换素材后重跑即可

## 维护指南

- **升级到新版本 Netdata**：下载对应官方 `.gz.run` → 重跑 repack.sh → 看 patch-report 的 `[WARN] 未找到字段`（上游改版信号）和 `0-hit 词条`（词典失效）→ 修词典再跑。
- **补翻译**：浏览器看到英文 → 先分清来源：
  - 界面按钮/菜单文案 → 在 zh-dict.tsv 加一行（单词记得带锚点）；
  - 图表标题/分组成员名（Metrics 树里的英文，来自 agent API 数据）→ 在 jf-zh-runtime.js 的 `D`/`FAM` 里加词条；
  然后对运行实例直接跑 patch-web.py 刷新 → 浏览器强刷验证 → 满意后重打包。
- **验证运行时翻译**：`node test-jfzh.mjs`（如有）或浏览器直接看 Metrics 树；翻译是浏览器侧 fetch 钩子，curl API 看到的仍是英文（正常）。
- **service worker 缓存**：dashboard v3 带 sw.js，升级/换包后浏览器可能拿到旧界面，需强刷（Ctrl+Shift+R）或清站点数据。
- **web 资源与架构无关**：x86_64 与 aarch64 包共用同一套补丁，两架构各跑一次 repack 即可。
- 词典命中报告里 `>X<` 形式的词条只作用于 HTML 文本节点。

## 已知边界

- 运行时翻译只译 agent 返回数据中的 `title`/`label`/`family` 三个**值**字段（display 层安全：dashboard 只按 context/chart id 查询，family 只用于客户端树形分组）；设备名（eth0/sda/nvme0n1）、插件内部路径（ChartEngine/*、Agent/JobMgr/*）、纯技术缩写（TCP SYN Cookie）有意保留英文。
- 个别维度名/单位（如 %、KB/s）保持原样，不翻译。
- 云功能入口被 isLocal 本地模式关闭，但部分云相关文案仍在 chunk 中（已翻译而非删除）。
