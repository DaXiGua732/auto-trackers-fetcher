import requests
import os
import logging
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse
from ipaddress import ip_address

# --- 配置 ---

# 热门 tracker
BEST_TRACKER_URLS = [
    "https://raw.githubusercontent.com/ngosang/trackerslist/master/trackers_best.txt",
    "https://cf.trackerslist.com/best.txt",
    "https://newtrackon.com/api/stable" 
]

# 全量 tracker
ALL_TRACKER_URLS = [
    "https://raw.githubusercontent.com/ngosang/trackerslist/master/trackers_all.txt",
    "https://cf.trackerslist.com/all.txt",
    "https://newtrackon.com/api/stable"
]

BEST_OUTPUT_FILE = "tracker.txt"
ALL_OUTPUT_FILE = "all_trackers.txt"

# --- 日志 ---
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# --- Session ---
session = requests.Session()
# 【重要】保留伪装 UA，因为 raw.githubusercontent.com 如果没有 UA 经常会被直接拒绝 (返回 403)
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
})


def fetch_trackers_from_url(url):
    """统一的拉取函数"""
    try:
        response = session.get(url, timeout=10)
        response.raise_for_status()
        trackers = {line.strip() for line in response.text.splitlines() if line.strip()}
        logging.info(f"[拉取成功] {url} -> {len(trackers)} 条")
        return trackers
    except requests.RequestException as e:
        logging.error(f"[拉取失败] {url} -> {e}")
        return set()


def fetch_all_trackers(urls):
    """多线程拉取"""
    all_trackers = set()
    with ThreadPoolExecutor(max_workers=len(urls)) as executor:
        futures = {executor.submit(fetch_trackers_from_url, url): url for url in urls}
        for future in as_completed(futures):
            all_trackers.update(future.result())
    return all_trackers


def validate_tracker_url(tracker_url):
    """质检单个 Tracker"""
    try:
        parsed = urlparse(tracker_url)
        if parsed.scheme not in ["udp", "http", "https"]: return False, "无效协议"
        if not parsed.hostname: return False, "无域名"
    except Exception: return False, "URL解析失败"

    hostname = parsed.hostname
    try:
        ip_str = socket.gethostbyname(hostname)
        ip_obj = ip_address(ip_str)
        if not ip_obj.is_global: return False, f"非公网IP({ip_str})"
    except socket.gaierror: return False, "DNS解析失败(死链)"
    except Exception: pass

    if parsed.scheme in ["http", "https"]:
        try:
            resp = requests.head(tracker_url, timeout=3, allow_redirects=True)
            if resp.status_code < 500: return True, "存活"
            else: return False, f"服务器错误({resp.status_code})"
        except requests.Timeout: return False, "响应超时"
        except requests.RequestException: return False, "连接拒绝"

    return True, "UDP(未探测)"


def filter_valid_trackers(raw_trackers):
    """多线程过滤无效 Tracker"""
    valid_trackers = set()
    invalid_count = 0
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(validate_tracker_url, url): url for url in raw_trackers}
        for future in as_completed(futures):
            url = futures[future]
            is_valid, reason = future.result()
            if is_valid:
                valid_trackers.add(url)
            else:
                invalid_count += 1
    logging.info(f"质检完毕: 总计 {len(raw_trackers)} 条, 有效 {len(valid_trackers)} 条, 过滤垃圾/死链 {invalid_count} 条")
    return valid_trackers


def read_old_trackers(file_path):
    if not os.path.exists(file_path): return set()
    try:
        with open(file_path, 'r', encoding='utf-8') as f: return {line.strip() for line in f if line.strip()}
    except IOError: return set()


def save_trackers(file_path, trackers):
    try:
        with open(file_path, 'w', encoding='utf-8', newline='\n') as f:
            f.write('\n'.join(sorted(trackers)))
        logging.info(f"写入 {file_path} 完成: {len(trackers)} 条")
    except IOError as e:
        logging.error(f"写入失败 {file_path}: {e}")


def process_tracker_group(name, urls, output_file):
    logging.info(f"=== 处理 {name} ===")
    raw_trackers = fetch_all_trackers(urls)
    if not raw_trackers:
        logging.error(f"{name} 未获取到数据")
        return

    logging.info(f"{name} 开始质检过滤...")
    valid_trackers = filter_valid_trackers(raw_trackers)

    old_trackers = read_old_trackers(output_file)
    if old_trackers:
        added = valid_trackers - old_trackers
        removed = old_trackers - valid_trackers
        if added: logging.info(f"{name} 新增 {len(added)} 个有效Tracker")
        if removed: logging.info(f"{name} 移除/失效 {len(removed)} 个旧Tracker")
        if not added and not removed: logging.info(f"{name} 列表无变化")

    save_trackers(output_file, valid_trackers)


def main():
    logging.info("=== Tracker更新开始 ===")
    process_tracker_group(name="BEST", urls=BEST_TRACKER_URLS, output_file=BEST_OUTPUT_FILE)
    print()
    process_tracker_group(name="ALL", urls=ALL_TRACKER_URLS, output_file=ALL_OUTPUT_FILE)
    logging.info("=== 全部完成 ===")


if __name__ == "__main__":
    main()
