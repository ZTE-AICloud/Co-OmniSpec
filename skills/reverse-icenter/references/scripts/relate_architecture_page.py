import json

import requests
import logging as log
from typing import List, Dict, Any
import os
import sys

if __name__ == "__main__":
    _script_dir = os.path.dirname(os.path.abspath(__file__))
    _scripts_python = os.path.dirname(_script_dir)
    if _scripts_python not in sys.path:
        sys.path.insert(0, _scripts_python)

from common import read_json, write_obj, get_md_title_tree_or_prefix_content, \
    CACHE_PATH, PAGE_IDS_FILE, PAGE_FILE_PATH, read_file, ARCHITECTURE_DOC_LINKS_FILE, script_pre_check


def get_page_description(page_data_list: List[Dict]) -> List[Dict[str, Any]]:
    for page in page_data_list:
        space_id, page_id = page['id'].split('-')
        content = read_file(f'{PAGE_FILE_PATH}/{space_id}-{page_id}.md')
        page['content'] = get_md_title_tree_or_prefix_content(content)
    return page_data_list


def get_embeddings(texts: List) -> List[Dict]:
    url = "https://maas-apigateway.dt.zte.com.cn/model/qwen3-embedding-8b/v1/embeddings"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer upok0xtsxztb51d98va286pn39c77wnz"
    }
    payload = {
        "model": "Qwen3-Embedding-8B",
        "input": [text if isinstance(text, str) else json.dumps(text, ensure_ascii=False) for text in texts]
    }

    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()

    return response.json()["data"]


def transfer_page_embedded_data(data_items: List[Dict[str, Any]], embeddings: List[Dict]) -> List[Dict]:
    result = []
    for i, item in enumerate(data_items):

        embedding_data = embeddings[i]
        if embedding_data:
            result.append({
                "id": item["id"],
                "embedding": embedding_data["embedding"]
            })
    return result


def embed_page():
    data = read_json(PAGE_IDS_FILE)
    log.info(f"start to embed {len(data)} pages")
    page_data_list = get_page_description(data)
    texts = [{'name': item['name'], 'content': item['content']} for item in page_data_list]

    batch_size = 300
    all_embeddings = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        try:
            embeddings = get_embeddings(batch)
            all_embeddings.extend(embeddings)
        except Exception as e:
            log.error(f"处理批次时出错: {e}")
            return []

    page_embedded_info = transfer_page_embedded_data(page_data_list, all_embeddings)
    # write_obj('page_embedding_data.json', page_embedded_info)
    return page_embedded_info


def embed_architecture(architecture: list):
    return get_embeddings(architecture)


def calculate_cosine_similarity(query_embedding, db_embeddings):
    import numpy as np

    # 将列表转换为numpy数组
    query_vec = np.array(query_embedding)
    db_matrix = np.array(db_embeddings)

    # 余弦相似度 = (A·B) / (||A|| * ||B||)
    dot_products = np.dot(db_matrix, query_vec)

    # 计算范数
    query_norm = np.linalg.norm(query_vec)
    db_norms = np.linalg.norm(db_matrix, axis=1)

    # 避免除零错误
    similarities = dot_products / (query_norm * db_norms + 1e-10)

    return similarities


def find_top_k_matches(query_embedding, page_embeddings, page_ids, k):
    similarities = calculate_cosine_similarity(query_embedding, page_embeddings)
    similarity_id_pairs = list(zip(similarities, page_ids))
    similarity_id_pairs.sort(key=lambda x: x[0], reverse=True)
    top_k = similarity_id_pairs[:k]

    return [(page_id.split('-'), similarity) for similarity, page_id in top_k]


def relate():
    page_embedded_info = embed_page()
    page_embedded_data = [i['embedding'] for i in page_embedded_info]
    page_ids = [i['id'] for i in page_embedded_info]
    architecture = read_json('.cache/icenter/architecture_flattened.json')
    log.info(f"开始将 {len(architecture)} 个架构节点和 {len(page_embedded_data)} 个文档进行关联")
    embedded_architecture_list = embed_architecture(architecture)

    for idx, arch_item in enumerate(embedded_architecture_list):
        query_embedding = arch_item['embedding']
        top_k_matches = find_top_k_matches(query_embedding, page_embedded_data, page_ids, 50)
        architecture_node = architecture[idx]
        architecture_node['matches'] = [page_id for page_id, _ in top_k_matches]
        node_name = architecture_node['name'].split('-')[-1]
        write_obj(f'{ARCHITECTURE_DOC_LINKS_FILE}/{node_name}.json', architecture_node)


    embedded_whole_architecture_embedding = get_embeddings([architecture])[0]['embedding']
    top_k_matches = find_top_k_matches(embedded_whole_architecture_embedding, page_embedded_data, page_ids, 100)
    write_obj(f'{CACHE_PATH}/related_page_ids.json', [page_id for page_id, _ in top_k_matches])

    print(f"所有匹配结果已保存到 {ARCHITECTURE_DOC_LINKS_FILE}/ 目录下")


def _main():
    script_pre_check()
    relate()


if __name__ == "__main__":
    _main()
