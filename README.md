```markdown
# auto-trackers-fetcher 🛰️

![Python Version](https://img.shields.io/badge/python-3.6+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Last Update](https://img.shields.io/github/last-commit/DaXiGua732/auto-trackers-fetcher)

`auto-trackers-fetcher` 是一个轻量级且高效的 Python 工具，专门用于从多个知名社区来源自动获取、聚合并去重 BitTorrent Tracker 列表。

## 📥 订阅地址 (每日自动更新)

如果你不想运行脚本，可以直接在下载软件（如 qBittorrent, Transmission, Motrix）中订阅以下链接。

### 🚀 加速链接 (推荐)
使用 jsDelivr CDN 加速，访问更稳定：
* **精选列表 (Best):** `https://cdn.jsdelivr.net/gh/DaXiGua732/auto-trackers-fetcher@main/tracker.txt`
* **全量列表 (All):** `https://cdn.jsdelivr.net/gh/DaXiGua732/auto-trackers-fetcher@main/all_trackers.txt`

### 🔗 原始链接 (GitHub Raw)
* **精选列表:** `https://raw.githubusercontent.com/DaXiGua732/auto-trackers-fetcher/main/tracker.txt`
* **全量列表:** `https://raw.githubusercontent.com/DaXiGua732/auto-trackers-fetcher/main/all_trackers.txt`

---

## 🌟 核心功能

* **多线程加速:** 采用 `ThreadPoolExecutor` 并发请求，即便数据源较多也能秒速完成。
* **智能去重:** 自动合并多个源的数据，剔除重复项并按字母顺序规范化排列。
* **云端自动化:** 通过 GitHub Actions 实现每日定时更新，无需人工干预。

## 🚀 快速上手

### 安装依赖
```bash
pip install requests
```

### 运行程序
```bash
python auto-trackers-fetcher.py
```

## 🤝 致谢 (Credits)

本项目的数据主要抓取并整合自以下优秀的开源项目，感谢他们的持续维护：

* [ngosang/trackerslist](https://github.com/ngosang/trackerslist)
* [XIU2/TrackersListCollection](https://github.com/XIU2/TrackersListCollection)

## 📄 开源协议
本项目基于 [MIT License](LICENSE) 协议开源。

## 💬 补充说明
* 本项目使用 **Gemini 3 Flash** 辅助创作。
* 仅供技术交流与学习使用，不进行任何商业用途。
```
