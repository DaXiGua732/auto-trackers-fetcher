# auto-trackers-fetcher 🛰️

![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Auto Update](https://github.com/DaXiGua732/auto-trackers-fetcher/actions/workflows/update-trackers.yml/badge.svg)
![Last Update](https://img.shields.io/github/last-commit/DaXiGua732/auto-trackers-fetcher)

`auto-trackers-fetcher` 是一个轻量的 BitTorrent Tracker 列表抓取 + 质检工具：从 3 个公开源拉取列表 → 合并去重 → 逐条质检 → 与上一次的结果比对 → 原子写回 `tracker.txt`（精选）和 `all_trackers.txt`（全量）。本仓库里的这两份文件由 GitHub Actions **每小时**自动刷新，可以直接订阅使用，也可以自己跑。

## 📥 订阅地址（每小时自动更新）

在下载软件的「自动更新 Tracker 列表」里填下面任一条即可，文件本身已经是质检后的结果。

### 🚀 加速链接（jsDelivr CDN）
CDN 有缓存，可能滞后几小时；要最新就走下面的 Raw。

* **精选列表 (Best):** `https://cdn.jsdelivr.net/gh/DaXiGua732/auto-trackers-fetcher@main/tracker.txt`
* **全量列表 (All):** `https://cdn.jsdelivr.net/gh/DaXiGua732/auto-trackers-fetcher@main/all_trackers.txt`

### 🔗 原始链接（GitHub Raw）
* **精选列表:** `https://raw.githubusercontent.com/DaXiGua732/auto-trackers-fetcher/main/tracker.txt`
* **全量列表:** `https://raw.githubusercontent.com/DaXiGua732/auto-trackers-fetcher/main/all_trackers.txt`

> 当前规模（2026-10-31 实测）：`tracker.txt` ≈ 58 条，`all_trackers.txt` ≈ 105 条。数字会随源的生死浮动。

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

* **🔗 多源聚合 + 智能去重**
  融合 3 个源（`ngosang/trackerslist` 静态列表、`cf.trackerslist.com` 静态列表、`newTrackon` 动态 API），自动合并重复项并按 URL 排序输出。同一份源被两组（精选/全量）同时用到时，一轮内只拉取一次。

* **🛡️ 逐条质检**
  每条 Tracker 入库前过三道关：
  1. **协议白名单**：只保留 `udp://` `http://` `https://`；畸形链接以及 `ws://` / `wss://` 条目会被丢弃；
  2. **公网地址筛查**：解析 DNS（IPv4 / **IPv6** 都支持）并校验 IP，**指向内网/本地回环（如 127.0.0.1）的地址会被过滤**；
  3. **HTTP 存活探测**：对 HTTP/HTTPS 节点发送带最小 announce 参数的 GET 请求（比 HEAD 更贴近真实访问）：`404`（端点不存在）与 `5xx` 判为失效，其余响应（含常见的 `400`/`403`）视为存活。

  > 💡 `udp://` 是无连接的，只做前两步（DNS）。日志会明确写出「UDP 未探测 N 条」，不会假装验过。

* **🧵 多线程并发 + 一轮内复用**
  基于 `ThreadPoolExecutor`：拉取最多 10 线程，质检最多 20 线程（`--max-workers` 可调）；每线程独立 `requests.Session`。本轮拉到的列表、每条 tracker 的质检结论、DNS 结果都在**一轮内**缓存，因此「精选」和「全量」重叠的那些条目只探一次。

* **📊 变更感知 & 增量提示**
  与旧文件逐条比对，日志里清楚写出新增 / 移除各多少条；列表完全没变时直接跳过写入，不产生无意义刷新。

* **🛟 数据安全设计（绝不因一次失败毁掉积累）**
  - **空结果保护**：拉取全部失败、或质检后一条有效都没有时，**保留旧文件不变**（退出码 1，方便 cron 感知）；
  - **骤降保护**：本轮有效条目比旧文件少两成（且超过 5 条）时拒绝写入、保留旧文件，用来区分「网络抖动」与「源真的被清理」；确认源确已清理时，删掉旧文件重跑即可；
  - **原子写入**：临时文件 + `os.replace()`，进程中断也不会留下半截文件；
  - **跳过空写**：内容无变化时不落盘。

* **♻️ 健壮性设计**
  - 拉取失败自带重试（默认 3 次，**指数退避 + 随机抖动**），且只对网络错误 / `5xx` / `429` 重试，`404` 这类永久错误不浪费时间；
  - DNS 与探测结论在一轮内缓存，减少重复查询；
  - 异常单点失败不影响整体流程；
  - 日志分级；失败与非零退出码，方便 cron / CI 感知。

### 🧪 质检到底验了什么（别期待过高）

`tracker.txt` / `all_trackers.txt` 里的条目是「**可解析 + （HTTP 的话）端点有响应**」，不等于 announce 一定可用：

- 约七成条目是 `udp://`，只验了域名能解析到公网 IP，没有真发过 UDP 报文；
- `http(s)://` 条目只要不是 `404`/`5xx` 就算活着，`400`/`403` 也会放行（多数 tracker 对「没有 info_hash 的请求」本来就返回 400）。

换句话说，这套质检能去掉**死域名、内网地址、明显挂掉的 HTTP 端点**，但去不掉「域名还在、服务已经不做种了」的僵尸节点。这与「只筛一次、不实跑下载」的定位是一致的。

## 🚀 快速上手

### 安装依赖
```bash
pip install -r requirements.txt
# 只有一个依赖，也可以直接：pip install requests
```

### 运行程序
```bash
python auto-trackers-fetcher.py
```
*(运行后会把质检过的列表写到当前目录的 `tracker.txt` 和 `all_trackers.txt`)*

### 可选参数

| 参数 | 说明 |
| :--- | :--- |
| `--output-dir <目录>` | 输出目录（默认当前目录，不存在会自动创建） |
| `--no-validate` | 跳过质检（仅合并去重，网络差时更快） |
| `--dry-run` | 干跑：拉取 / 质检 / 比对，但不写任何文件 |
| `--log-level {DEBUG,INFO,WARNING,ERROR}` | 日志级别（默认 INFO） |
| `--max-workers <N>` | 质检线程数上限（默认 `min(条目数, 20)`，必须 ≥ 1） |

示例：
```bash
# 指定输出目录，仅拉取不校验
python auto-trackers-fetcher.py --output-dir ./lists --no-validate

# 干跑确认一切正常（会被骤降保护拦下的话，退出码同样是 1）
python auto-trackers-fetcher.py --dry-run
```

### 退出码

| 退出码 | 含义 |
| :--- | :--- |
| `0` | 两组都成功（含「无变化跳过写入」「干跑」） |
| `1` | 有任一组失败：拉取为空 / 质检无有效条目 / 骤降保护拦下 / 写入失败 |
| `130` | 被 Ctrl-C 中断 |

### 实测耗时（2026-10-31，本机，200 余条）

| 场景 | 耗时 |
| :--- | :--- |
| `--no-validate --dry-run`（只拉取） | ~3 秒 |
| 完整一轮（拉取 + 质检 + 比对 + 写盘） | ~20 秒 |
| 其中 HTTP 探测次数 | 55 次（两组重叠的只探一次） |

## 🧑💻 开发与维护

### 目录

| 文件 | 作用 |
| :--- | :--- |
| `auto-trackers-fetcher.py` | 全部逻辑：解析 / 质检策略 / 本轮资源 / 拉取 / 质检 / 写盘 / CLI |
| `test_auto_trackers.py` | 回归测试（不联网、不碰磁盘） |
| `GLOSSARY.md` | 领域的词表：tracker、源、质检、生效列表、骤降保护、一轮更新 |
| `.github/workflows/update-trackers.yml` | 每小时自动跑一遍并提交两个 txt |

### 跑测试
```bash
pip install requests          # 测试需要导入脚本，因此需要这个依赖
python -m unittest -v test_auto_trackers
```
20 个用例覆盖：URL 解析、质检判定（重试与状态码）、本轮缓存的命中与生命周期、写盘策略的全部分支、旧文件保护、原子写入。已在本机 Python **3.8 / 3.10 / 3.13 / 3.15** 实跑通过（CI 用 3.10）。

### 自动更新是怎么跑的
`.github/workflows/update-trackers.yml` 每小时（UTC 整点）在 ubuntu-latest 上跑一次，也可以到 **Actions → Auto Update Trackers → Run workflow** 手动触发：

1. checkout → 装 Python 3.10 → `pip install requests`；
2. `python auto-trackers-fetcher.py`（无参数，写在仓库根目录）；
3. 只有 `tracker.txt` / `all_trackers.txt` 有变化时，才由 `github-actions[bot]` 提交一次。

想改行为，改脚本里的常量即可：源列表与输出文件名都在 `GROUPS`（加一组 = 加一行数据）；骤降保护的阈值在 `plan_update`，改之前请先看那段旁边的注释。

> ⚠️ 因为机器人在跑，直接改仓库里的 txt 文件会在下一次整点被覆盖；要长期改变输出，改脚本或源列表。

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

本项目的数据抓取并整合自以下开源项目，感谢他们的持续维护：

* [ngosang/trackerslist](https://github.com/ngosang/trackerslist) —— 精选 / 全量列表
* [XIU2/TrackersListCollection](https://github.com/XIU2/TrackersListCollection) —— 即 `cf.trackerslist.com` 背后的列表
* [CorralPeltzer/newTrackon](https://github.com/CorralPeltzer/newTrackon) —— `/api/stable` 动态列表

## 📄 开源协议
本项目基于 [MIT License](LICENSE) 协议开源。

## 💬 补充说明
* 本项目使用 **Gemini** 辅助创作。
* 仅供技术交流与学习使用，不进行任何商业用途。