"""
Chroma 向量存储封装 — 知识条目的 Embedding 存储与检索
使用百炼 API 的 Embedding（通过 HTTP 直接调用）
"""
import os
from pathlib import Path
import requests
import chromadb
from chromadb.config import Settings


# 持久化路径：默认项目根目录下的 data/chroma，可通过环境变量 CHROMA_PATH 覆盖
_DEFAULT_CHROMA_PATH = str(
    Path(__file__).resolve().parent.parent.parent.parent / "data" / "chroma"
)
CHROMA_PATH = os.getenv("CHROMA_PATH", _DEFAULT_CHROMA_PATH)
COLLECTION_NAME = "ticket_knowledge"


class DirectEmbedding:
    """直接 HTTP 调用百炼 Embedding API"""

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.url = base_url.rstrip("/") + "/embeddings"
        self.model = "text-embedding-v3"
        self.dimensions = 1024

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)

    def embed_documents(self, texts: list[str]) -> list[float]:
        return [self._embed(t) for t in texts]

    def _embed(self, text: str) -> list[float]:
        resp = requests.post(
            self.url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "input": text,
                "dimensions": self.dimensions,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["data"][0]["embedding"]


def _get_embedding_fn():
    return DirectEmbedding()


# 全局客户端（懒加载）
_client = None  # type: chromadb.PersistentClient | None
_collection = None  # type: chromadb.Collection | None
_embedding_fn = None


def _get_client() -> chromadb.PersistentClient:
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(
            path=CHROMA_PATH,
            settings=Settings(anonymized_telemetry=False),
        )
    return _client


def _get_collection() -> chromadb.Collection:
    global _collection
    if _collection is None:
        client = _get_client()
        _collection = client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"description": "售后工单知识库"},
        )
    return _collection


def _get_embedding():
    global _embedding_fn
    if _embedding_fn is None:
        _embedding_fn = _get_embedding_fn()
    return _embedding_fn


def add_knowledge(
    knowledge_id: str,
    title: str,
    problem_description: str = "",
    root_cause: str = "",
    symptoms: str = "",
    solution: str = "",
    steps: list[str] | None = None,
    prevention: str = "",
    tags: list[str] | None = None,
    category: str = "",
    difficulty: str = "",
    metadata: dict | None = None,
) -> bool:
    """
    将知识条目存入向量库（四段式结构：问题→原因→现象→方案）。

    Args:
        knowledge_id: 知识条目唯一标识
        title: 标题
        problem_description: 问题描述
        root_cause: 发生原因
        symptoms: 可能产生的现象
        solution: 解决方法参考
        steps: 操作步骤列表
        prevention: 预防措施
        tags: 标签列表
        category: 分类
        difficulty: 难度
        metadata: 额外元数据

    Returns:
        是否成功
    """
    try:
        collection = _get_collection()
        embedding_fn = _get_embedding()

        tag_text = " ".join(tags) if tags else ""

        # 组合搜索文本：标题 + 标签 + 问题描述 + 原因 + 现象 + 方案
        search_text = f"{title} {tag_text} {problem_description} {root_cause} {symptoms} {solution}"

        # 生成 Embedding 向量
        vector = embedding_fn.embed_query(search_text)

        # 准备元数据（完整四段式结构）
        doc_metadata = metadata or {}
        doc_metadata.update({
            "title": title,
            "tags": ", ".join(tags) if tags else "",
            "category": category,
            "difficulty": difficulty,
            "problem_description": problem_description[:500],
            "root_cause": root_cause[:500],
            "symptoms": symptoms[:500],
            "solution": solution[:500],
            "steps": " | ".join(steps) if steps else "",
            "prevention": prevention[:300],
        })

        # 存入 Chroma（upsert 模式：存在则更新）
        collection.upsert(
            ids=[knowledge_id],
            embeddings=[vector],
            documents=[search_text],
            metadatas=[doc_metadata],
        )
        return True
    except Exception as e:
        print(f"[VectorStore] 添加知识条目失败: {e}")
        return False


def search_similar(
    query: str,
    top_k: int = 5,
) -> list[dict]:
    """
    搜索相似知识条目。

    Args:
        query: 查询文本
        top_k: 返回数量

    Returns:
        [{"id": ..., "title": ..., "summary": ..., "tags": ..., "similarity": 0.95}, ...]
    """
    try:
        collection = _get_collection()
        embedding_fn = _get_embedding()

        query_vector = embedding_fn.embed_query(query)

        results = collection.query(
            query_embeddings=[query_vector],
            n_results=top_k,
            include=["metadatas", "documents", "distances"],
        )

        items = []
        if results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                metadata = (results["metadatas"] or [[]])[0]
                distances = (results["distances"] or [[]])[0]
                distance = distances[i] if i < len(distances) else 1.0
                similarity = max(0, 1 - distance)

                meta = metadata[i] if i < len(metadata) else {}
                items.append({
                    "id": doc_id,
                    "title": meta.get("title", ""),
                    "summary": meta.get("problem_description", "")[:200],
                    "tags": meta.get("tags", "").split(", ") if meta.get("tags") else [],
                    "category": meta.get("category", ""),
                    "difficulty": meta.get("difficulty", ""),
                    "similarity": round(similarity, 4),
                    "ticket_id": meta.get("ticket_id"),
                })
        return items
    except Exception as e:
        print(f"[VectorStore] 检索失败: {e}")
        return []


def get_knowledge_count() -> int:
    """获取知识库条目数量"""
    try:
        collection = _get_collection()
        return collection.count()
    except Exception:
        return 0


def list_all_knowledge(
    keyword: str = "",
    category: str = "",
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """
    分页获取知识库条目列表，支持关键词搜索。
    """
    try:
        collection = _get_collection()
        result = collection.get(include=["metadatas", "documents"])

        items = []
        if result["ids"]:
            for i, doc_id in enumerate(result["ids"]):
                meta = (result["metadatas"] or [{}])[i] if i < len(result.get("metadatas") or []) else {}
                doc = (result["documents"] or [""])[i] if i < len(result.get("documents") or []) else ""
                items.append({
                    "id": doc_id,
                    "title": meta.get("title", ""),
                    "problem_description": meta.get("problem_description", ""),
                    "root_cause": meta.get("root_cause", ""),
                    "symptoms": meta.get("symptoms", ""),
                    "solution": meta.get("solution", ""),
                    "steps": meta.get("steps", ""),
                    "prevention": meta.get("prevention", ""),
                    "tags": meta.get("tags", ""),
                    "category": meta.get("category", ""),
                    "difficulty": meta.get("difficulty", ""),
                    "ticket_id": meta.get("ticket_id"),
                    "document": doc,
                })

        # 筛选
        if keyword:
            kw = keyword.lower()
            items = [
                it for it in items
                if kw in it["title"].lower()
                or kw in it["problem_description"].lower()
                or kw in it["root_cause"].lower()
                or kw in it["symptoms"].lower()
                or kw in it["solution"].lower()
            ]
        if category:
            items = [it for it in items if it["category"] == category]

        total = len(items)

        # 分页
        start = (page - 1) * page_size
        end = start + page_size
        page_items = items[start:end]

        return {
            "items": page_items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    except Exception as e:
        print(f"[VectorStore] 列表查询失败: {e}")
        return {"items": [], "total": 0, "page": page, "page_size": page_size}


def get_knowledge_by_id(knowledge_id: str) -> dict | None:
    """
    根据 ID 获取单条知识条目详情（完整四段式结构）。
    """
    try:
        collection = _get_collection()
        result = collection.get(
            ids=[knowledge_id],
            include=["metadatas", "documents"],
        )
        if result["ids"]:
            meta = (result["metadatas"] or [{}])[0]
            doc = (result["documents"] or [""])[0]
            return {
                "id": result["ids"][0],
                "title": meta.get("title", ""),
                "problem_description": meta.get("problem_description", ""),
                "root_cause": meta.get("root_cause", ""),
                "symptoms": meta.get("symptoms", ""),
                "solution": meta.get("solution", ""),
                "steps": meta.get("steps", ""),
                "prevention": meta.get("prevention", ""),
                "tags": meta.get("tags", ""),
                "category": meta.get("category", ""),
                "difficulty": meta.get("difficulty", ""),
                "ticket_id": meta.get("ticket_id"),
                "document": doc,
            }
        return None
    except Exception as e:
        print(f"[VectorStore] 详情查询失败: {e}")
        return None
