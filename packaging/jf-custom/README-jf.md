# jf-custom —— Netdata v2.12.1 机房监控定制重打包工具链

对官方 Netdata 静态安装包（`.gz.run`）做**品牌化 + 界面中文化 + 去云化离线加固**的重打包流水线。
不重编译 agent，二进制与官方包完全一致（已 md5 逐文件核对），风险最小。

## 定制内容

| 类别 | 内容 |
|---|---|
| 品牌化 | `<title>` → 机房监控中心；favicon.ico；主 logo（netdata.svg ← brand-assets/logo.svg）；安装器 label |
| 中文化 | `zh-dict.tsv` 词典对 dashboard v3 成品 JS/HTML 做字符串替换（v1 覆盖主导航/告警/节点/常用操作约 200 词条） |
| 去云化 UI | 入口页改为官方 local-agent.html 的本地模式语义：UI 包本地加载（不访 app.netdata.cloud）、`isLocal:true` 直进看板（跳过登录/认领向导）、关闭 PostHog 行为追踪并置空 token |
| 去云化配置 | 内置遥测退出标记 `.opt-out-from-anonymous-statistics`；`netdata.conf` 禁用 agent 自动更新；updater 脚本置换为离线桩 |

## 用法

```bash
# x86_64
bash repack.sh /path/netdata-x86_64-v2.12.1.gz.run /path/netdata-x86_64-v2.12.1-jf1.gz.run [工作目录]
# aarch64
bash repack.sh /path/netdata-aarch64-v2.12.1.gz.run /path/netdata-aarch64-v2.12.1-jf1.gz.run [工作目录]

# 自定义品牌名
BRAND="某某监控" bash repack.sh ...
```

产物在指定输出路径；补丁报告在 `<工作目录>/patch-report.txt`（含逐词条命中数与 0 命中告警）。

## 文件说明

- `repack.sh` —— 流水线入口：切 makeself 头/负载 → 解包 → 打补丁 → gzip -9 重打包 → 重算 `MD5/CRCsum/filesizes/totalsize` 头字段 → 拼回 `.run`
- `patch-web.py` —— web 资源补丁器（去云化 + 品牌 + 词典），幂等，可单独用于快速迭代：
  `python3 patch-web.py --web-dir <运行实例的web目录> --dict zh-dict.tsv --assets brand-assets`
- `zh-dict.tsv` —— 中英词典（TSV）。规则见文件头注释；**单词必须带属性锚点**（`title:"Nodes"` 这种），严禁裸替换单词（会撞功能代码，如 `"Home"` 是键盘 key 判断）
- `patch-conf.sh` —— 配置层加固（遥测标记/netdata.conf/updater 桩）
- `brand-assets/` —— 品牌素材（logo.svg、fav32.png 生成 favicon.ico 等），换素材后重跑即可

## 维护指南

- **升级到新版本 Netdata**：下载对应官方 `.gz.run` → 重跑 repack.sh → 看 patch-report 的 `[WARN] 未找到字段`（上游改版信号）和 `0-hit 词条`（词典失效）→ 修词典再跑。
- **补翻译**：浏览器看到英文 → 在 zh-dict.tsv 加一行（单词记得带锚点）→ 对运行实例直接跑 patch-web.py 刷新 → 浏览器强刷验证 → 满意后重打包。
- **service worker 缓存**：dashboard v3 带 sw.js，升级/换包后浏览器可能拿到旧界面，需强刷（Ctrl+Shift+R）或清站点数据。
- **web 资源与架构无关**：x86_64 与 aarch64 包共用同一套补丁，两架构各跑一次 repack 即可。
- 词典命中报告里 `>X<` 形式的词条只作用于 HTML 文本节点。

## 已知边界

- 图表内部小节名（如 "System Overview" 菜单里的 context 分组名）来自 agent 数据（C 侧生成），不在本词典覆盖范围；如需中文化要改 agent 源码（后续源码构建线）。
- 云功能入口被 isLocal 本地模式关闭，但部分云相关文案仍在 chunk 中（已翻译而非删除）。
