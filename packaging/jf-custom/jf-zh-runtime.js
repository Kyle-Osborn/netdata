/* jf-zh-runtime.js —— 机房监控定制运行时脚本
 * 1) 隐藏云入口按钮（登录 / AI Insights）
 * 2) fetch 钩子：把 agent 返回的英文图表标题/分组成员名按词典翻译（标题形如 "Base (chart-id)"，
 *    译基础名、保留括号内的 chart id）
 * 由 patch-web.py 注入到各入口 HTML；词典直接维护在本文件 D / FAM 两个对象里。
 */
(function () {
  'use strict';

  /* ---------- 1. 隐藏云入口按钮 ---------- */
  var css = ''
    + '[data-testid="sign-in-dropdown"]{display:none!important}'
    + '[data-testid="userControl-signInRow"]{display:none!important}'
    + '[data-ga="click-sign-in::header"]{display:none!important}'
    + '[data-testid="viewPicker-insights"]{display:none!important}'
    + '[data-ga="view-picker::click-view-insights::global-view"]{display:none!important}';
  try {
    var st = document.createElement('style');
    st.textContent = css;
    (document.head || document.documentElement).appendChild(st);
  } catch (e) { /* ignore */ }

  /* ---------- 2. agent 侧词典 ---------- */
  var D = {
    /* 传感器/温度 */
    "Sensor Temperature": "传感器温度",
    "Sensor Temperature Alarm Status": "传感器温度告警状态",
    "Temperature Sensors Distribution": "温度传感器分布",
    /* CPU / 系统 */
    "Total CPU utilization": "CPU 总使用率",
    "CPU Idle Jitter": "CPU 空闲抖动",
    "CPU Interrupts": "CPU 中断",
    "CPU Context Switches": "CPU 上下文切换",
    "Current CPU Frequency": "当前 CPU 频率",
    "System Uptime": "系统运行时长",
    "System Load Average": "系统平均负载",
    "System Active Processes": "系统活跃进程",
    "System Processes": "系统进程",
    "System Processes State": "系统进程状态",
    "Started Processes": "已启动进程",
    "System softirqs": "系统软中断",
    "System softnet_stat": "软网络统计",
    "File Descriptors": "文件描述符",
    "File Descriptors Utilization": "文件描述符使用率",
    "Available Entropy": "可用熵",
    "CPU some pressure": "CPU 部分压力",
    "CPU some pressure stall time": "CPU 部分压力停滞时间",
    /* 内存 */
    "System RAM": "系统内存",
    "Available RAM for applications": "应用可用内存",
    "System Swap": "交换分区",
    "Swap I/O": "交换分区 I/O",
    "Swap Memory Cached in RAM": "内存缓存的交换页",
    "Memory Paged from/to disk": "内存与磁盘换页",
    "Memory Page Faults": "内存缺页",
    "Out of Memory Kills": "OOM 终止次数",
    "Out of Memory Protection": "OOM 防护",
    "Committed (Allocated) Memory": "已提交（分配）内存",
    "Writeback Memory": "回写内存",
    "Memory Used by Kernel": "内核占用内存",
    "Reclaimable Kernel Memory": "可回收内核内存",
    "Transparent HugePages Memory": "透明大页内存",
    "Details of Transparent HugePages Usage": "透明大页使用详情",
    "Transparent Huge Page Fault Allocations": "透明大页缺页分配",
    "Transparent Huge Page File Allocations": "透明大页文件分配",
    "Transparent Huge Zero Page Allocations": "透明大零页分配",
    "Transparent Huge Pages Collapsed by khugepaged": "khugepaged 合并的透明大页",
    "Transparent Huge Page Splits": "透明大页拆分",
    "Transparent Huge Pages Swap Out": "透明大页换出",
    "Transparent Huge Pages Compaction": "透明大页整理",
    "Memory Reclaiming": "内存回收",
    "Direct Memory Mappings": "直接内存映射",
    "Memory Ballooning Operations": "内存气泡操作",
    "Corrupted Memory, detected by ECC": "ECC 检测到的坏内存",
    "Memory some pressure": "内存部分压力",
    "Memory some pressure stall time": "内存部分压力停滞时间",
    "Memory full pressure": "内存完全压力",
    "Memory full pressure stall time": "内存完全压力停滞时间",
    "I/O some pressure": "I/O 部分压力",
    "I/O some pressure stall time": "I/O 部分压力停滞时间",
    "I/O full pressure": "I/O 完全压力",
    "I/O full pressure stall time": "I/O 完全压力停滞时间",
    /* 磁盘 */
    "Disk I/O": "磁盘 I/O",
    "Disk I/O Bandwidth": "磁盘 I/O 带宽",
    "Disk Space Usage": "磁盘空间使用",
    "Disk Files (inodes) Usage": "磁盘文件（inode）使用",
    "Disk Completed I/O Operations": "磁盘已完成 I/O 操作",
    "Disk Completed Extended I/O Operations": "磁盘已完成扩展 I/O 操作",
    "Disk Current I/O Operations": "磁盘当前 I/O 操作",
    "Disk Backlog": "磁盘积压",
    "Disk Busy Time": "磁盘繁忙时间",
    "Disk Utilization Time": "磁盘使用时间",
    "Disk Merged Operations": "磁盘合并操作",
    "Disk Merged Discard Operations": "磁盘合并丢弃操作",
    "Disk Total I/O Time": "磁盘总 I/O 时间",
    "Disk Total I/O Time for Extended Operations": "扩展操作磁盘总 I/O 时间",
    "Average Completed I/O Operation Time": "平均单次 I/O 耗时",
    "Average Completed Extended I/O Operation Time": "平均单次扩展 I/O 耗时",
    "Average Completed I/O Operation Bandwidth": "平均单次 I/O 带宽",
    "Average Service Time": "平均服务时间",
    "Amount of Discarded Data": "丢弃数据量",
    "Average Amount of Discarded Data": "平均丢弃数据量",
    /* 网络 */
    "Physical Network Interfaces Aggregated Bandwidth": "物理网口聚合带宽",
    "Bandwidth": "带宽",
    "Packets": "数据包",
    "Interface Errors": "网卡错误",
    "Interface Drops": "网卡丢包",
    "Interface FIFO Buffer Errors": "网卡 FIFO 缓冲错误",
    "Interface Operational State": "网卡工作状态",
    "Interface Physical Link State": "网卡物理链路状态",
    "Interface MTU": "网卡 MTU",
    "Network Interface Events": "网卡事件",
    "IPv4 Bandwidth": "IPv4 带宽",
    "IPv4 Packets": "IPv4 数据包",
    "IPv4 Errors": "IPv4 错误",
    "IPv4 Fragments Sent": "IPv4 分片发送",
    "IPv4 Fragments Reassembly": "IPv4 分片重组",
    "IPv4 Broadcast Bandwidth": "IPv4 广播带宽",
    "IPv4 Broadcast Packets": "IPv4 广播数据包",
    "IPv4 Multicast Packets": "IPv4 组播数据包",
    "IP Multicast Bandwidth": "IP 组播带宽",
    "IPv4 ECN Statistics": "IPv4 ECN 统计",
    "IPv4 ICMP Packets": "IPv4 ICMP 数据包",
    "IPv4 ICMP Errors": "IPv4 ICMP 错误",
    "IPv4 ICMP Messages": "IPv4 ICMP 消息",
    "IPv4 TCP Packets": "IPv4 TCP 数据包",
    "IPv4 TCP Errors": "IPv4 TCP 错误",
    "IPv4 TCP Opens": "IPv4 TCP 连接建立",
    "IPv4 TCP Handshake Issues": "IPv4 TCP 握手问题",
    "IPv4 UDP Packets": "IPv4 UDP 数据包",
    "IPv4 UDP Errors": "IPv4 UDP 错误",
    "IPv4 UDPLite Packets": "IPv4 UDPLite 数据包",
    "IPv4 UDPLite Errors": "IPv4 UDPLite 错误",
    "IPv6 Bandwidth": "IPv6 带宽",
    "IPv6 Packets": "IPv6 数据包",
    "IPv6 Fragments Sent": "IPv6 分片发送",
    "IPv6 Fragments Reassembly": "IPv6 分片重组",
    "IPv6 Errors": "IPv6 错误",
    "IPv6 UDP Packets": "IPv6 UDP 数据包",
    "IPv6 UDP Errors": "IPv6 UDP 错误",
    "IPv6 UDPlite Packets": "IPv6 UDPLite 数据包",
    "IPv6 UDP Lite Errors": "IPv6 UDPLite 错误",
    "IPv6 Multicast Bandwidth": "IPv6 组播带宽",
    "IPv6 Broadcast Bandwidth": "IPv6 广播带宽",
    "IPv6 Broadcast Packets": "IPv6 广播数据包",
    "IPv6 Multicast Packets": "IPv6 组播数据包",
    "IPv6 ICMP Messages": "IPv6 ICMP 消息",
    "IPv6 ICMP Redirects": "IPv6 ICMP 重定向",
    "IPv6 ICMP Errors": "IPv6 ICMP 错误",
    "IPv6 ICMP Echo": "IPv6 ICMP 回显",
    "IPv6 ICMP Group Membership": "IPv6 ICMP 组成员",
    "IPv6 Router Messages": "IPv6 路由器消息",
    "IPv6 Neighbor Messages": "IPv6 邻居消息",
    "IPv6 ICMP MLDv2 Reports": "IPv6 ICMP MLDv2 报告",
    "IPv6 ICMP Types": "IPv6 ICMP 类型",
    "IPv6 ECT Packets": "IPv6 ECT 数据包",
    "TCP Connections": "TCP 连接",
    "TCP Memory Pressures": "TCP 内存压力",
    "TCP Connection Aborts": "TCP 连接中断",
    "TCP Reordered Packets by Detection Method": "TCP 乱序包（按检测方式）",
    "TCP Out-Of-Order Queue": "TCP 乱序队列",
    "TCP SYN Cookies": "TCP SYN Cookie",
    "TCP SYN Queue Issues": "TCP SYN 队列问题",
    "TCP Accept Queue Issues": "TCP Accept 队列问题",
    "Sockets used for all address families": "全部协议族套接字",
    "TCP Sockets": "TCP 套接字",
    "TCP Sockets Memory": "TCP 套接字内存",
    "IPv4 UDP Sockets": "IPv4 UDP 套接字",
    "IPv4 UDP Sockets Memory": "IPv4 UDP 套接字内存",
    "IPv4 UDPLITE Sockets": "IPv4 UDPLITE 套接字",
    "IPv4 RAW Sockets": "IPv4 RAW 套接字",
    "IPv4 FRAG Sockets": "IPv4 FRAG 套接字",
    "IPv4 FRAG Sockets Memory": "IPv4 FRAG 套接字内存",
    "IPv6 TCP Sockets": "IPv6 TCP 套接字",
    "IPv6 UDP Sockets": "IPv6 UDP 套接字",
    "IPv6 UDPLITE Sockets": "IPv6 UDPLITE 套接字",
    "IPv6 RAW Sockets": "IPv6 RAW 套接字",
    "IPv6 FRAG Sockets": "IPv6 FRAG 套接字",
    "Connection Tracker Connections": "连接跟踪连接数",
    "Connection Tracker New Connections": "连接跟踪新建连接",
    "Connection Tracker Changes": "连接跟踪变更",
    "Connection Tracker Searches": "连接跟踪查找",
    "Connection Tracker Errors": "连接跟踪错误",
    "Connection Tracker Expectations": "连接跟踪期望连接",
    /* IPC / 时钟 */
    "IPC Semaphore Arrays": "IPC 信号量数组",
    "IPC Semaphores": "IPC 信号量",
    "IPC Shared Memory Number of Segments": "IPC 共享内存段数",
    "IPC Shared Memory Used Bytes": "IPC 共享内存用量",
    "System Clock Synchronization State": "系统时钟同步状态",
    "System Clock Status": "系统时钟状态",
    "Computed Time Offset Between Local System and Reference Clock": "与参考时钟的偏差",
    /* 应用组（apps） */
    "Applications Groups CPU utilization (100% = 1 core)": "应用组 CPU 使用率（100%=1核）",
    "Applications Groups memory usage without shared": "应用组内存使用（不含共享）",
    "Applications Groups CPU context switches": "应用组 CPU 上下文切换",
    "Applications Groups memory RSS usage": "应用组 RSS 内存",
    "Applications Groups virtual memory size": "应用组虚拟内存",
    "Applications Groups memory page faults": "应用组内存缺页",
    "Applications Groups swap usage": "应用组交换分区使用",
    "Applications Groups disk physical IO": "应用组磁盘物理 I/O",
    "Applications Groups disk logical IO": "应用组磁盘逻辑 I/O",
    "Applications Groups processes": "应用组进程数",
    "Applications Groups threads": "应用组线程数",
    "Applications Groups open file descriptors limit": "应用组文件描述符上限",
    "Applications Groups open files descriptors": "应用组已打开文件描述符",
    "Applications Groups uptime": "应用组运行时长",
    "User CPU utilization (100% = 1 core)": "用户 CPU 使用率（100%=1核）",
    "User memory usage without shared": "用户内存使用（不含共享）",
    "User CPU context switches": "用户 CPU 上下文切换",
    "User memory RSS usage": "用户 RSS 内存",
    "User virtual memory size": "用户虚拟内存",
    "User memory page faults": "用户内存缺页",
    "User swap usage": "用户交换分区使用",
    "User disk physical IO": "用户磁盘物理 I/O",
    "User disk logical IO": "用户磁盘逻辑 I/O",
    "User processes": "用户进程数",
    "User threads": "用户线程数",
    "User open file descriptors limit": "用户文件描述符上限",
    "User open files descriptors": "用户已打开文件描述符",
    "User uptime": "用户运行时长",
    "User Group CPU utilization (100% = 1 core)": "用户组 CPU 使用率（100%=1核）",
    "User Group memory usage without shared": "用户组内存使用（不含共享）",
    "User Group CPU context switches": "用户组 CPU 上下文切换",
    "User Group memory RSS usage": "用户组 RSS 内存",
    "User Group virtual memory size": "用户组虚拟内存",
    "User Group memory page faults": "用户组内存缺页",
    "User Group swap usage": "用户组交换分区使用",
    "User Group disk physical IO": "用户组磁盘物理 I/O",
    "User Group disk logical IO": "用户组磁盘逻辑 I/O",
    "User Group processes": "用户组进程数",
    "User Group threads": "用户组线程数",
    "User Group open file descriptors limit": "用户组文件描述符上限",
    "User Group open files descriptors": "用户组已打开文件描述符",
    "User Group uptime": "用户组运行时长",
    /* Netdata 自身 */
    "Netdata CPU usage": "Netdata CPU 使用",
    "Netdata uptime": "Netdata 运行时长",
    "Netdata Memory": "Netdata 内存",
    "Netdata Memory Buffers": "Netdata 内存缓冲",
    "Netdata Web API Clients": "Web API 客户端数",
    "Netdata Web API Requests Received": "Web API 请求数",
    "Netdata Web API Response Time": "Web API 响应时间",
    "Netdata Time-Series DB Queries": "时序数据库查询数",
    "Netdata Time-Series DB Samples Read": "时序数据库读取样本数",
    "Netdata Time-Series Collected Samples": "已采集时序样本数",
    "Netdata Time-Series Points Generated": "已生成时序数据点",
    "Netdata Network Traffic": "Netdata 网络流量",
    "Machine learning status": "机器学习状态",
    "Dimensions by metric type": "按指标类型统计维度",
    "Training status of dimensions": "维度训练状态",
    "Anomaly detection dimensions": "异常检测维度",
    "ML running": "ML 运行状态",
    "Percentage of anomalous dimensions": "异常维度占比",
    "Percentage of anomalous dimensions by context": "按上下文统计异常维度占比",
    "Anomaly detection events": "异常检测事件",
    "Training queue operations": "训练队列操作",
    "Training queue size": "训练队列长度",
    "Training time stats": "训练耗时统计",
    "Training results": "训练结果",
    "dbengine space and time retention": "dbengine 空间与时间留存",
    /* agent 内部（ChartEngine / 构建管线） */
    "Build phase duration in seconds": "构建阶段耗时（秒）",
    "BuildPlan duration in seconds": "BuildPlan 耗时（秒）",
    "Planner actions by kind": "规划器动作数（按类型）",
    "Failed BuildPlan calls": "BuildPlan 失败调用数",
    "Successful BuildPlan calls": "BuildPlan 成功调用数",
    "BuildPlan calls skipped due failed collect cycle": "因采集失败跳过的 BuildPlan 调用数",
    "1 when build sequence monotonicity is currently violated": "构建序列单调性被破坏时为 1",
    "Chart instances in the latest successful build rollup": "最近成功构建的图表实例数",
    "Inferred dimensions in the latest successful build rollup": "最近成功构建的推断维度数",
    "Route cache entries in the latest successful build rollup": "最近成功构建的路由缓存条目数",
    "Route cache lookup hits": "路由缓存命中数",
    "Route cache lookup misses": "路由缓存未命中数",
    "Route cache entries pruned": "已清理的路由缓存条目数",
    "Route cache entries retained after prune": "清理后保留的路由缓存条目数",
    "Route cache full-drop prune events": "路由缓存满丢弃清理事件数",
    "Series scanned by planner": "规划器扫描的序列数",
    "Series matched by template or autogen": "模板/自动生成匹配的序列数",
    "Series matched by autogen fallback": "自动生成回退匹配的序列数",
    "Series left unmatched after routing": "路由后仍未匹配的序列数",
    /* apps / 网络视图插件内部 IPC */
    "Apps Plugin CPU": "Apps 插件 CPU 使用",
    "Apps Plugin Files": "Apps 插件文件",
    "Apps Plugin APPS_LOOKUP Server Requests": "Apps 插件 APPS_LOOKUP 服务端请求数",
    "Apps Plugin APPS_LOOKUP Server Request Duration": "Apps 插件 APPS_LOOKUP 服务端请求耗时",
    "Apps Plugin CGROUPS_LOOKUP Client Requests": "Apps 插件 CGROUPS_LOOKUP 客户端请求数",
    "Apps Plugin CGROUPS_LOOKUP Client Cache": "Apps 插件 CGROUPS_LOOKUP 客户端缓存",
    "Apps Plugin CGROUPS_LOOKUP Client Peer": "Apps 插件 CGROUPS_LOOKUP 客户端对端",
    "Apps Plugin CGROUPS_LOOKUP Client Request Duration": "Apps 插件 CGROUPS_LOOKUP 客户端请求耗时",
    "Apps Plugin CGROUPS_LOOKUP Client Queue Depth": "Apps 插件 CGROUPS_LOOKUP 客户端队列深度",
    "CGROUPS_LOOKUP Server Requests": "CGROUPS_LOOKUP 服务端请求数",
    "CGROUPS_LOOKUP Server Request Duration Histogram": "CGROUPS_LOOKUP 服务端请求耗时分布",
    "Network Viewer APPS_LOOKUP Client Requests": "网络视图插件 APPS_LOOKUP 请求数",
    "Network Viewer APPS_LOOKUP Client Cache": "网络视图插件 APPS_LOOKUP 缓存",
    "Network Viewer APPS_LOOKUP Client Peer": "网络视图插件 APPS_LOOKUP 对端",
    "Network Viewer APPS_LOOKUP Worker Request Duration": "网络视图插件 APPS_LOOKUP 工作耗时",
    "Network Viewer APPS_LOOKUP Function Handler Overhead": "网络视图插件 APPS_LOOKUP 函数处理开销",
    "Network Viewer APPS_LOOKUP Intake Depth": "网络视图插件 APPS_LOOKUP 接入队列深度",
    "cgroups Discovery Scans": "cgroups 发现扫描次数",
    "SNMP topology internal devices": "SNMP 拓扑设备数",
    "SNMP topology internal last refresh": "SNMP 拓扑最近刷新时间",
    "SNMP topology internal refreshes": "SNMP 拓扑刷新次数",
    "Data Collection Status": "数据采集状态",
    "Data Collection Duration": "数据采集耗时",
    "Metrics in the netdata statsd database": "statsd 数据库指标数",
    "Useful metrics in the netdata statsd database": "statsd 有效指标数",
    "Events processed by the netdata statsd server": "statsd 处理事件数",
    "Read operations made by the netdata statsd server": "statsd 读操作数",
    "Bytes read by the netdata statsd server": "statsd 读取字节数",
    "Network packets processed by the netdata statsd server": "statsd 处理网络包数",
    "statsd server TCP connects and disconnects": "statsd TCP 连接与断开",
    "statsd server TCP connected sockets": "statsd TCP 已连接套接字",
    "Private metric charts created by the netdata statsd server": "statsd 私有指标图数",
    /* 维度标签（常见） */
    "used": "已用",
    "free": "可用",
    "available": "可用",
    "cached": "缓存",
    "buffers": "缓冲",
    "total": "合计",
    "incoming": "入站",
    "outgoing": "出站",
    "received": "接收",
    "sent": "发送",
    "reads": "读",
    "writes": "写"
  };

  /* 分组（family）白名单：只译人读的显示名，设备名与 id 型不译 */
  var FAM = {
    "CPU usage": "CPU 使用",
    "Memory Usage": "内存使用",
    "Network Traffic": "网络流量",
    "Temperature": "温度",
    "OOM kills": "OOM 终止",
    "Uptime": "运行时长",
    "clock synchronization": "时钟同步",
    "conntrack": "连接跟踪",
    "page faults": "缺页",
    "machine learning": "机器学习",
    "ipc semaphores": "IPC 信号量",
    "ipc shared memory": "IPC 共享内存",
    "dbengine retention": "dbengine 留存",
    "Data Collection Samples": "采集样本",
    "Time-Series Queries": "时序查询",
    "Internal": "内部",
    "utilization": "使用率",
    "processes": "进程",
    "softirqs": "软中断",
    "sockets": "套接字",
    "hugepages": "大页内存",
    "entropy": "熵",
    "writeback": "回写",
    "reclaiming": "内存回收",
    "interrupts": "中断",
    "idlejitter": "空闲抖动",
    "cpufreq": "CPU 频率",
    "overview": "总览",
    /* 常用 id 型族（v6 与 v4 不能译成同值，否则树里两组合并） */
    "cpu": "CPU",
    "mem": "内存",
    "ram": "内存",
    "swap": "交换分区",
    "load": "负载",
    "disk": "磁盘",
    "io": "I/O",
    "fds": "文件描述符",
    "files": "文件",
    "kernel": "内核",
    "slab": "Slab 内存",
    "ipc": "IPC",
    "ecc": "ECC",
    "ecn": "ECN",
    "icmp": "ICMP",
    "icmp6": "ICMP(v6)",
    "tcp": "TCP",
    "tcp6": "TCP(v6)",
    "udp": "UDP",
    "udp6": "UDP(v6)",
    "udplite": "UDPLite",
    "udplite6": "UDPLite(v6)",
    "raw": "RAW",
    "raw6": "RAW(v6)",
    "fragments": "分片",
    "fragments6": "分片(v6)",
    "multicast": "组播",
    "multicast6": "组播(v6)",
    "broadcast": "广播",
    "broadcast6": "广播(v6)",
    "packets": "数据包",
    "errors": "错误",
    "network": "网络",
    "netlink": "网络链路",
    "softnet_stat": "软网络统计",
    "ops": "操作",
    "latency": "延迟",
    "dimensions": "维度",
    "discovery": "发现",
    "balloon": "内存气泡",
    "uptime": "运行时长",
    "anomaly_detection": "异常检测",
    "anomaly_rate": "异常率",
    "apps.plugin": "Apps 插件",
    "network-viewer.plugin": "网络视图插件"
    /* 设备名（eth0/sda/nvme0n1 等）与插件内部路径（ChartEngine/*、Agent/JobMgr/*）不译 */
  };

  /* 前缀规则：Job Manager 内部指标是 "Current/Cumulative/Age of the Job Manager <id>" 模式，
     逐条列词典不划算，按前缀换中文后保留 <id> 原文 */
  var RULES = [
    [/^Current Job Manager /, 'Job Manager 当前 '],
    [/^Cumulative Job Manager /, 'Job Manager 累计 '],
    [/^Age of the Job Manager /, 'Job Manager 最长等待 ']
  ];

  function trBase(s) {
    if (D[s] !== undefined) return D[s];
    for (var i = 0; i < RULES.length; i++) {
      if (RULES[i][0].test(s)) return s.replace(RULES[i][0], RULES[i][1]);
    }
    return null;
  }

  function trTitle(s) {
    if (!s || typeof s !== 'string' || s.length > 200) return s;
    var r = trBase(s);
    if (r !== null) return r;
    /* 标题形如 "Base (chart-id)"：译基础名，保留括号内的 chart id */
    var i = s.lastIndexOf(' (');
    if (i > 0 && s.charAt(s.length - 1) === ')') {
      var base = s.slice(0, i);
      var id = s.slice(i + 2, -1);
      r = trBase(base);
      if (r !== null) return r + ' (' + id + ')';
    }
    return s;
  }

  function walk(o, depth) {
    if (!o || depth > 14) return;
    if (Array.isArray(o)) {
      for (var i = 0; i < o.length; i++) walk(o[i], depth + 1);
      return;
    }
    if (typeof o !== 'object') return;
    for (var k in o) {
      if (!Object.prototype.hasOwnProperty.call(o, k)) continue;
      var v = o[k];
      if (typeof v === 'string') {
        if (k === 'title') o[k] = trTitle(v);
        else if (k === 'label') { if (D[v] !== undefined) o[k] = D[v]; }
        else if (k === 'family') { if (FAM[v] !== undefined) o[k] = FAM[v]; }
      } else if (v && typeof v === 'object') {
        walk(v, depth + 1);
      }
    }
  }

  var origFetch = window.fetch ? window.fetch.bind(window) : null;
  if (!origFetch) return;

  window.fetch = function () {
    var args = arguments;
    var url = (typeof args[0] === 'string') ? args[0] : ((args[0] && args[0].url) || '');
    return origFetch.apply(window, args).then(function (resp) {
      try {
        if (!resp.ok) return resp;
        var ct = (resp.headers && resp.headers.get) ? (resp.headers.get('content-type') || '') : '';
        if (ct.indexOf('json') === -1) return resp;
        var isApi = url.indexOf('/api/v3/q') !== -1
          || url.indexOf('/api/v1/charts') !== -1
          || url.indexOf('/api/v1/contexts') !== -1
          || url.indexOf('/api/v3/nodes') !== -1;
        if (!isApi) return resp;
        return resp.clone().text().then(function (txt) {
          var t = txt.trim();
          if (!t || (t.charAt(0) !== '{' && t.charAt(0) !== '[')) return resp;
          var data;
          try { data = JSON.parse(t); } catch (e) { return resp; }
          walk(data, 0);
          var h = {};
          if (resp.headers && resp.headers.forEach) resp.headers.forEach(function (val, key) { h[key] = val; });
          return new Response(JSON.stringify(data), { status: resp.status, statusText: resp.statusText, headers: h });
        }).catch(function () { return resp; });
      } catch (e) { return resp; }
    });
  };
})();
