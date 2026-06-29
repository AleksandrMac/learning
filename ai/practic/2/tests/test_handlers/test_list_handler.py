import pytest
from handlers.base import ParseContext
from handlers.list_handler import ListHandler
from nodes.concrete import ParagraphNode, PointNode


class TestListHandler:
    
    @pytest.fixture
    def handler(self):
        return ListHandler()
    
    def test_can_handle_list_with_colon(self, handler):
        context = ParseContext(
            block='Буквенное обозначение отражает вид сметного расчета:\n'
                  'а) СР - сметный расчет;\n'
                  'б) ЛСР - локальный сметный расчет.'
        )
        assert handler.can_handle(context) is True
    
    def test_cannot_handle_text_without_colon(self, handler):
        context = ParseContext(
            block='Текст без двоеточия\n'
                  'а) пункт 1\n'
                  'б) пункт 2'
        )
        assert handler.can_handle(context) is False
    
    def test_handle_list_with_numbered_intro(self, handler):
        """Пункт со списком: родитель — PointNode с вводным абзацем."""
        context = ParseContext(
            block='8. При определении сметной стоимости применяются:\n'
                '    а) сметные нормы;\n'
                '    б) федеральные единичные расценки;\n'
                '    в) территориальные единичные расценки.'
        )
        
        node = handler.handle(context)
        
        # Родитель — PointNode
        assert isinstance(node, PointNode)
        assert node.number == '8'
        
        # 🔑 Проверяем, что есть вводный абзац
        assert len(node.children) == 4  # 1 intro + 3 subpoints
        
        # Первый ребёнок — вводный абзац
        assert isinstance(node.children[0], ParagraphNode)
        assert node.children[0].number == '1'
        assert 'применяются' in node.children[0].text
        
        # Остальные — подпункты
        assert isinstance(node.children[1], PointNode)
        assert node.children[1].number == 'а'
        assert isinstance(node.children[1].children[0], ParagraphNode)
        assert 'сметные нормы' in node.children[1].children[0].text
        
        assert node.children[2].number == 'б'
        assert node.children[3].number == 'в'
    
    def test_handle_list_without_numbered_intro(self, handler):
        """Список без номера в вводной строке: родитель — ParagraphNode."""
        context = ParseContext(
            block='Буквенное обозначение отражает вид сметного расчета:\n'
                  '    а) СР - сметный расчет;\n'
                  '    б) ЛСР - локальный сметный расчет.'
        )
        
        node = handler.handle(context)
        
        # 🔑 Родитель — ParagraphNode (нет номера)
        assert isinstance(node, ParagraphNode)
        
        # Подпункты
        assert isinstance(node.children[0], PointNode)
        assert node.children[0].number == 'а'