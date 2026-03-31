import requests
import os
import logging
import socket
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse
from ipaddress import ip_address
from typing import Set, Tuple
from contextlib import contextmanager

# --- 配置 ---

# 重试配置
MAX_RETRIES = 3
RETRY_DELAY = 2

# Tracker源URL
BEST_TRACKER_URLS = [
    "https://raw.githubusercontent.com/ngosang/trackerslist/master/trackers_best.txt",
    "https://cf.trackerslist.com/best.txt",
    "https://newtrackon.com/api/stable"
]

ALL_TRACKER_URLS = [
    "https://raw.githubusercontent.com/ngosang/trackerslist/master/trackers_all.txt",
    "https://cf.trackerslist.com/all.txt",
    "https://newtrackon.com/api/stable"
]

BEST_OUTPUT_FILE = "tracker.txt"
ALL_OUTPUT_FILE = "all_trackers.txt"

# --- 日志配置 ---
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# --- Session管理 ---
@contextmanager
def create_session():
    """创建带UA配置的Session，支持上下文管理"""
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })
    yield session
    session.close()


def fetch_trackers_from_url(url: str, session: requests.Session, max_retries: int = MAX_RETRIES) -> Set[str]:
    """拉取Tracker列表，带重试机制"""
    for attempt in range(1, max_retries + 1):
        try:
            response = session.get(url, timeout=10)
            response.raise_for_status()
            trackers = {line.strip() for line in response.text.splitlines() if line.strip()}
            logging.info(f"[拉取成功] {url} -> {len(trackers)} 条")
            return trackers
        except requests.RequestException as e:
            if attempt < max_retries:
                logging.warning(f"[重试 {attempt}/{max_retries}] {url} -> {e}")
                time.sleep(RETRY_DELAY)
            else:
                logging.error(f"[拉取失败] {url} -> {e}")
                return set()
    return set()


def fetch_all_trackers(urls: list, session: requests.Session) -> Set[str]:
    """多线程拉取并去重"""
    all_trackers: Set[str] = set()
    max_workers = min(len(urls), 10)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(fetch_trackers_from_url, url, session): url for url in urls}
        for future in as_completed(futures):
            result = future.result()
            if result:
                all_trackers.update(result)
    
    original_count = sum(len(future.result()) for future in futures if future.done())
    dedup_count = len(all_trackers)
    if original_count > dedup_count:
        logging.info(f"去重: 原始 {original_count} 条 -> 去重后 {dedup_count} 条")
    
    return all_trackers


def validate_tracker_url(tracker_url: str) -> Tuple[bool, str]:
    """验证单个Tracker的有效性"""
    try:
        parsed = urlparse(tracker_url)
        if parsed.scheme not in ["udp", "http", "https"]:
            return False, "无效协议"
        if not parsed.hostname:
            return False, "无域名"
    except Exception:
        return False, "URL解析失败"

    hostname = parsed.hostname
    try:
        ip_str = socket.gethostbyname(hostname)
        ip_obj = ip_address(ip_str)
        if not ip_obj.is_global:
            return False, f"非公网IP({ip_str})"
    except socket.gaierror:
        return False, "DNS解析失败(死链)"
    except Exception:
        pass

    if parsed.scheme in ["http", "https"]:
        try:
            resp = requests.head(tracker_url, timeout=3, allow_redirects=True)
            if resp.status_code < 500:
                return True, "存活"
            return False, f"服务器错误({resp.status_code})"
        except requests.Timeout:
            return False, "响应超时"
        except requests.RequestException:
            return False, "连接拒绝"

    return True, "UDP(未探测)"


def filter_valid_trackers(raw_trackers: Set[str]) -> Set[str]:
    """多线程过滤无效Tracker"""
    valid_trackers: Set[str] = set()
    invalid_count = 0
    max_workers = min(len(raw_trackers), 20)
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(validate_tracker_url, url): url for url in raw_trackers}
        completed = 0
        total = len(futures)
        
        for future in as_completed(futures):
            completed += 1
            url = futures[future]
            is_valid, reason = future.result()
            if is_valid:
                valid_trackers.add(url)
            else:
                invalid_count += 1
            
            if completed % 50 == 0 or completed == total:
                logging.info(f"质检进度: {completed}/{total} (已过滤: {invalid_count})")
    
    logging.info(f"质检完毕: 总计 {len(raw_trackers)} 条, 有效 {len(valid_trackers)} 条, 过滤 {invalid_count} 条")
    return valid_trackers


def read_old_trackers(file_path: str) -> Set[str]:
    """读取旧的Tracker文件"""
    if not os.path.exists(file_path):
        return set()
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return {line.strip() for line in f if line.strip()}
    except IOError:
        return set()


def save_trackers(file_path: str, trackers: Set[str]) -> bool:
    """保存Tracker到文件，返回成功状态"""
    try:
        sorted_trackers = sorted(trackers)
        with open(file_path, 'w', encoding='utf-8', newline='\n') as f:
            f.write('\n'.join(sorted_trackers))
        logging.info(f"写入 {file_path} 完成: {len(trackers)} 条")
        return True
    except IOError as e:
        logging.error(f"写入失败 {file_path}: {e}")
        return False


def process_tracker_group(name: str, urls: list, output_file: str, session: requests.Session) -> None:
    """处理单组Tracker：拉取、验证、对比增量、保存"""
    logging.info(f"=== 处理 {name} ===")
    raw_trackers = fetch_all_trackers(urls, session)
    if not raw_trackers:
        logging.error(f"{name} 未获取到数据")
        return

    logging.info(f"{name} 开始质检过滤...")
    valid_trackers = filter_valid_trackers(raw_trackers)

    old_trackers = read_old_trackers(output_file)
    if old_trackers:
        added = valid_trackers - old_trackers
        removed = old_trackers - valid_trackers
        if added:
            logging.info(f"{name} 新增 {len(added)} 个Tracker")
        if removed:
            logging.info(f"{name} 移除/失效 {len(removed)} 个Tracker")
        if not added and not removed:
            logging.info(f"{name} 列表无变化")

    save_trackers(output_file, valid_trackers)


def main() -> None:
    """主入口：处理所有Tracker组"""
    logging.info("=== Tracker更新开始 ===")
    with create_session() as session:
        process_tracker_group(name="BEST", urls=BEST_TRACKER_URLS, output_file=BEST_OUTPUT_FILE, session=session)
        print()
        process_tracker_group(name="ALL", urls=ALL_TRACKER_URLS, output_file=ALL_OUTPUT_FILE, session=session)
    logging.info("=== 全部完成 ===")


if __name__ == "__main__":
    main()
