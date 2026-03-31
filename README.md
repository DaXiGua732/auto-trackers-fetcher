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

## 🌟 核心功能

* **🛡️ 智能三重质检机制 (核心亮点):** 
  摒弃“拿来即用”的盲目模式，保存前对所有节点进行严格体检：
  1. **格式与协议校验**：剔除非标准链接。
  2. **DNS 解析与安全过滤**：自动过滤无法解析的死链；**拦截被恶意篡改指向内网/本地回环（如 127.0.0.1）的劫持链接**。
  3. **HTTP 存活探测**：对 Web 类节点发起轻量级 HEAD 请求，过滤域名有效但服务已宕机的“僵尸节点”。
* **🧵 多线程极速并发:** 采用 `ThreadPoolExecutor` 同时进行网络拉取和质检探测，百余个节点在十几秒内完成全量验证。
* **🔗 多源聚合与去重:** 融合 GitHub 静态列表与 newTrackon 动态 API，自动去重并按字母排序。
* **📉 失效感知追踪:** 对比本地旧文件，不仅能提示“新增了什么”，还能明确告知“移除/失效了哪些旧节点”。

## 🚀 快速上手

### 安装依赖
```bash
pip install requests
```

### 运行程序
```bash
python auto-trackers-fetcher.py
```
*(运行后会将经过质检的纯净列表输出到本地的 `tracker.txt` 和 `all_trackers.txt`)*

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
* [newTrackon](https://newtrackon.com/)

## 📄 开源协议
本项目基于 [MIT License](LICENSE) 协议开源。

## 💬 补充说明
* 本项目使用 **Gemini** 辅助创作。
* 仅供技术交流与学习使用，不进行任何商业用途。
```
