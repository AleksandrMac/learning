import pytest
from parsers.amendment_parsers import MultipleReplaceWordsParser
from nodes.target import TargetAddress, TargetComponent, ComponentType
from nodes.amendments import MultipleReplaceWordsAmendmentNode, Replacement


class TestMultipleReplaceWordsParser:
    
    @pytest.fixture
    def parser(self):
        return MultipleReplaceWordsParser()
    
    def test_can_parse_two_replacements(self, parser):
        """Распознаёт две последовательные замены."""
        text = (
            'слова «(графы 4, 5, 6)» заменить словами «(графы 4, 5, 6 и 7)», '
            'слова «(графы 7, 8)» заменить словами «(графы 7 и 8)»'
        )
        assert parser.can_parse(text) is True
    
    def test_can_parse_single_replacement_returns_false(self, parser):
        """Одиночная замена НЕ распознаётся этим парсером."""
        text = 'слова «старое» заменить словами «новое»'
        assert parser.can_parse(text) is False
    
    def test_parse_two_replacements(self, parser):
        """Парсит две замены в один узел."""
        text = (
            'слова «(графы 4, 5, 6)» заменить словами «(графы 4, 5, 6 и 7)», '
            'слова «(графы 7, 8)» заменить словами «(графы 7 и 8)»'
        )
        
        target = TargetAddress(components=[
            TargetComponent(ComponentType.POINT, '50', level=1),
            TargetComponent(ComponentType.PARAGRAPH, '2'),
        ])
        
        node = parser.parse(text, target)
        
        assert isinstance(node, MultipleReplaceWordsAmendmentNode)
        assert node.action == 'multiple_replace_words'
        assert len(node.replacements) == 2
        
        # Первая замена
        assert node.replacements[0].old_text == '(графы 4, 5, 6)'
        assert node.replacements[0].new_text == '(графы 4, 5, 6 и 7)'
        
        # Вторая замена
        assert node.replacements[1].old_text == '(графы 7, 8)'
        assert node.replacements[1].new_text == '(графы 7 и 8)'
        
        # Target сохранён
        assert node.target.get_component_at_level(1).value == '50'
        assert node.target.paragraph_number == '2'
    
    def test_parse_three_replacements(self, parser):
        """Парсит три замены."""
        text = (
            'слова «A» заменить словами «B», '
            'слова «C» заменить словами «D», '
            'слова «E» заменить словами «F»'
        )
        
        target = TargetAddress(components=[
            TargetComponent(ComponentType.POINT, '10', level=1)
        ])
        
        node = parser.parse(text, target)
        
        assert len(node.replacements) == 3
        assert node.replacements[2].old_text == 'E'
        assert node.replacements[2].new_text == 'F'
    
    def test_parse_with_target_subpoint(self, parser):
        """Парсер извлекает целевой подпункт из текста."""
        text = (
            'в подпункте «а» слова «X» заменить словами «Y», '
            'слова «A» заменить словами «B»'
        )
        
        target = TargetAddress(components=[
            TargetComponent(ComponentType.POINT, '10', level=1)
        ])
        
        node = parser.parse(text, target)
        
        # Target расширен подпунктом
        assert node.target.get_component_at_level(1).value == '10'
        assert node.target.get_component_at_level(2).value == 'а'
    
    def test_parse_with_special_characters(self, parser):
        """Работает со спецсимволами внутри кавычек (скобки, запятые)."""
        text = (
            'слова «(графы 4, 5, 6)» заменить словами «(графы 4, 5, 6 и 7)», '
            'слова «(графы 7, 8)» заменить словами «(графы 7 и 8)»'
        )
        
        target = TargetAddress(components=[
            TargetComponent(ComponentType.POINT, '50', level=1)
        ])
        
        node = parser.parse(text, target)
        
        # Скобки и запятые сохранены
        assert node.replacements[0].old_text == '(графы 4, 5, 6)'
        assert node.replacements[0].new_text == '(графы 4, 5, 6 и 7)'