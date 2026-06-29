import pytest
from nodes.base import BaseNode
from nodes.concrete import (
    ParagraphNode, PointNode
)


class TestBaseNode:
    """Тесты базового класса узла."""
    
    def test_add_child(self):
        """Добавление дочернего узла."""
        parent = ParagraphNode(number='8', text='При определении применяются:')
        child = PointNode(number='а')
        
        parent.add_child(child)
        
        assert len(parent.children) == 1
        assert parent.children[0] == child
        assert child.parent_id == parent.id
    
    def test_node_metadata(self):
        """Метаданные узла."""
        node = ParagraphNode(
            number='153',
            text='Текст пункта',
            valid_from='2022-09-11',
            meta={'source': 'pr_557-421'}
        )
        
        assert node.valid_from == '2022-09-11'
        assert node.meta['source'] == 'pr_557-421'