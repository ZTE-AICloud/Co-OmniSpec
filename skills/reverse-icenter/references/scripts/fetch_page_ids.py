import json
import logging as log
import os
import sys

if __name__ == "__main__":
    _script_dir = os.path.dirname(os.path.abspath(__file__))
    _scripts_python = os.path.dirname(_script_dir)
    if _scripts_python not in sys.path:
        sys.path.insert(0, _scripts_python)

from common import ICenterClient, write_file, PAGE_IDS_FILE, parse_icenter_url


def fetch_all_page_ids(page_info_list):
    client = ICenterClient()

    log.info("开始获取所有子页面 ID")
    page_info = client.get_all_children_pages(page_info_list)
    log.info("共获取 %s 个子页面", len(page_info))

    write_file(PAGE_IDS_FILE, json.dumps(transfer_page_info(page_info), ensure_ascii=False, indent=2))
    log.info("已写入 %s", PAGE_IDS_FILE)


def transfer_page_info(page_info_list):
    page_index = {f"{i['space_id']}-{i['id']}": i for i in page_info_list}

    name_path_cache = {}

    def get_name_path(_id):
        cur_item = page_index.get(_id)
        if not cur_item:
            return []
        parent_id = cur_item.get("parent_id")
        current_name = cur_item.get("name")

        if not parent_id:
            path = [current_name] if current_name is not None else []
        else:
            parent_item = page_index.get(_id)
            if parent_item:
                full_parent_id = f"{parent_item.get("space_id")}-{parent_item.get("parent_id")}"
                parent_path = get_name_path(full_parent_id)
                path = parent_path + ([current_name] if current_name is not None else [])
            else:
                path = [current_name] if current_name is not None else []

        name_path_cache[_id] = path
        return path

    page_info = []
    for item in page_info_list:
        _id = f"{item['space_id']}-{item['id']}"
        name_path = get_name_path(_id)
        page_info.append({"id": _id, "name": name_path, })

    return page_info


def script_pre_check():
    import sys
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True, help="仓库根目录")
    parser.add_argument(
        "--page-root",
        required=True,
        help="iCenter 根页面，格式为iCenter url，以逗号分割多个目录",
    )
    args = parser.parse_args()

    repo_root = os.path.abspath(args.repo_root)
    if not os.path.isdir(repo_root):
        log.error(f"错误：仓库根目录不存在: {repo_root}")
        sys.exit(1)
    os.chdir(repo_root)

    return args


def _main():
    args = script_pre_check()
    page_roots = getattr(args, "page_root", '')
    page_roots = page_roots.split(',')
    page_info_list = [parse_icenter_url(i) for i in page_roots]
    if not page_info_list:
        raise ValueError(f"无效的 --page-root 参数 {page_roots}")
    fetch_all_page_ids(page_info_list)


if __name__ == "__main__":
    _main()
