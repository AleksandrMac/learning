import numpy as np
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any
from graph.models import DocumentGraph, GraphNode, NodeType


class GraphRetriever:
    """
    Гибридный Retriever для DocumentGraph.
    Объединяет семантический поиск с графовой навигацией.
    """
    
    def __init__(self, graph: DocumentGraph, model_name: str = "sentence-transformers/LaBSE", device: str ="cpu"):
        self.graph = graph
        self.model = SentenceTransformer(model_name, device=device)
        self.device = device

        # In-memory векторный индекс
        self.node_ids: List[str] = []
        self.node_texts: List[str] = []
        self.node_embeddings: np.ndarray = None
        
        self._build_vector_index()
    
    def _build_vector_index(self):
        """Индексирует текстовые узлы графа."""
        text_nodes = self.graph.get_all_text_nodes()
        
        self.node_ids = [node.id for node in text_nodes]
        self.node_texts = [node.text for node in text_nodes]
        
        if self.node_texts:
            self.node_embeddings = self.model.encode(
                self.node_texts, 
                convert_to_numpy=True,
                show_progress_bar=False,
                device=self.device
            )
    
    # ═══════════════════════════════════════════════════════
    # 1. СЕМАНТИЧЕСКИЙ ПОИСК
    # ═══════════════════════════════════════════════════════
    def semantic_search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Находит узлы по смыслу вопроса."""
        if self.node_embeddings is None:
            return []
        
        query_emb = self.model.encode([query], convert_to_numpy=True, device=self.device)
        similarities = np.dot(self.node_embeddings, query_emb.T).flatten()
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            node_id = self.node_ids[idx]
            node = self.graph.get_node(node_id)
            parent = self.graph.get_parent(node_id)
            
            results.append({
                'node': node,
                'score': float(similarities[idx]),
                'section': parent.title if parent else None,
            })
        return results
    
    # ═══════════════════════════════════════════════════════
    # 2. СТРУКТУРНЫЙ ПОИСК
    # ═══════════════════════════════════════════════════════
    def get_point_with_context(self, point_id: str) -> Dict[str, Any]:
        """Возвращает пункт с полным контекстом."""
        return self.graph.get_full_context(point_id)
    
    def get_point_history(self, point_id: str) -> List[Dict[str, Any]]:
        """Возвращает историю изменений пункта."""
        return self.graph.get_point_history(point_id)
    
    # ═══════════════════════════════════════════════════════
    # 3. ГИБРИДНЫЙ ЗАПРОС (для LLM)
    # ═══════════════════════════════════════════════════════
    def retrieve_context(self, query: str, top_k: int = 3, include_history: bool = False) -> str:
        """
        Формирует финальный контекст для промпта LLM.
        
        Args:
            query: Вопрос пользователя
            top_k: Количество релевантных пунктов
            include_history: Включать ли историю изменений
        """
        results = self.semantic_search(query, top_k=top_k)
        
        context_parts = []
        for res in results:
            node = res['node']
            
            # Формируем заголовок
            part = f"[{node.type.value.upper()} {node.number}]"
            if res.get('section'):
                part += f" (Раздел: {res['section']})"
            part += f"\n{node.text}\n"
            
            # Опционально добавляем историю
            if include_history:
                history = self.get_point_history(node.id)
                if history:
                    part += "\n📜 История изменений:\n"
                    for h in history:
                        part += f"  - Поправка №{h['amendment_id']} ({h['action']}): "
                        if h.get('old_text'):
                            part += f"было «{h['old_text']}» → стало «{h['new_text']}»\n"
                        else:
                            part += f"«{h['new_text']}»\n"
            
            context_parts.append(part)
        
        return "\n---\n".join(context_parts)