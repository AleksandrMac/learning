# graph/queries.py
from typing import List, Optional
from .models import DocumentGraph, GraphNode, NodeType, EdgeType, PointNode


class GraphQueries:
    """Базовые запросы к графу."""
    
    def __init__(self, graph: DocumentGraph):
        self.graph = graph
    
    def get_point(self, number: str) -> Optional[PointNode]:
        """Получить пункт по номеру."""
        for node in self.graph.nodes.values():
            if isinstance(node, PointNode) and node.number == number:
                return node
        return None
    
    def get_point_with_amendments(self, number: str) -> dict:
        """
        Получить пункт со всеми его изменениями.
        
        Returns:
            {
                'point': PointNode,
                'amendments': [AmendmentNode, ...],
                'references_to': [PointNode, ...],
                'references_from': [PointNode, ...]
            }
        """
        point = self.get_point(number)
        if not point:
            return {}
        
        # Находим amendments, которые применяют к этому пункту
        amendments = []
        for edge in self.graph.get_edges_to(point.id, EdgeType.AMENDS):
            amend_node = self.graph.get_node(edge.source_id)
            if amend_node:
                amendments.append(amend_node)
        
        # Находим пункты, на которые ссылается этот
        references_to = []
        for edge in self.graph.get_edges_from(point.id, EdgeType.REFERENCES):
            ref_node = self.graph.get_node(edge.target_id)
            if ref_node:
                references_to.append(ref_node)
        
        # Находим пункты, которые ссылаются на этот
        references_from = []
        for edge in self.graph.get_edges_to(point.id, EdgeType.REFERENCES):
            ref_node = self.graph.get_node(edge.source_id)
            if ref_node:
                references_from.append(ref_node)
        
        return {
            'point': point,
            'amendments': amendments,
            'references_to': references_to,
            'references_from': references_from,
        }
    
    def get_all_points(self) -> List[PointNode]:
        """Получить все пункты документа."""
        return [n for n in self.graph.nodes.values() if isinstance(n, PointNode)]
    
    def get_all_amendments(self) -> List[GraphNode]:
        """Получить все amendments."""
        return [n for n in self.graph.nodes.values() 
                if n.type == NodeType.AMENDMENT]
    
    def get_document_structure(self) -> dict:
        """
        Получить структуру документа в виде дерева.
        
        Returns:
            {
                'id': '...',
                'type': 'document',
                'title': '...',
                'children': [
                    {'id': '...', 'type': 'section', 'title': '...', 'children': [...]}
                ]
            }
        """
        # Находим корневой узел документа
        doc_node = None
        for node in self.graph.nodes.values():
            if node.type == NodeType.DOCUMENT:
                doc_node = node
                break
        
        if not doc_node:
            return {}
        
        return self._build_tree(doc_node.id)
    
    def _build_tree(self, node_id: str, depth: int = 0) -> dict:
        """Рекурсивно построить дерево."""
        node = self.graph.get_node(node_id)
        if not node:
            return {}
        
        if depth > 10:  # Защита от бесконечной рекурсии
            return {'id': node_id, 'type': node.type.value, 'truncated': True}
        
        children = self.graph.get_children(node_id)
        
        result = {
            'id': node_id,
            'type': node.type.value,
            'number': getattr(node, 'number', None),
            'title': getattr(node, 'title', None),
        }
        
        if children:
            result['children'] = [
                self._build_tree(c.id, depth + 1) for c in children
            ]
        
        return result
    
    def find_path(self, from_id: str, to_id: str, max_depth: int = 5) -> List[str]:
        """Найти кратчайший путь между узлами (BFS)."""
        from collections import deque
        
        if from_id == to_id:
            return [from_id]
        
        queue = deque([(from_id, [from_id])])
        visited = {from_id}
        
        while queue:
            current, path = queue.popleft()
            
            if len(path) > max_depth:
                continue
            
            # Ищем соседей через все типы рёбер
            neighbors = set()
            for edge in self.graph.edges:
                if edge.source_id == current:
                    neighbors.add(edge.target_id)
                elif edge.target_id == current:
                    neighbors.add(edge.source_id)
            
            for neighbor in neighbors:
                if neighbor == to_id:
                    return path + [neighbor]
                
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))
        
        return []  # Путь не найден
    
    def get_point_versions(self, number: str) -> List[PointNode]:
        """
        Получить все версии пункта.
        
        Returns:
            Список версий, отсортированный по версии (старая → новая)
        """
        versions = []
        
        for node in self.graph.nodes.values():
            if not isinstance(node, PointNode):
                continue
            
            if node.number != number:
                continue
            
            version_num = node.metadata.get('version', 1)
            versions.append((version_num, node))
        
        # Сортируем по версии
        versions.sort(key=lambda x: x[0])
        return [v[1] for v in versions]
    
    def get_current_version(self, number: str) -> Optional[PointNode]:
        """
        Получить текущую (последнюю) версию пункта.
        """
        versions = self.get_point_versions(number)
        return versions[-1] if versions else None
    
    def get_amendment_history(self, point_number: str) -> List[dict]:
        """
        Получить историю изменений пункта.
        
        Returns:
            [
                {
                    'amendment_id': '...',
                    'amendment_number': '...',
                    'action': 'replace',
                    'date': '...',
                    'old_text': '...',
                    'new_text': '...'
                },
                ...
            ]
        """
        history = []
        
        # Находим все amendments, которые ссылаются на этот пункт
        point_id = self._find_point_id_by_number(point_number)
        if not point_id:
            return history
        
        # Ищем рёбра AMENDS
        for edge in self.graph.get_edges_to(point_id, EdgeType.AMENDS):
            amend_node = self.graph.get_node(edge.source_id)
            if not amend_node or amend_node.type != NodeType.AMENDMENT:
                continue
            
            # Извлекаем детали замены
            old_text = None
            new_text = None
            
            for child_id in self.graph.get_edges_from(amend_node.id, EdgeType.CONTAINS):
                child = self.graph.get_node(child_id.target_id)
                if child and child.type == NodeType.REPLACEMENT:
                    old_text = getattr(child, 'old_text', None)
                    new_text = getattr(child, 'new_text', None)
                    break
            
            history.append({
                'amendment_id': amend_node.id,
                'amendment_number': getattr(amend_node, 'amendment_number', None),
                'action': getattr(amend_node, 'action', None),
                'date': getattr(amend_node, 'amendment_date', None),
                'old_text': old_text,
                'new_text': new_text
            })
        
        return history
    
    def get_point_with_context(self, number: str, include_versions: bool = True,
                               include_amendments: bool = True,
                               include_references: bool = True) -> dict:
        """
        Получить пункт с полным контекстом.
        
        Args:
            number: номер пункта
            include_versions: включить все версии
            include_amendments: включить историю изменений
            include_references: включить ссылки
        
        Returns:
            {
                'current': PointNode,
                'versions': [PointNode, ...],
                'amendments': [...],
                'references_to': [...],
                'references_from': [...],
                'superseded_by': [...],
                'supersedes': [...]
            }
        """
        current = self.get_current_version(number) if include_versions else self.get_point(number)
        if not current:
            return {}
        
        result = {
            'current': current,
        }
        
        if include_versions:
            result['versions'] = self.get_point_versions(number)
        
        if include_amendments:
            result['amendments'] = self.get_amendment_history(number)
        
        if include_references:
            # Ссылки на другие пункты
            refs_to = []
            for edge in self.graph.get_edges_from(current.id, EdgeType.REFERENCES):
                target = self.graph.get_node(edge.target_id)
                if target:
                    refs_to.append({
                        'point': target,
                        'type': edge.metadata.get('type', 'point'),
                        'context': edge.metadata
                    })
            
            # Ссылки от других пунктов
            refs_from = []
            for edge in self.graph.get_edges_to(current.id, EdgeType.REFERENCES):
                source = self.graph.get_node(edge.source_id)
                if source:
                    refs_from.append({
                        'point': source,
                        'type': edge.metadata.get('type', 'point'),
                        'context': edge.metadata
                    })
            
            result['references_to'] = refs_to
            result['references_from'] = refs_from
        
        # 🔹 Версионирование
        if include_versions:
            # Какие пункты эта версия заменяет
            supersedes = []
            for edge in self.graph.get_edges_from(current.id, EdgeType.SUPERSEDES):
                old_version = self.graph.get_node(edge.target_id)
                if old_version:
                    supersedes.append(old_version)
            
            # Какие версии заменяют эту
            superseded_by = []
            for edge in self.graph.get_edges_to(current.id, EdgeType.SUPERSEDES):
                new_version = self.graph.get_node(edge.source_id)
                if new_version:
                    superseded_by.append(new_version)
            
            result['supersedes'] = supersedes
            result['superseded_by'] = superseded_by
        
        return result
    
    def _find_point_id_by_number(self, number: str) -> Optional[str]:
        """Найти ID пункта по номеру."""
        for node_id, node in self.graph.nodes.items():
            if isinstance(node, PointNode) and node.number == number:
                return node_id
        return None