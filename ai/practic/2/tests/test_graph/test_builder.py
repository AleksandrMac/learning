import pytest
from graph.builder import GraphBuilder
from graph.models import NodeType, EdgeType, PointNode, AmendmentNode
from nodes.concrete import PointNode as ParsedPointNode, ParagraphNode as ParsedParagraphNode
from nodes.amendments import ReplaceWordsAmendmentNode, ExcludeAmendmentNode
from nodes.target import TargetAddress, TargetComponent, ComponentType


class TestGraphBuilder:
    
    @pytest.fixture
    def builder(self):
        return GraphBuilder()
    
    def test_build_simple_point(self, builder):
        """Построение графа с одним пунктом."""
        point = ParsedPointNode(number='14')
        para = ParsedParagraphNode(number='1', text='Текст пункта 14.')
        point.add_child(para)
        
        graph = builder.build([point], document_title="Тестовый документ")
        
        # Проверяем узлы
        assert len(graph.nodes) == 3  # doc + point + paragraph
        assert any(n.type == NodeType.DOCUMENT for n in graph.nodes.values())
        assert any(n.type == NodeType.POINT for n in graph.nodes.values())
        assert any(n.type == NodeType.PARAGRAPH for n in graph.nodes.values())
        
        # Проверяем рёбра
        assert len(graph.edges) == 2  # doc→point, point→para
        assert all(e.type == EdgeType.CONTAINS for e in graph.edges)
    
    def test_build_with_amendment(self, builder):
        """Построение графа с amendment."""
        # Исходный пункт
        point = ParsedPointNode(number='14')
        para = ParsedParagraphNode(number='1', text='Текст пункта.')
        point.add_child(para)
        
        # Amendment
        target = TargetAddress(components=[
            TargetComponent(ComponentType.POINT, '14', level=1)
        ])
        amendment = ReplaceWordsAmendmentNode(
            number='1',
            text='Заменить слова',
            target=target,
            old_text='старое',
            new_text='новое'
        )
        
        graph = builder.build([point, amendment], document_title="Тест")
        
        # Проверяем, что есть ребро AMENDS
        amend_edges = [e for e in graph.edges if e.type == EdgeType.AMENDS]
        assert len(amend_edges) == 1
        
        # Проверяем ReplacementNode
        repl_nodes = [n for n in graph.nodes.values() if n.type == NodeType.REPLACEMENT]
        assert len(repl_nodes) == 1
        assert repl_nodes[0].old_text == 'старое'
        assert repl_nodes[0].new_text == 'новое'
    
    def test_extract_references(self, builder):
        """Извлечение ссылок между пунктами."""
        point_14 = ParsedPointNode(number='14')
        para_14 = ParsedParagraphNode(
            number='1', 
            text='В соответствии с пунктом 13 Методики...'
        )
        point_14.add_child(para_14)
        
        point_13 = ParsedPointNode(number='13')
        para_13 = ParsedParagraphNode(number='1', text='Текст пункта 13.')
        point_13.add_child(para_13)
        
        graph = builder.build([point_13, point_14], document_title="Тест")
        
        # Проверяем ребро REFERENCES
        ref_edges = [e for e in graph.edges if e.type == EdgeType.REFERENCES]
        assert len(ref_edges) == 1
        
        # Пункт 14 ссылается на пункт 13
        source = graph.get_node(ref_edges[0].source_id)
        target = graph.get_node(ref_edges[0].target_id)
        assert source.number == '14'
        assert target.number == '13'
