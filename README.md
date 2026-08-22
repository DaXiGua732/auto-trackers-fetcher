# auto-trackers-fetcher 🛰️

![Python Version](https://img.shields.io/badge/python-3.6+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Last Update](https://img.shields.io/github/last-commit/DaXiGua732/auto-trackers-fetcher)

`auto-trackers-fetcher` 是一个轻量级且高效的 Python **智能质检工具**。它不仅从多个知名来源自动获取 BitTorrent Tracker 列表，更会在保存前进行严格的可用性与安全性过滤，为你剔除死链与恶意地址，提供真正纯净、高可用的 Tracker 节点。

## 📥 订阅地址 (每日自动更新)

如果你不想运行脚本，可以直接在下载软件（如 qBittorrent, Transmission, Motrix）中订阅以下链接。**这些文件已经是经过质检后的纯净版。**

### 🚀 加速链接 (推荐)
使用 jsDelivr CDN 加速，访问更稳定：
* **精选列表 (Best):** `https://cdn.jsdelivr.net/gh/DaXiGua732/auto-trackers-fetcher@main/tracker.txt`
* **全量列表 (All):** `https://cdn.jsdelivr.net/gh/DaXiGua732/auto-trackers-fetcher@main/all_trackers.txt`

### 🔗 原始链接 (GitHub Raw)
* **精选列表:** `https://raw.githubusercontent.com/DaXiGua732/auto-trackers-fetcher/main/tracker.txt`
* **全量列表:** `https://raw.githubusercontent.com/DaXiGua732/auto-trackers-fetcher/main/all_trackers.txt`

---

## 🌍 Tracker 是什么？它对 BT 下载有什么用？

很多人用 BT 下载种子，却不知道 **Tracker 是让"散落在全世界的下载者"彼此相遇的关键一环**。下面用大白话讲清楚。

### BT 下载的本质：人人都是"搬运工"

普通下载（HTTP/FTP）像**去超市买东西**：所有人都从同一个货架（服务器）拿，人一多货架就拥挤甚至断货。

BT 下载则更像**小区里互相借书**：你下载一个文件时，同时也在把已经下好的部分分享给其他人；你从别人那里拿一份，别人也从你这里拿一份。没有任何中央仓库，文件被拆成无数小块，像拼图一样分布在全世界许多台电脑上。

### 问题来了：你怎么知道"谁手里有我要的块"？

所有人都互不相识，怎么找到彼此？这就是 **Tracker** 的用武之地 —— 它是一本公用"通讯录"。

简单说，Tracker 的职责只有三句话：

1. **报名**：你下载开始时，先去找 Tracker 报个到："我在下这个种子，地址是 xxx，欢迎来连我。"
2. **牵线**：Tracker 翻翻本子，把同样在下载/做种这个种子的其他人地址告诉你："这 50 台电脑也在弄，去试它们吧。"
3. **退场**：牵完线之后，你和那些电脑直接**点对点**互传，Tracker 就不再参与了，退居幕后。

打个比方：Tracker 像**图书馆借阅登记册**。你想找一本冷门书，先查登记册，就知道这本书现在在谁手里、去哪借；但真正把书递给你的是借书人本人，不是登记册。

### 为什么"Tracker 越多越好"？

- **没有 Tracker 或 Tracker 失效**：相当于通讯录被撕了，你只能靠自己认识的人（DHT 的补充机制，下详），冷门种子经常因此"连一个人都找不到"，下载卡在 0%。
- **Tracker 列表越长**：能互相找到的人就越多，越容易凑齐所有分片，下载速度也越快、越稳。
- **对老种子、冷门资源尤其重要**：热门的种子"认识的人多"，不靠通讯录也行；种子越老，越依赖这份通讯录把你和仅剩的几位做种人连起来。

### 那 DHT 又是什么？

现在的 BT 客户端还内置了 **DHT（分布式哈希表）** 机制——相当于"每家每户都自己备了一本小通讯录，邻居之间互相交换信息"，不依赖统一登记处也能找人。但 DHT 的发现方式比较"慢节奏"，对老种子的补给远不如一份靠谱的 Tracker 列表直接。**所以两者是互补关系：DHT 是兜底，Tracker 列表是主力。**

### 为什么需要"纯净"的 Tracker 列表？

就像通讯录里混进了错号码和无良中介一样，未经筛选的 Tracker 列表可能包含：

| 问题 | 后果 |
| :--- | :--- |
| **死链/僵尸节点** | 一直尝试连接却无回应，白白拖慢下载、浪费连接数 |
| **内网/回环地址**（如 127.0.0.1） | 根本是伪造地址，可能用于掩盖来历不明的"用户" |
| **恶意 Tracker** | 可能记录你的 IP、上报下载行为，甚至诱导你连接到别有用心的节点 |

本项目存在的意义就是**帮你把通讯录"净水过滤"一遍**：去掉联系不上的人、去掉一眼假的名片，只留下真正可用、可信任的节点。

---

## 🌟 核心功能

* **🛡️ 三层智能过滤机制**  
  不盲目收录，每条 Tracker 入库前必经三重校验：
  1. **协议白名单**：仅保留 `udp://` `http://` `https://` 标准协议，自动剔除畸形链接；
  2. **安全域名筛查**：解析 DNS（同时支持 IPv4 / **IPv6**）并校验 IP，**自动拦截指向内网/本地回环（如 127.0.0.1）的劫持链接**；
  3. **真实存活探测**：对 HTTP/HTTPS 节点发送带最小 announce 参数的 GET 请求（比 HEAD 探测更贴近真实访问），快速识别并过滤"域名有效但服务宕机"的僵尸节点。  
  > 💡 UDP 协议因无连接特性，仅执行前两步校验，兼顾效率与安全。

* **🧵 多线程并发加速**  
  基于 `ThreadPoolExecutor` 实现拉取与质检并行（每线程独立 Session，避免共享状态竞态）：  
  → 源站拉取：最多 10 线程并发请求  
  → 有效性验证：最多 20 线程批量探测  
  → 百余个节点通常在 15~30 秒内完成全流程处理

* **🔗 多源聚合 + 智能去重**  
  融合 `ngosang/trackerslist` 静态列表与 `newTrackon` 动态 API，自动合并重复项（结果按 URL 缓存、跨组复用）并按字母排序，输出干净规整的列表文件。

* **📊 变更感知 & 增量提示**  
  每次运行自动对比本地旧文件，清晰告知：  
  ✅ 新增了多少可用节点  
  ❌ 移除了多少失效/降级节点  
  🔄 列表整体稳定性趋势一目了然

* **🛟 数据安全设计（绝不因一次失败毁掉积累）**  
  - **空结果保护**：若拉取全部失败或质检后无任何有效节点，**保留旧文件不变**，而不是用空列表覆盖；
  - **原子写入**：临时文件 + `os.replace()`，进程中断也不会留下半截文件；
  - **增量跳过**：列表无变化时直接跳过写入，避免无意义刷新。

* **♻️ 健壮性设计**  
  - 网络请求自带重试机制（默认 3 次，**指数退避 + 随机抖动**）；
  - DNS 解析结果缓存，减少重复查询；
  - 异常捕获全覆盖，单点失败不影响整体流程；
  - 失败时返回非零退出码，方便 cron / CI 感知；
  - 日志分级输出，运行状态实时可追踪。

## 🚀 快速上手

### 安装依赖
```bash
pip install -r requirements.txt
```

### 运行程序
```bash
python auto-trackers-fetcher.py
```
*(运行后会将经过质检的纯净列表输出到本地的 `tracker.txt` 和 `all_trackers.txt`)*

### 可选参数

| 参数 | 说明 |
| :--- | :--- |
| `--output-dir <目录>` | 输出目录（默认当前目录） |
| `--no-validate` | 跳过有效性质检（仅合并去重，适合网络差的场景） |
| `--dry-run` | 干跑：拉取/质检但不写任何文件 |
| `--log-level {DEBUG,INFO,WARNING,ERROR}` | 日志级别（默认 INFO） |
| `--max-workers <N>` | 质检线程数上限（默认按条目数取 min(条目数, 20)） |

示例：
```bash
# 指定输出目录，仅拉取不校验
python auto-trackers-fetcher.py --output-dir ./lists --no-validate

# 干跑确认一切正常
python auto-trackers-fetcher.py --dry-run
```

## 💻 推荐开源下载软件

为了获得最佳的下载体验，建议配合以下优秀的开源 BT 客户端使用本项目提供的 Tracker 列表：

| 软件名称 | 平台 | 特点 | 开源地址 |
| :--- | :--- | :--- | :--- |
| **qBittorrent-EE** | Windows/macOS/Linux | **强烈推荐**。增强版支持自动屏蔽吸血客户端，内置 Tracker 自动更新。 | [GitHub](https://github.com/c0re100/qBittorrent-Enhanced-Edition) |
| **qBittorrent** | Windows/macOS/Linux | 全球最流行的开源 BT 客户端，功能全面且稳定。 | [GitHub](https://github.com/qbittorrent/qBittorrent) |
| **LibreTorrent** | **Android** | **移动端首选**。完全开源、零广告、功能强大的安卓下载器。 | [GitHub](https://github.com/proninyaroslav/libretorrent) |
| **Motrix** | Windows/macOS/Linux | 极简高颜值，支持 BT、磁力、HTTP、FTP 等全能下载。 | [GitHub](https://github.com/agalwood/Motrix) |
| **Transmission** | macOS/Linux/Docker | 极度轻量，资源占用极低，适合 NAS 或服务器使用。 | [GitHub](https://github.com/transmission/transmission) |

## 🤝 致谢 (Credits)

本项目的数据主要抓取并整合自以下优秀的开源项目，感谢他们的持续维护：

* [ngosang/trackerslist](https://github.com/ngosang/trackerslist)
* [XIU2/TrackersListCollection](https://github.com/XIU2/TrackersListCollection)
* [CorralPeltzer/newTrackon](https://github.com/CorralPeltzer/newTrackon)

## 📄 开源协议
本项目基于 [MIT License](LICENSE) 协议开源。

## 💬 补充说明
* 本项目使用 **Gemini** 辅助创作。
* 仅供技术交流与学习使用，不进行任何商业用途。
