import requests
import os
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- 配置 ---

# 热门 tracker
BEST_TRACKER_URLS = [
    "https://cdn.jsdelivr.net/gh/ngosang/trackerslist@master/trackers_best.txt",
    "https://cf.trackerslist.com/best.txt"
]

# 全量 tracker（冷门用）
ALL_TRACKER_URLS = [
    "https://cdn.jsdelivr.net/gh/ngosang/trackerslist@master/trackers_all.txt",
    "https://cf.trackerslist.com/all.txt"
]

BEST_OUTPUT_FILE = "tracker.txt"
ALL_OUTPUT_FILE = "all_trackers.txt"

# --- 日志 ---
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s"
)

# --- Session ---
session = requests.Session()


def fetch_trackers_from_url(url):
    try:
        response = session.get(url, timeout=10)
        response.raise_for_status()

        trackers = {
            line.strip()
            for line in response.text.splitlines()
            if line.strip()
        }

        logging.info(f"[OK] {url} -> {len(trackers)}")
        return trackers

    except requests.RequestException as e:
        logging.error(f"[FAIL] {url} -> {e}")
        return set()


def fetch_all_trackers(urls):
    all_trackers = set()
    failed = []

    with ThreadPoolExecutor(max_workers=len(urls)) as executor:
        futures = {executor.submit(fetch_trackers_from_url, url): url for url in urls}

        for future in as_completed(futures):
            url = futures[future]
            result = future.result()

            if result:
                all_trackers.update(result)
            else:
                failed.append(url)

    if failed:
        logging.warning(f"失败源: {failed}")

    return all_trackers


def read_old_trackers(file_path):
    if not os.path.exists(file_path):
        return set()

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return {line.strip() for line in f if line.strip()}
    except IOError as e:
        logging.error(f"读取失败 {file_path}: {e}")
        return set()


def save_trackers(file_path, trackers):
    try:
        with open(file_path, 'w', encoding='utf-8', newline='\n') as f:
            f.write('\n'.join(sorted(trackers)))

        logging.info(f"写入 {file_path} 完成: {len(trackers)} 条")

    except IOError as e:
        logging.error(f"写入失败 {file_path}: {e}")


def process_tracker_group(name, urls, output_file):
    logging.info(f"=== 处理 {name} ===")

    new_trackers = fetch_all_trackers(urls)

    if not new_trackers:
        logging.error(f"{name} 未获取到数据")
        return

    logging.info(f"{name} 共 {len(new_trackers)} 个 tracker")

    old_trackers = read_old_trackers(output_file)

    if old_trackers:
        added = new_trackers - old_trackers

        if added:
            logging.info(f"{name} 新增 {len(added)} 个:")
            for i, t in enumerate(sorted(added), 1):
                print(f"[{name}] {i}. {t}")
        else:
            logging.info(f"{name} 无新增")

    save_trackers(output_file, new_trackers)


def main():
    logging.info("=== Tracker 更新开始 ===")

    # 热门（适合热门资源）
    process_tracker_group(
        name="BEST",
        urls=BEST_TRACKER_URLS,
        output_file=BEST_OUTPUT_FILE
    )

    print()

    # 全量（适合冷门资源）
    process_tracker_group(
        name="ALL",
        urls=ALL_TRACKER_URLS,
        output_file=ALL_OUTPUT_FILE
    )

    logging.info("=== 全部完成 ===")


if __name__ == "__main__":
    main()
