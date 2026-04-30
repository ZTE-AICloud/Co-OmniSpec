import logging as log
import os
import sys

if __name__ == "__main__":
    _script_dir = os.path.dirname(os.path.abspath(__file__))
    _scripts_python = os.path.dirname(_script_dir)
    if _scripts_python not in sys.path:
        sys.path.insert(0, _scripts_python)

from common import ICenterClient, PAGE_IDS_FILE, read_json, concurrent_execute, \
    script_pre_check


def fetch_pages_to_local():
    """读取子页面 ID 列表，将每个页面内容保存到本地 page/ 目录。
    """
    client = ICenterClient()

    page_info = read_json(PAGE_IDS_FILE)

    page_params = [item['id'].split('-') for item in page_info]
    log.info("开始拉取 %s 个页面到本地", len(page_params))
    concurrent_execute(client.save_page_detail, page_params)
    log.info("页面拉取完成")


def _main():
    script_pre_check()

    fetch_pages_to_local()


if __name__ == "__main__":
    _main()
