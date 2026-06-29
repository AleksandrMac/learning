import re
from typing import List, Optional
from .models import (
    DocumentGraph, GraphNode, GraphEdge, NodeType, EdgeType,
    DocumentNode, SectionNode, PointNode, ParagraphNode,
    FormulaNode, DefinitionNode, AmendmentNode, ReplacementNode
)
from nodes.base import BaseNode
from nodes.concrete import PointNode as ParsedPointNode, SectionNode as ParsedSectionNode, ParagraphNode as ParsedParagraphNode
from nodes.amendments import (
    AmendmentNode as ParsedAmendmentNode,
    ReplaceAmendmentNode, AddAmendmentNode, ExcludeAmendmentNode,
    ReplaceWordsAmendmentNode, MultipleReplaceWordsAmendmentNode,
    AddParagraphAmendmentNode, AddPointsAmendmentNode, AddSectionAmendmentNode,
    AddSubpointAmendmentNode, RepealAmendmentNode
)
from nodes.target import TargetAddress, ComponentType


class GraphBuilder:
    """
    Строит граф документа из распарсенных узлов.
    
    Usage:
        builder = GraphBuilder()
        graph = builder.build(parsed_nodes, document_title="Методика № 421/пр")
    """
    
    def __init__(self):
        self.graph = DocumentGraph()
        self._node_counter = 0
        self._id_map = {}  # Маппинг: исходный узел → ID в графе
    
    def build(
        self, 
        parsed_nodes: List[BaseNode], 
        document_title: str = "Документ",
        document_metadata: Optional[dict] = None
    ) -> DocumentGraph:
        """
        Построить граф из списка распарсенных узлов.
        
        Args:
            parsed_nodes: список узлов верхнего уровня
            document_title: название документа
            document_metadata: дополнительные метаданные
        
        Returns:
            DocumentGraph — построенный граф
        """
        self.graph = DocumentGraph(metadata=document_metadata or {})
        self._node_counter = 0
        self._id_map = {}
        
        # 🔹 Создаём корневой узел документа
        doc_node = DocumentNode(
            id=self._make_id('doc', document_title),
            title=document_title
        )
        self.graph.add_node(doc_node)
        
        # 🔹 Обходим все узлы верхнего уровня
        for node in parsed_nodes:
            self._process_node(node, parent_id=doc_node.id, parent_number=None)
        
        # 🔹 Извлекаем ссылки между пунктами (REFERENCES)
        self._extract_references()
        
        return self.graph
    
    def _make_id(self, prefix: str, identifier: str) -> str:
        """Создать уникальный ID для узла."""
        self._node_counter += 1
        safe_id = re.sub(r'[^a-zA-Z0-9а-яА-Я_.-]', '_', str(identifier))
        return f"{prefix}:{safe_id}#{self._node_counter}"
    
    def _process_node(
        self, 
        node: BaseNode, 
        parent_id: str, 
        parent_number: Optional[str]
    ) -> Optional[str]:
        """
        Рекурсивно обработать узел и его детей.
        
        Returns:
            ID созданного узла графа или None
        """
        # 🔹 Разные типы узлов обрабатываются по-разному
        if isinstance(node, ParsedSectionNode):
            return self._process_section(node, parent_id)
        elif isinstance(node, ParsedPointNode):
            return self._process_point(node, parent_id, parent_number)
        elif isinstance(node, ParsedParagraphNode):
            return self._process_paragraph(node, parent_id)
        elif isinstance(node, ParsedAmendmentNode):
            return self._process_amendment(node, parent_id)
        else:
            # Неизвестный тип — пропускаем, но обрабатываем детей
            for child in getattr(node, 'children', []):
                self._process_node(child, parent_id, parent_number)
            return None
    
    def _process_section(self, node: ParsedSectionNode, parent_id: str) -> str:
        """Обработать раздел."""
        graph_node = SectionNode(
            id=self._make_id('section', node.title),
            title=node.title,
            roman_number=getattr(node, 'number', None),
            level=1
        )
        self.graph.add_node(graph_node)
        self.graph.add_edge(GraphEdge(
            source_id=parent_id,
            target_id=graph_node.id,
            type=EdgeType.CONTAINS
        ))
        
        # Обрабатываем детей раздела
        for child in node.children:
            self._process_node(child, graph_node.id, None)
        
        return graph_node.id
    
    def _process_point(
        self, 
        node: ParsedPointNode, 
        parent_id: str, 
        parent_number: Optional[str]
    ) -> str:
        """Обработать пункт."""
        # Формируем полный номер (например, "14.1" для подпункта)
        full_number = node.number
        if parent_number:
            full_number = f"{parent_number}.{node.number}"
        
        # Определяем уровень
        level = 1
        if '.' in full_number:
            level = full_number.count('.') + 1
        
        graph_node = PointNode(
            id=self._make_id('point', full_number),
            number=node.number,
            level=level,
            text=self._extract_point_text(node),
            metadata={'full_number': full_number}
        )
        self.graph.add_node(graph_node)
        self._id_map[id(node)] = graph_node.id
        
        self.graph.add_edge(GraphEdge(
            source_id=parent_id,
            target_id=graph_node.id,
            type=EdgeType.CONTAINS
        ))
        
        # Обрабатываем детей пункта
        for child in node.children:
            self._process_node(child, graph_node.id, full_number)
        
        return graph_node.id
    
    def _process_paragraph(self, node: ParsedParagraphNode, parent_id: str) -> str:
        """Обработать абзац."""
        if node.number is None:
            print(f"\n[DEBUG] ParagraphNode без номера:")
            print(f"  text: {node.text[:100]!r}")
            print(f"  parent_id: {parent_id}")
            print(f"  type(node): {type(node).__name__}")
            import traceback
            traceback.print_stack()
        graph_node = ParagraphNode(
            id=self._make_id('para', f"{parent_id}_{node.number}"),
            number=node.number,
            text=node.text,
            point_id=parent_id
        )
        self.graph.add_node(graph_node)
        self.graph.add_edge(GraphEdge(
            source_id=parent_id,
            target_id=graph_node.id,
            type=EdgeType.CONTAINS
        ))
        return graph_node.id
    
    def _process_amendment(self, node: ParsedAmendmentNode, parent_id: str) -> str:
        """Обработать amendment."""
        # Определяем целевые пункты из target
        target_point_ids = []
        if hasattr(node, 'target') and node.target:
            for comp in node.target.components:
                if comp.type == ComponentType.POINT:
                    # Пытаемся найти соответствующий пункт в графе
                    point_id = self._find_point_by_number(comp.value)
                    if point_id:
                        target_point_ids.append(point_id)
        
        graph_node = AmendmentNode(
            id=self._make_id('amend', node.number or 'unknown'),
            amendment_number=node.number or 'unknown',
            action=getattr(node, 'action', 'unknown'),
            target_point_ids=target_point_ids,
            source_text=getattr(node, 'text', '')
        )
        self.graph.add_node(graph_node)
        self._id_map[id(node)] = graph_node.id
        
        # Рёбра AMENDS к целевым пунктам
        for target_id in target_point_ids:
            self.graph.add_edge(GraphEdge(
                source_id=graph_node.id,
                target_id=target_id,
                type=EdgeType.AMENDS,
                metadata={'action': graph_node.action}
            ))
        
        # 🔹 Обрабатываем специфичные типы amendments
        self._process_amendment_details(node, graph_node.id)
        
        # Обрабатываем детей (для composite)
        for child in getattr(node, 'children', []):
            self._process_node(child, graph_node.id, None)
        
        return graph_node.id
    
    def _process_amendment_details(self, node: ParsedAmendmentNode, amendment_id: str) -> None:
        """Обработать детали конкретного amendment."""
        # ReplaceWords — одна замена
        if isinstance(node, ReplaceWordsAmendmentNode):
            repl_node = ReplacementNode(
                id=self._make_id('repl', f"{amendment_id}_1"),
                old_text=node.old_text,
                new_text=node.new_text,
                amendment_id=amendment_id
            )
            self.graph.add_node(repl_node)
            self.graph.add_edge(GraphEdge(
                source_id=amendment_id,
                target_id=repl_node.id,
                type=EdgeType.CONTAINS
            ))
        
        # MultipleReplaceWords — несколько замен
        elif isinstance(node, MultipleReplaceWordsAmendmentNode):
            for i, replacement in enumerate(node.replacements):
                repl_node = ReplacementNode(
                    id=self._make_id('repl', f"{amendment_id}_{i+1}"),
                    old_text=replacement.old_text,
                    new_text=replacement.new_text,
                    amendment_id=amendment_id
                )
                self.graph.add_node(repl_node)
                self.graph.add_edge(GraphEdge(
                    source_id=amendment_id,
                    target_id=repl_node.id,
                    type=EdgeType.CONTAINS
                ))
        
        # Add — дополнение
        elif isinstance(node, AddAmendmentNode):
            repl_node = ReplacementNode(
                id=self._make_id('repl', f"{amendment_id}_add"),
                anchor=node.anchor,
                new_text=node.new_text,
                amendment_id=amendment_id
            )
            self.graph.add_node(repl_node)
            self.graph.add_edge(GraphEdge(
                source_id=amendment_id,
                target_id=repl_node.id,
                type=EdgeType.CONTAINS
            ))
        
        # Exclude — исключение
        elif isinstance(node, ExcludeAmendmentNode):
            repl_node = ReplacementNode(
                id=self._make_id('repl', f"{amendment_id}_excl"),
                old_text=node.old_text,
                amendment_id=amendment_id
            )
            self.graph.add_node(repl_node)
            self.graph.add_edge(GraphEdge(
                source_id=amendment_id,
                target_id=repl_node.id,
                type=EdgeType.CONTAINS
            ))
    
    def _extract_point_text(self, node: ParsedPointNode) -> str:
        """Извлечь текстовое содержимое пункта."""
        texts = []
        for child in node.children:
            if isinstance(child, ParsedParagraphNode):
                texts.append(child.text)
        return ' '.join(texts)
    
    def _find_point_by_number(self, number: str) -> Optional[str]:
        """Найти узел пункта по номеру."""
        for node_id, node in self.graph.nodes.items():
            if isinstance(node, PointNode) and node.number == number:
                return node_id
        return None
    
    # graph/builder.py (обновлённый метод _extract_references)

    def _extract_references(self) -> None:
        """
        Извлечь ссылки между пунктами из текста.
        
        Поддерживаемые форматы:
        - "пункт N" / "пункта N" / "пунктом N"
        - "абзац N пункта M"
        - "абзац (первый|второй|...) пункта M"
        - "подпункт а пункта N"
        - "пункт N.M" (составной номер)
        """
        # 🔹 Паттерны для поиска ссылок
        patterns = {
            # Простая ссылка на пункт
            'point_simple': re.compile(
                r'(?:пункт\w*\s+|п\.\s*)(\d+(?:\.\d+)*)',
                re.IGNORECASE
            ),
            
            # Абзац пункта (с числом)
            'paragraph_point': re.compile(
                r'абзац(?:е|ем)?\s+(\d+)\s+пункта\s+(\d+(?:\.\d+)*)',
                re.IGNORECASE
            ),
            
            # Абзац пункта (с числительным)
            'paragraph_word_point': re.compile(
                r'абзац(?:е|ем)?\s+(первый|второй|третий|четвертый|пятый|шестой|'
                r'седьмой|восьмой|девятый|десятый)\s+пункта\s+(\d+(?:\.\d+)*)',
                re.IGNORECASE
            ),
            
            # Подпункт пункта
            'subpoint_point': re.compile(
                r'подпункт(?:е|ом)?\s*[«"]?([а-яё])["»]?\s+пункта\s+(\d+(?:\.\d+)*)',
                re.IGNORECASE
            ),
            
            # Подпункт (без явного указания пункта — ищем в контексте)
            'subpoint_only': re.compile(
                r'подпункт(?:е|ом)?\s*[«"]?([а-яё])["»]',
                re.IGNORECASE
            ),
        }
        
        # Словарь для преобразования числительных в цифры
        ordinal_numbers = {
            'первый': '1', 'второй': '2', 'третий': '3', 'четвертый': '4',
            'пятый': '5', 'шестой': '6', 'седьмой': '7', 'восьмой': '8',
            'девятый': '9', 'десятый': '10'
        }
        
        for node_id, node in self.graph.nodes.items():
            if not isinstance(node, PointNode):
                continue
            
            if not node.text:
                continue
            
            found_refs = set()  # Чтобы избежать дубликатов
            
            # 🔍 1. Ищем "абзац N пункта M"
            for match in patterns['paragraph_point'].finditer(node.text):
                para_num = match.group(1)
                point_num = match.group(2)
                ref_key = f"para:{point_num}:{para_num}"
                if ref_key not in found_refs:
                    self._add_reference(node_id, point_num, EdgeType.REFERENCES, 
                                    {'type': 'paragraph', 'number': para_num})
                    found_refs.add(ref_key)
            
            # 🔍 2. Ищем "абзац (первый|второй|...) пункта M"
            for match in patterns['paragraph_word_point'].finditer(node.text):
                word_num = match.group(1).lower()
                point_num = match.group(2)
                para_num = ordinal_numbers.get(word_num, word_num)
                ref_key = f"para:{point_num}:{para_num}"
                if ref_key not in found_refs:
                    self._add_reference(node_id, point_num, EdgeType.REFERENCES,
                                    {'type': 'paragraph', 'number': para_num, 'word': word_num})
                    found_refs.add(ref_key)
            
            # 🔍 3. Ищем "подпункт а пункта N"
            for match in patterns['subpoint_point'].finditer(node.text):
                subpoint_letter = match.group(1)
                point_num = match.group(2)
                ref_key = f"subpoint:{point_num}:{subpoint_letter}"
                if ref_key not in found_refs:
                    self._add_reference(node_id, point_num, EdgeType.REFERENCES,
                                    {'type': 'subpoint', 'letter': subpoint_letter})
                    found_refs.add(ref_key)
            
            # 🔍 4. Ищем простые ссылки "пункт N" (но не внутри других паттернов)
            for match in patterns['point_simple'].finditer(node.text):
                ref_number = match.group(1)
                
                # Проверяем, не является ли эта ссылка частью более сложного паттерна
                start_pos = match.start()
                is_part_of_complex = False
                
                for complex_match in patterns['paragraph_point'].finditer(node.text):
                    if complex_match.start() <= start_pos <= complex_match.end():
                        is_part_of_complex = True
                        break
                
                if not is_part_of_complex and ref_number != node.number:
                    ref_key = f"point:{ref_number}"
                    if ref_key not in found_refs:
                        self._add_reference(node_id, ref_number, EdgeType.REFERENCES,
                                        {'type': 'point'})
                        found_refs.add(ref_key)

    def _add_reference(self, source_id: str, target_number: str, 
                    edge_type: EdgeType, metadata: dict) -> None:
        """Добавить ссылку между узлами."""
        target_id = self._find_point_by_number(target_number)
        
        if target_id and target_id != source_id:
            # Проверяем, нет ли уже такого ребра
            existing = False
            for edge in self.graph.edges:
                if (edge.source_id == source_id and 
                    edge.target_id == target_id and 
                    edge.type == edge_type):
                    existing = True
                    break
            
            if not existing:
                self.graph.add_edge(GraphEdge(
                    source_id=source_id,
                    target_id=target_id,
                    type=edge_type,
                    metadata=metadata
                ))
    def _process_amendment_with_versioning(self, node: ParsedAmendmentNode, 
                                        amendment_id: str) -> None:
        """
        Обработать amendment с созданием версий пунктов.
        
        Создаёт рёбра SUPERSEDES для заменённых пунктов.
        """
        # 🔹 Для replace amendments создаём новые версии
        if isinstance(node, (ReplaceAmendmentNode, ReplaceWordsAmendmentNode)):
            self._create_supersedes_links(node, amendment_id)
        
        # 🔹 Для multiple replace words
        elif isinstance(node, MultipleReplaceWordsAmendmentNode):
            self._create_supersedes_links(node, amendment_id)
        
        # 🔹 Для add/exclude — помечаем как модификацию
        elif isinstance(node, (AddAmendmentNode, ExcludeAmendmentNode, 
                            AddParagraphAmendmentNode)):
            self._mark_point_as_modified(node, amendment_id)

    def _create_supersedes_links(self, node, amendment_id: str) -> None:
        """
        Создать связи SUPERSEDES для заменённых пунктов.
        
        Логика:
        1. Находим целевые пункты
        2. Создаём новые версии (PointNode с суффиксом _v2)
        3. Создаём ребро SUPERSEDES: new_version → old_version
        4. Обновляем текст пункта
        """
        if not hasattr(node, 'target') or not node.target:
            return
        
        # Находим все целевые пункты
        for comp in node.target.components:
            if comp.type != ComponentType.POINT:
                continue
            
            old_point_id = self._find_point_by_number(comp.value)
            if not old_point_id:
                continue
            
            old_point = self.graph.get_node(old_point_id)
            if not old_point:
                continue
            
            # 🔹 Создаём новую версию пункта
            new_number = f"{comp.value}_v{self._get_next_version(comp.value)}"
            new_point_id = self._make_id('point', new_number)
            
            # Определяем новый текст (если есть new_content)
            new_text = old_point.text
            if hasattr(node, 'new_content') and node.new_content:
                # Извлекаем текст из new_content
                new_text = self._extract_new_content_text(node.new_content)
            
            # Создаём новую версию
            new_point = PointNode(
                id=new_point_id,
                number=comp.value,  # Оригинальный номер
                level=old_point.level,
                text=new_text,
                section_id=old_point.section_id,
                metadata={
                    'full_number': old_point.metadata.get('full_number', comp.value),
                    'version': self._get_next_version(comp.value),
                    'amended_by': amendment_id,
                    'amendment_date': getattr(node, 'amendment_date', None)
                }
            )
            self.graph.add_node(new_point)
            
            # 🔹 Создаём ребро SUPERSEDES: новая версия → старая
            self.graph.add_edge(GraphEdge(
                source_id=new_point_id,
                target_id=old_point_id,
                type=EdgeType.SUPERSEDES,
                metadata={
                    'amendment_id': amendment_id,
                    'action': getattr(node, 'action', 'replace')
                }
            ))
            
            # 🔹 Обновляем связи CONTAINS (родитель → новая версия)
            parent = self.graph.get_parent(old_point_id)
            if parent:
                # Удаляем старую связь
                self.graph.edges = [
                    e for e in self.graph.edges 
                    if not (e.source_id == parent.id and 
                        e.target_id == old_point_id and 
                        e.type == EdgeType.CONTAINS)
                ]
                # Добавляем новую связь
                self.graph.add_edge(GraphEdge(
                    source_id=parent.id,
                    target_id=new_point_id,
                    type=EdgeType.CONTAINS
                ))

    def _mark_point_as_modified(self, node, amendment_id: str) -> None:
        """
        Пометить пункт как модифицированный (для add/exclude).
        
        Не создаёт новую версию, но добавляет метаданные.
        """
        if not hasattr(node, 'target') or not node.target:
            return
        
        for comp in node.target.components:
            if comp.type != ComponentType.POINT:
                continue
            
            point_id = self._find_point_by_number(comp.value)
            if not point_id:
                continue
            
            point = self.graph.get_node(point_id)
            if point and hasattr(point, 'metadata'):
                # Добавляем информацию об amendment
                if 'amendments' not in point.metadata:
                    point.metadata['amendments'] = []
                
                point.metadata['amendments'].append({
                    'amendment_id': amendment_id,
                    'action': getattr(node, 'action', 'unknown'),
                    'date': getattr(node, 'amendment_date', None)
                })

    def _extract_new_content_text(self, new_content) -> str:
        """Извлечь текст из new_content amendment."""
        texts = []
        
        if isinstance(new_content, list):
            for item in new_content:
                if hasattr(item, 'text') and item.text:
                    texts.append(item.text)
                elif hasattr(item, 'children'):
                    for child in item.children:
                        if hasattr(child, 'text') and child.text:
                            texts.append(child.text)
        
        return ' '.join(texts)

    def _get_next_version(self, point_number: str) -> int:
        """Определить следующую версию для пункта."""
        version = 1
        
        for node in self.graph.nodes.values():
            if (isinstance(node, PointNode) and 
                node.number == point_number and 
                'version' in node.metadata):
                version = max(version, node.metadata['version'] + 1)
        
        return version