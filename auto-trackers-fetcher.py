#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tracker 列表自动更新脚本（v2，改进版）。

相较 v1 的主要改进：
- 数据安全：质检后无有效结果时保留旧文件，不再用空列表覆盖；
- HTTP 探测改为 GET + 最小 announce 参数 + 复用 Session/UA（HEAD 常被服务器拒绝）；
- 文件写入改为"临时文件 + os.replace"原子替换，中断不会损坏旧文件；
- 多线程各线程独立 requests.Session（Session 非线程安全）；
- DNS 解析改用 getaddrinfo（支持 IPv6-only 主机），并加缓存；
- 拉取/探测重试改为指数退避 + 随机抖动；URL 拉取结果按 URL 缓存（跨组复用）；
- 新增命令行参数：--output-dir / --no-validate / --dry-run / --log-level / --max-workers；
- 失败时返回非零退出码，便于 cron/CI 感知。
"""

import argparse
import logging
import os
import random
import socket
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from ipaddress import ip_address
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse

try:
    import requests
except ImportError as e:  # pragma: no cover
    raise SystemExit("缺少依赖 requests，请先运行: pip install -r requirements.txt") from e

# --- 配置 ---

# 重试配置
MAX_RETRIES = 3
RETRY_BASE_DELAY = 2.0          # 指数退避基数（秒），实际延迟 = 基数 * 2^(n-1) + 抖动
FETCH_TIMEOUT = (5, 15)         # 拉取超时 (连接, 读取)
PROBE_TIMEOUT = (3, 5)          # 探测超时 (连接, 读取)

# Tracker 源 URL
BEST_TRACKER_URLS = [
    "https://raw.githubusercontent.com/ngosang/trackerslist/master/trackers_best.txt",
    "https://cf.trackerslist.com/best.txt",
    "https://newtrackon.com/api/stable",
]

ALL_TRACKER_URLS = [
    "https://raw.githubusercontent.com/ngosang/trackerslist/master/trackers_all.txt",
    "https://cf.trackerslist.com/all.txt",
    "https://newtrackon.com/api/stable",
]

BEST_OUTPUT_FILE = "tracker.txt"
ALL_OUTPUT_FILE = "all_trackers.txt"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# HTTP tracker 的最小 announce 探测参数（无 info_hash 时多数 tracker 返回 400，
# 这通常意味着 tracker 是存活的；404 才说明端点/路径不存在）
ANNOUNCE_QUERY = (
    "info_hash=%1a%2b%3c%4d%5e%6f%70%71%72%73%74%75%76%77%78%79%7a%0a%0b%0c%0d"
    "&peer_id=-TR3000-abcdefghijklmnop&port=6881&uploaded=0&downloaded=0&left=0"
    "&compact=1&numwant=0&event=started"
)

logger = logging.getLogger("tracker-fetcher")

# --- Session 管理：每线程独立 Session ---
_thread_local = threading.local()
_all_sessions: List[requests.Session] = []
_sessions_lock = threading.Lock()


def get_session() -> requests.Session:
    """获取当前线程的 Session（懒创建 + 线程隔离）。"""
    session = getattr(_thread_local, "session", None)
    if session is None:
        session = requests.Session()
        session.headers["User-Agent"] = USER_AGENT
        _thread_local.session = session
        with _sessions_lock:
            _all_sessions.append(session)
    return session


def close_all_sessions() -> None:
    """关闭所有线程创建的 Session。"""
    with _sessions_lock:
        for session in _all_sessions:
            session.close()
        _all_sessions.clear()


# --- DNS 缓存（线程安全）---
_dns_cache: Dict[str, Tuple[bool, str]] = {}
_dns_cache_lock = threading.Lock()


# --- Tracker 文本解析与规范化 ---

def normalize_tracker_url(url: str) -> Optional[str]:
    """规范化 Tracker URL：小写 scheme/host、去尾部斜杠；非法返回 None。"""
    url = url.strip()
    if not url:
        return None
    try:
        parsed = urlparse(url)
    except ValueError:
        return None
    if parsed.scheme.lower() not in ("udp", "http", "https"):
        return None
    if not parsed.hostname:
        return None
    netloc = parsed.netloc.lower()
    normalized = parsed._replace(scheme=parsed.scheme.lower(), netloc=netloc).geturl()
    # 仅去掉 URL 末尾的斜杠（不影响路径内的 /announce 等）
    if normalized.endswith("/"):
        normalized = normalized.rstrip("/")
    return normalized


def parse_tracker_lines(text: str) -> Set[str]:
    """解析文本中的 Tracker 行：跳过空行/注释行，并做规范化去重。"""
    trackers: Set[str] = set()
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        normalized = normalize_tracker_url(line)
        if normalized:
            trackers.add(normalized)
    return trackers


# --- 拉取（带指数退避重试 + 结果缓存）---

def fetch_trackers_from_url(url: str, max_retries: int = MAX_RETRIES) -> Set[str]:
    """拉取单源 Tracker 列表，指数退避 + 抖动重试；最终失败返回空集合。"""
    for attempt in range(1, max_retries + 1):
        try:
            response = get_session().get(url, timeout=FETCH_TIMEOUT)
            response.raise_for_status()
            trackers = parse_tracker_lines(response.text)
            logger.info("[拉取成功] %s -> %d 条", url, len(trackers))
            return trackers
        except requests.RequestException as e:
            if attempt < max_retries:
                delay = RETRY_BASE_DELAY * (2 ** (attempt - 1)) + random.uniform(0, 1)
                logger.warning("[重试 %d/%d] %s -> %s（%.1f 秒后重试）", attempt, max_retries, url, e, delay)
                time.sleep(delay)
            else:
                logger.error("[拉取失败] %s -> %s", url, e)
                return set()
    return set()


def fetch_all_trackers(urls: List[str], url_cache: Dict[str, Set[str]]) -> Set[str]:
    """多线程拉取全部源并去重；非空结果按 URL 缓存（跨组复用）。"""
    if not urls:
        return set()

    def fetch_cached(url: str) -> Set[str]:
        if url in url_cache:
            return url_cache[url]
        result = fetch_trackers_from_url(url)
        if result:  # 仅缓存成功结果，失败的留待下次重试
            url_cache[url] = result
        return result

    all_trackers: Set[str] = set()
    results: Dict[str, Set[str]] = {}
    max_workers = max(1, min(len(urls), 10))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(fetch_cached, url): url for url in urls}
        for future in as_completed(futures):
            url = futures[future]
            result = future.result()
            results[url] = result
            all_trackers.update(result)

    original_count = sum(len(v) for v in results.values())
    if original_count > len(all_trackers):
        logger.info("去重: 原始 %d 条 -> 去重后 %d 条", original_count, len(all_trackers))
    return all_trackers


# --- 有效性校验 ---

def resolve_global(hostname: str) -> Tuple[bool, str]:
    """解析主机名（IPv4/IPv6），返回 (是否含公网IP, 说明)。带缓存。"""
    with _dns_cache_lock:
        if hostname in _dns_cache:
            return _dns_cache[hostname]

    try:
        infos = socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP)
        addresses = sorted({info[4][0] for info in infos})
        for ip_str in addresses:
            try:
                if ip_address(ip_str).is_global:
                    result = (True, ip_str)
                    break
            except ValueError:
                continue
        else:
            result = (False, "无非公网IP(%s)" % "/".join(addresses))
    except socket.gaierror:
        result = (False, "DNS解析失败(死链)")
    except OSError as e:
        result = (False, "DNS解析异常(%s)" % e)

    with _dns_cache_lock:
        _dns_cache[hostname] = result
    return result


def probe_http_tracker(tracker_url: str) -> Optional[int]:
    """GET + 最小 announce 参数探测 HTTP tracker，返回状态码；网络失败返回 None。"""
    sep = "&" if "?" in tracker_url else "?"
    probe_url = tracker_url + sep + ANNOUNCE_QUERY
    try:
        response = get_session().get(probe_url, timeout=PROBE_TIMEOUT, stream=True, allow_redirects=True)
        try:
            # 读取少量响应体以复用连接（避免 tracker 返回大体积页面被完整下载）
            if response.raw:
                response.raw.read(4096)
        except Exception:
            pass
        finally:
            response.close()
        return response.status_code
    except requests.RequestException:
        return None


def validate_tracker_url(tracker_url: str) -> Tuple[bool, str]:
    """验证单个 Tracker 的有效性。"""
    try:
        parsed = urlparse(tracker_url)
    except ValueError:
        return False, "URL解析失败"
    if parsed.scheme not in ("udp", "http", "https"):
        return False, "无效协议"
    if not parsed.hostname:
        return False, "无域名"

    ok, info = resolve_global(parsed.hostname)
    if not ok:
        return False, info

    if parsed.scheme in ("http", "https"):
        status = probe_http_tracker(tracker_url)
        if status is None:
            return False, "连接失败/超时"
        if status == 404:
            return False, "HTTP 404(端点不存在)"
        if status >= 500:
            return False, "服务器错误(%d)" % status
        return True, "存活(HTTP %d)" % status

    return True, "UDP(未探测)"


def filter_valid_trackers(raw_trackers: Set[str], max_workers: Optional[int] = None) -> Set[str]:
    """多线程过滤无效 Tracker。"""
    if not raw_trackers:
        return set()
    valid_trackers: Set[str] = set()
    invalid_count = 0
    workers = max_workers or min(len(raw_trackers), 20)
    workers = max(1, workers)

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(validate_tracker_url, url): url for url in raw_trackers}
        completed = 0
        total = len(futures)
        for future in as_completed(futures):
            completed += 1
            is_valid, reason = future.result()
            if is_valid:
                valid_trackers.add(futures[future])
            else:
                invalid_count += 1
            if completed % 50 == 0 or completed == total:
                logger.info("质检进度: %d/%d (已过滤: %d)", completed, total, invalid_count)

    logger.info("质检完毕: 总计 %d 条, 有效 %d 条, 过滤 %d 条", len(raw_trackers), len(valid_trackers), invalid_count)
    return valid_trackers


# --- 文件读写 ---

def read_old_trackers(file_path: str) -> Set[str]:
    """读取旧 Tracker 文件。"""
    if not os.path.exists(file_path):
        return set()
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return {line.strip() for line in f if line.strip()}
    except (IOError, OSError) as e:
        logger.warning("读取旧文件失败 %s: %s（按空处理）", file_path, e)
        return set()


def save_trackers(file_path: str, trackers: Set[str]) -> bool:
    """原子写入 Tracker 文件（临时文件 + os.replace）。"""
    try:
        sorted_trackers = sorted(trackers)
        content = "\n".join(sorted_trackers) + ("\n" if sorted_trackers else "")
        dir_path = os.path.dirname(os.path.abspath(file_path)) or "."
        fd, tmp_path = tempfile.mkstemp(prefix=".trackers-", suffix=".tmp", dir=dir_path)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
                f.write(content)
            os.replace(tmp_path, file_path)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        logger.info("写入 %s 完成: %d 条", file_path, len(trackers))
        return True
    except (IOError, OSError) as e:
        logger.error("写入失败 %s: %s", file_path, e)
        return False


# --- 分组处理 ---

def process_tracker_group(
    name: str,
    urls: List[str],
    output_file: str,
    url_cache: Dict[str, Set[str]],
    validate: bool = True,
    dry_run: bool = False,
    max_workers: Optional[int] = None,
) -> bool:
    """处理单组 Tracker：拉取、验证、对比增量、保存。返回是否成功。"""
    logger.info("=== 处理 %s ===", name)
    raw_trackers = fetch_all_trackers(urls, url_cache)
    if not raw_trackers:
        logger.error("%s 未获取到任何数据，保留旧文件不变", name)
        return False

    if validate:
        logger.info("%s 开始质检过滤...", name)
        valid_trackers = filter_valid_trackers(raw_trackers, max_workers=max_workers)
    else:
        valid_trackers = raw_trackers

    if not valid_trackers:
        logger.error("%s 质检后无有效 Tracker，保留旧文件不变", name)
        return False

    old_trackers = read_old_trackers(output_file)
    if old_trackers:
        added = valid_trackers - old_trackers
        removed = old_trackers - valid_trackers
        if added:
            logger.info("%s 新增 %d 个 Tracker", name, len(added))
        if removed:
            logger.info("%s 移除/失效 %d 个 Tracker", name, len(removed))
        if not added and not removed:
            logger.info("%s 列表无变化，跳过写入", name)
            return True
    else:
        logger.info("%s 首次生成: %d 条", name, len(valid_trackers))

    if dry_run:
        logger.info("%s 干跑模式（--dry-run），不写入文件", name)
        return True
    return save_trackers(output_file, valid_trackers)


# --- 主入口 ---

def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Tracker 列表自动更新脚本：拉取 → 质检 → 增量对比 → 原子写入",
    )
    parser.add_argument("--output-dir", default=".", help="输出目录（默认当前目录）")
    parser.add_argument("--no-validate", action="store_true", help="跳过有效性质检（仅合并去重）")
    parser.add_argument("--dry-run", action="store_true", help="干跑：拉取/质检但不写文件")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                        help="日志级别（默认 INFO）")
    parser.add_argument("--max-workers", type=int, default=None,
                        help="质检线程数上限（默认 min(条目数, 20)）")
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(level=getattr(logging, args.log_level.upper()),
                        format="%(levelname)s: %(message)s")
    os.makedirs(args.output_dir, exist_ok=True)

    best_out = os.path.join(args.output_dir, BEST_OUTPUT_FILE)
    all_out = os.path.join(args.output_dir, ALL_OUTPUT_FILE)
    url_cache: Dict[str, Set[str]] = {}

    logger.info("=== Tracker 更新开始 ===")
    try:
        ok1 = process_tracker_group("BEST", BEST_TRACKER_URLS, best_out, url_cache,
                                    validate=not args.no_validate, dry_run=args.dry_run,
                                    max_workers=args.max_workers)
        ok2 = process_tracker_group("ALL", ALL_TRACKER_URLS, all_out, url_cache,
                                    validate=not args.no_validate, dry_run=args.dry_run,
                                    max_workers=args.max_workers)
        logger.info("=== 全部完成（%s）===", "成功" if (ok1 and ok2) else "部分失败")
        return 0 if (ok1 and ok2) else 1
    except KeyboardInterrupt:
        logger.error("收到中断信号，退出")
        return 130
    finally:
        close_all_sessions()


if __name__ == "__main__":
    sys.exit(main())
