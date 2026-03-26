# auto-trackers-fetcher 🛰️

![Python Version](https://img.shields.io/badge/python-3.6+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-brightgreen.svg)

`auto-trackers-fetcher` 是一个轻量级且高效的 Python 工具，专门用于从多个权威源自动获取、聚合并去重 BitTorrent Tracker 列表。通过保持 Tracker 的实时更新，可以帮助下载软件（如 qBittorrent, Transmission, Motrix 等）更快地寻找 Peer 节点，大幅提升下载速度。

## 🌟 核心功能

- **多线程加速:** 采用 `ThreadPoolExecutor` 并发请求，即便数据源较多也能秒速完成。
- **智能去重与排序:** 自动合并多个源的数据，剔除重复项并按字母顺序规范化排列。
- **双层筛选机制:**
  - **BEST 列表:** 精选稳定性最高、连接最快的 Tracker，适合热门资源。
  - **ALL 列表:** 包含海量备用 Tracker，适合拯救冷门或老旧资源。
- **变化提醒:** 每次运行会自动对比本地旧数据，并在控制台显示**新增**的 Tracker 地址。

## 🚀 快速开始

### 安装依赖
只需安装 `requests` 库：
```bash
pip install requests
