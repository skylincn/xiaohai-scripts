#!/usr/bin/env python3
"""
memory_search.py - 小海虾长期记忆检索工具
基于 TF-IDF + 余弦相似度，无需额外依赖库
用法: python3 memory_search.py "查询词" [--top N]
"""

import os
import json
import sys
import re
import math
from collections import Counter
from typing import List, Dict, Tuple

NAS_PATH = "/var/services/homes/skyyz/shared/coordination"
LOCAL_PATH = "/root/.openclaw/workspace/coordination"
MEMORY_FILE = "memory.json"


def load_memory() -> Dict:
    """加载记忆文件，优先从 NAS 拉取最新"""
    # 尝试 NAS
    try:
        nas_file = os.path.join(NAS_PATH, MEMORY_FILE)
        if os.path.exists(nas_file):
            with open(nas_file, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    
    # 降级到本地
    local_file = os.path.join(LOCAL_PATH, MEMORY_FILE)
    if os.path.exists(local_file):
        with open(local_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    return {"version": "1.0", "entries": []}


def tokenize(text: str) -> List[str]:
    """中英文分词（优化版：2-gram 中文 + 英文单词）"""
    text = text.lower()
    # 中文 2-gram（解决单字无意义问题）
    chinese = re.findall(r'[\u4e00-\u9fff]+', text)
    chinese_bigrams = []
    for chars in chinese:
        for i in range(len(chars) - 1):
            chinese_bigrams.append(chars[i:i+2])
    # 英文单词
    english = re.findall(r'[a-z0-9]+', text)
    return english + chinese_bigrams


def compute_tfidf(documents: List[str]) -> Tuple[List[List[float]], List[str]]:
    """
    计算 TF-IDF 向量
    documents: 文档列表，每篇文档是完整文本（如一个 entry 的 title+content）
    返回: (向量列表, 词汇表)
    """
    vocab = set()
    for doc in documents:
        vocab.update(tokenize(doc))
    vocab = sorted(list(vocab))
    vocab_map = {w: i for i, w in enumerate(vocab)}
    
    # TF: 词频 / 总词数
    vectors = []
    for doc in documents:
        tokens = tokenize(doc)
        tf = Counter(tokens)
        total = len(tokens) or 1
        vec = [0.0] * len(vocab)
        for word, count in tf.items():
            if word in vocab_map:
                vec[vocab_map[word]] = count / total
        vectors.append(vec)
    
    # IDF: log(总文档数 / 包含该词的文档数)
    n_docs = len(documents)
    doc_freq = Counter()
    for doc in documents:
        for word in set(tokenize(doc)):
            doc_freq[word] += 1
    
    idf = {}
    for word in vocab:
        df = doc_freq.get(word, 0) or 1  # 平滑
        idf[word] = math.log(n_docs / df)
    
    # 应用 IDF
    for vec in vectors:
        for i, w in enumerate(vocab):
            vec[i] *= idf.get(w, 0)
    
    return vectors, vocab


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """计算两个向量的余弦相似度"""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def search_memory(query: str, top_k: int = 5) -> List[Dict]:
    """
    在记忆中搜索最相关的结果
    返回 top_k 条记忆（按相关性排序）
    """
    memory = load_memory()
    entries = memory.get("entries", [])
    
    if not entries:
        return []
    
    # 构建文档文本（title + content + tags 拼接）
    documents = []
    for e in entries:
        text = " ".join(filter(None, [
            e.get("source", ""),      # 来源（如日期文件名）
            e.get("type", ""),         # 类型
            e.get("shrimp", ""),       # 来源虾
            e.get("content", "")      # 内容（最重要）
        ]))
        documents.append(text)
    
    # 计算 TF-IDF
    vectors, vocab = compute_tfidf(documents)
    
    # 查询向量
    query_tokens = tokenize(query)
    query_tf = Counter(query_tokens)
    query_vec = [0.0] * len(vocab)
    for word, count in query_tf.items():
        if word in vocab:
            query_vec[vocab.index(word)] = count / len(query_tokens)
    
    # 计算相似度
    scores = []
    for i, vec in enumerate(vectors):
        sim = cosine_similarity(query_vec, vec)
        scores.append((i, sim))
    
    # 排序
    scores.sort(key=lambda x: x[1], reverse=True)
    
    # 返回 top_k
    results = []
    for i, sim in scores[:top_k]:
        if sim > 0:
            entry = entries[i].copy()
            entry["_score"] = round(sim, 3)
            results.append(entry)
    
    return results


def display_results(results: List[Dict], query: str):
    """格式化输出"""
    print(f"\n{'='*60}")
    print(f"🔍 记忆检索: {query}")
    print(f"📋 找到 {len(results)} 条相关记忆")
    print(f"{'='*60}")
    
    if not results:
        print("（无相关记忆）")
        return
    
    for i, r in enumerate(results):
        score_bar = "█" * int(r['_score'] * 10) + "░" * (10 - int(r['_score'] * 10))
        print(f"\n[{i+1}] {r.get('type', '无分类') or r.get('source', '未知')}")
        print(f"    相似度: {r['_score']:.3f} [{score_bar}]")
        print(f"    来源: {r.get('source', '-')} | 虾: {r.get('shrimp', '-')} | 时间: {r.get('synced_at', '-')[:10]}")
        content = r.get('content', '')[:120]
        if content:
            print(f"    内容: {content}...")
    
    print(f"\n{'='*60}")


def auto_inject_context(query: str, threshold: float = 0.15) -> str:
    """
    自动注入上下文到查询中
    阈值 0.15 = 相似度 > 15% 的记忆会被注入
    返回格式化的上下文字符串
    """
    results = search_memory(query, top_k=3)
    
    if not results or results[0]['_score'] < threshold:
        return ""  # 无相关记忆，不注入
    
    context_parts = []
    context_parts.append("【相关记忆背景】")
    
    for r in results:
        if r['_score'] >= threshold:
            context_parts.append(
                f"- [{r.get('source', '未知')}] {r.get('title', '')}: {r.get('content', '')[:80]}..."
            )
    
    return "\n".join(context_parts)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="小海虾记忆检索")
    parser.add_argument("query", help="检索词")
    parser.add_argument("--top", "-n", type=int, default=5, help="返回数量")
    parser.add_argument("--json", "-j", action="store_true", help="JSON输出")
    
    args = parser.parse_args()
    
    results = search_memory(args.query, args.top)
    
    if args.json:
        print(json.dumps({"query": args.query, "results": results}, ensure_ascii=False, indent=2))
    else:
        display_results(results, args.query)