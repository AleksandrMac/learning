import pytest
from nodes.concrete import (
    ParagraphNode, PointNode, FormulaNode, 
    DefinitionNode, SectionNode
)

class TestConcreteNodes:
    """Тесты конкретных типов узлов."""
    
    def test_paragraph_node(self):
        """Узел абзаца."""
        node = ParagraphNode(
            number='83',
            text='Сметная цена определяется на основании данных ФГИС ЦС.'
        )
        
        assert node.number == '83'
        assert 'ФГИС ЦС' in node.text
    
    def test_point_node(self):
        """Узел подпункта."""
        node = PointNode(
            number='а'
        )
        
        assert node.number == 'а'
    
    def test_formula_node(self):
        """Узел формулы."""
        node = FormulaNode(
            number='3.1',
            expression='С_маш.р = Ц_а / Т_с'
        )
        
        assert node.number == '3.1'
        assert 'Ц_а' in node.expression
    
    def test_definition_node(self):
        """Узел определения переменной."""
        node = DefinitionNode(
            term='Ц_а',
            description='цена услуг на предоставление несерийных строительных машин'
        )
        
        assert node.term == 'Ц_а'
        assert 'цена услуг' in node.description
    
    def test_section_node(self):
        """Узел раздела."""
        node = SectionNode(
            number='I',
            title='Общие положения'
        )
        
        assert node.number == 'I'
        assert node.title == 'Общие положения'