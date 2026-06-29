import pytest
from graph.builder import GraphBuilder
from graph.queries import GraphQueries
from nodes.concrete import PointNode as ParsedPointNode, ParagraphNode as ParsedParagraphNode


class TestGraphQueries:
    
    @pytest.fixture
    def graph_with_data(self):
        builder = GraphBuilder()
        
        point_13 = ParsedPointNode(number='13')
        point_13.add_child(ParsedParagraphNode(number='1', text='Пункт 13.'))
        
        point_14 = ParsedPointNode(number='14')
        point_14.add_child(ParsedParagraphNode(
            number='1', 
            text='В соответствии с пунктом 13...'
        ))
        
        return builder.build([point_13, point_14], document_title="Тест")
    
    def test_get_point(self, graph_with_data):
        queries = GraphQueries(graph_with_data)
        
        point = queries.get_point('14')
        assert point is not None
        assert point.number == '14'
    
    def test_get_point_with_amendments(self, graph_with_data):
        queries = GraphQueries(graph_with_data)
        
        result = queries.get_point_with_amendments('14')
        assert 'point' in result
        assert 'references_to' in result
        
        # Пункт 14 ссылается на 13
        ref_numbers = [p.number for p in result['references_to']]
        assert '13' in ref_numbers
    
    def test_get_document_structure(self, graph_with_data):
        queries = GraphQueries(graph_with_data)
        
        structure = queries.get_document_structure()
        assert structure['type'] == 'document'
        assert 'children' in structure
        assert len(structure['children']) == 2  # 2 пункта