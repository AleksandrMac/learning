# graph/models.py
from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════
# 🔹 Типы узлов графа
# ═══════════════════════════════════════════════════════

class NodeType(str, Enum):
    DOCUMENT = 'document'
    SECTION = 'section'
    POINT = 'point'
    PARAGRAPH = 'paragraph'
    FORMULA = 'formula'
    DEFINITION = 'definition'
    AMENDMENT = 'amendment'
    REPLACEMENT = 'replacement'


# ═══════════════════════════════════════════════════════
# 🔹 Типы рёбер графа
# ═══════════════════════════════════════════════════════

class EdgeType(str, Enum):
    CONTAINS = 'contains'       # Структурная вложенность
    AMENDS = 'amends'           # Amendment → целевой Point
    REFERENCES = 'references'   # Point → Point (ссылка в тексте)
    SUPERSEDES = 'supersedes'   # Новая версия → старая
    DEFINES = 'defines'         # Point → Definition
    USES_TERM = 'uses_term'     # Point → Definition (использование)


# ═══════════════════════════════════════════════════════
# 🔹 Базовая модель узла
# ═══════════════════════════════════════════════════════

class GraphNode(BaseModel):
    """Базовый узел графа."""
    id: str                                    # Уникальный ID (например, "doc:methodika_421/point:14")
    type: NodeType
    number: Optional[str] = None               # Номер (14, а, I, ...)
    level: Optional[int] = None                # Уровень вложенности
    text: Optional[str] = None                 # Текстовое содержимое
    title: Optional[str] = None                # Заголовок (для Section, Document)
    metadata: Dict[str, Any] = Field(default_factory=dict)  # Дополнительные данные
    created_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        frozen = False


# ═══════════════════════════════════════════════════════
# 🔹 Специализированные узлы
# ═══════════════════════════════════════════════════════

class DocumentNode(GraphNode):
    """Корневой узел документа."""
    type: NodeType = NodeType.DOCUMENT
    title: str
    version: Optional[str] = None
    date: Optional[str] = None
    source_file: Optional[str] = None


class SectionNode(GraphNode):
    """Раздел документа (I, II, ...)."""
    type: NodeType = NodeType.SECTION
    title: str
    roman_number: Optional[str] = None  # I, II, III, ...


class PointNode(GraphNode):
    """Пункт документа."""
    type: NodeType = NodeType.POINT
    number: str
    level: int = 1
    text: str = ''
    section_id: Optional[str] = None  # ID раздела, к которому принадлежит


class ParagraphNode(GraphNode):
    """Абзац внутри пункта."""
    type: NodeType = NodeType.PARAGRAPH
    number: str  # Номер абзаца (1, 2, ...)
    text: str
    point_id: str  # ID родительского пункта


class FormulaNode(GraphNode):
    """Формула."""
    type: NodeType = NodeType.FORMULA
    latex: str
    tag: Optional[str] = None  # Номер формулы (1), (2), ...


class DefinitionNode(GraphNode):
    """Определение термина."""
    type: NodeType = NodeType.DEFINITION
    term: str
    definition: str
    defined_in_point_id: str


class AmendmentNode(GraphNode):
    """Изменение к документу."""
    type: NodeType = NodeType.AMENDMENT
    amendment_number: str  # Номер изменения (1, 2, ...)
    action: str  # replace, add, exclude, composite, ...
    target_point_ids: List[str] = Field(default_factory=list)  # ID целевых пунктов
    amendment_date: Optional[str] = None
    source_text: Optional[str] = None


class ReplacementNode(GraphNode):
    """Конкретная замена в amendment."""
    type: NodeType = NodeType.REPLACEMENT
    old_text: Optional[str] = None
    new_text: Optional[str] = None
    anchor: Optional[str] = None  # Для AddAmendment
    amendment_id: str  # ID родительского amendment


# ═══════════════════════════════════════════════════════
# 🔹 Модель ребра
# ═══════════════════════════════════════════════════════

class GraphEdge(BaseModel):
    """Ребро графа."""
    source_id: str
    target_id: str
    type: EdgeType
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        frozen = False


# ═══════════════════════════════════════════════════════
# 🔹 Полный граф
# ═══════════════════════════════════════════════════════

class DocumentGraph(BaseModel):
    """Полный граф документа."""
    nodes: Dict[str, GraphNode] = Field(default_factory=dict)
    edges: List[GraphEdge] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def add_node(self, node: GraphNode) -> None:
        """Добавить узел в граф."""
        self.nodes[node.id] = node
    
    def add_edge(self, edge: GraphEdge) -> None:
        """Добавить ребро в граф."""
        # Проверяем, что оба узла существуют
        if edge.source_id not in self.nodes:
            raise ValueError(f"Source node {edge.source_id} not found")
        if edge.target_id not in self.nodes:
            raise ValueError(f"Target node {edge.target_id} not found")
        self.edges.append(edge)
    
    def get_node(self, node_id: str) -> Optional[GraphNode]:
        """Получить узел по ID."""
        return self.nodes.get(node_id)
    
    def get_edges_from(self, node_id: str, edge_type: Optional[EdgeType] = None) -> List[GraphEdge]:
        """Получить все рёбра, исходящие из узла."""
        result = []
        for edge in self.edges:
            if edge.source_id == node_id:
                if edge_type is None or edge.type == edge_type:
                    result.append(edge)
        return result
    
    def get_edges_to(self, node_id: str, edge_type: Optional[EdgeType] = None) -> List[GraphEdge]:
        """Получить все рёбра, входящие в узел."""
        result = []
        for edge in self.edges:
            if edge.target_id == node_id:
                if edge_type is None or edge.type == edge_type:
                    result.append(edge)
        return result
    
    def get_children(self, node_id: str) -> List[GraphNode]:
        """Получить дочерние узлы (через CONTAINS)."""
        edges = self.get_edges_from(node_id, EdgeType.CONTAINS)
        return [self.nodes[e.target_id] for e in edges if e.target_id in self.nodes]
    
    def get_parent(self, node_id: str) -> Optional[GraphNode]:
        """Получить родительский узел (через CONTAINS)."""
        edges = self.get_edges_to(node_id, EdgeType.CONTAINS)
        if edges:
            return self.nodes.get(edges[0].source_id)
        return None
    
    def to_dict(self) -> Dict:
        """Сериализация в словарь."""
        return {
            'nodes': {k: v.model_dump() for k, v in self.nodes.items()},
            'edges': [e.model_dump() for e in self.edges],
            'metadata': self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'DocumentGraph':
        """Десериализация из словаря."""
        nodes = {}
        for node_id, node_data in data['nodes'].items():
            node_type = node_data['type']
            # Выбираем правильный класс узла
            node_class = {
                NodeType.DOCUMENT: DocumentNode,
                NodeType.SECTION: SectionNode,
                NodeType.POINT: PointNode,
                NodeType.PARAGRAPH: ParagraphNode,
                NodeType.FORMULA: FormulaNode,
                NodeType.DEFINITION: DefinitionNode,
                NodeType.AMENDMENT: AmendmentNode,
                NodeType.REPLACEMENT: ReplacementNode,
            }[node_type]
            nodes[node_id] = node_class(**node_data)
        
        edges = [GraphEdge(**e) for e in data['edges']]
        
        return cls(
            nodes=nodes,
            edges=edges,
            metadata=data.get('metadata', {})
        )

    def get_all_text_nodes(self) -> List[GraphNode]:
        """Получить все узлы с текстом (для векторной индексации)."""
        text_nodes = []
        for node in self.nodes.values():
            if node.type in [NodeType.POINT, NodeType.PARAGRAPH, NodeType.SECTION]:
                if node.text:  # Только если есть текст
                    text_nodes.append(node)
        return text_nodes
    
    def get_amendments_for_point(self, point_id: str) -> List[AmendmentNode]:
        """
        Получить все поправки, которые изменяют этот пункт.
        Использует рёбра AMENDS (Amendment → Point).
        """
        amendments = []
        # Ищем рёбра AMENDS, входящие в point_id
        for edge in self.get_edges_to(point_id, EdgeType.AMENDS):
            amendment_node = self.nodes.get(edge.source_id)
            if amendment_node and amendment_node.type == NodeType.AMENDMENT:
                amendments.append(amendment_node)
        return amendments
    
    def get_replacements_for_point(self, point_id: str) -> List[ReplacementNode]:
        """Получить конкретные замены для пункта."""
        replacements = []
        for edge in self.get_edges_to(point_id, EdgeType.AMENDS):
            # Проверяем, есть ли ребро от Replacement к Point
            replacement_node = self.nodes.get(edge.source_id)
            if replacement_node and replacement_node.type == NodeType.REPLACEMENT:
                replacements.append(replacement_node)
        return replacements
    
    def get_related_points(self, point_id: str) -> List[PointNode]:
        """Получить пункты, на которые ссылается этот пункт (через REFERENCES)."""
        related = []
        for edge in self.get_edges_from(point_id, EdgeType.REFERENCES):
            target_node = self.nodes.get(edge.target_id)
            if target_node and target_node.type == NodeType.POINT:
                related.append(target_node)
        return related
    
    def get_point_history(self, point_id: str) -> List[Dict[str, Any]]:
        """
        Получить историю изменений пункта (генерация на лету).
        Возвращает список изменений с old_text, new_text, датой.
        """
        history = []
        
        # Получаем все поправки для этого пункта
        amendments = self.get_amendments_for_point(point_id)
        
        for amendment in amendments:
            # Получаем замены из этой поправки
            replacements = self.get_replacements_for_point(point_id)
            for replacement in replacements:
                if replacement.amendment_id == amendment.amendment_number:
                    history.append({
                        'amendment_id': amendment.amendment_number,
                        'action': amendment.action,
                        'old_text': replacement.old_text,
                        'new_text': replacement.new_text,
                        'anchor': replacement.anchor,
                        'date': amendment.amendment_date,
                    })
        
        # Сортируем по дате (от новых к старым)
        return sorted(history, key=lambda x: x.get('date', ''), reverse=True)
    
    def get_full_context(self, point_id: str) -> Dict[str, Any]:
        """Получить пункт с полным контекстом (раздел, история, связи)."""
        node = self.get_node(point_id)
        if not node:
            return {'error': 'Point not found'}
        
        parent = self.get_parent(point_id)
        related = self.get_related_points(point_id)
        history = self.get_point_history(point_id)
        
        return {
            'node': node,
            'section': parent.title if parent else None,
            'related_points': [p.number for p in related],
            'history': history,
        }