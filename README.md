# Torrent Tracker Updater

![Python Version](https://img.shields.io/badge/python-3.6+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

这是一个轻量级的 Python 工具，用于从多个权威来源自动获取、聚合并更新 BitTorrent Tracker 列表。通过保持 Tracker 的时效性，可以显著提升下载器的 Peer 连接速度。

## ✨ 功能特性

* **多线程并发:** 使用 `ThreadPoolExecutor` 同时请求多个 Tracker 源，速度极快。
* **分类处理:** 区分“精选热门 (Best)”和“全量备份 (All)”两套列表，适应不同下载场景。
* **智能去重:** 自动过滤重复项，并按字母顺序排序保存。
* **变更追踪:** 运行后自动对比本地旧文件，并在控制台高亮显示新增的 Tracker 地址。
* **健壮性:** 内置请求超时处理与详细的日志系统。

## 🚀 快速上手

### 1. 克隆仓库
```bash
git clone [https://github.com/DaXiGua732/auto-trackers-fetcher.git](https://github.com/DaXiGua732/auto-trackers-fetcher.git)
cd torrent-tracker-updater
