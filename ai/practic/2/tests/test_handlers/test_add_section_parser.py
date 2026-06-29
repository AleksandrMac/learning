# tests/test_handlers/test_add_section_parser.py
import pytest
from handlers.amendment_handler import AmendmentHandler
from handlers.base import ParseContext
from nodes.amendments import AddSectionAmendmentNode
from nodes.concrete import SectionNode, PointNode, ParagraphNode


class TestAddSectionParser:
    """
    Тест парсинга пункта 71:
    "Дополнить Методику разделом XII следующего содержания: «...»"
    
    🔑 Проверяем поле new_content напрямую, а не children секции.
    """
    
    @pytest.fixture
    def handler(self):
        return AmendmentHandler()
    
    @pytest.fixture
    def amendment_text(self):
        """Текст пункта 71 с опечаткой (лишняя » внутри пункта 193)."""
        return (
            '71. Дополнить Методику разделом XII следующего содержания:\n'
            '«\n'
            '## XII. Особенности определения сметной стоимости работ по сохранению '
            'объектов культурного наследия\n'
            '193. Определение сметной стоимости работ по сохранению объектов '
            'культурного наследия на этапе архитектурно-строительного проектирования '
            'базисно-индексным методом осуществляется с применением Сборника цен '
            'на научно-проектные работы по памятникам истории и культуры '
            '(далее — Сборник СЦНПР-91) и сборников сметных норм и единичных '
            'расценок на реставрационно-восстановительные работы по памятникам '
            'истории и культуры г. Москвы (ССН- 84)» (далее — Сборники ССН-84), '
            'сведения о которых включены в ФРСН.\n'
            '194. Пересчет в текущий уровень цен стоимости научно-проектных работ '
            'по памятникам истории и культуры, определенных с использованием '
            'Сборника СЦНПР-91, выполняется с применением индексов изменения '
            'сметной стоимости изыскательских работ к уровню цен по состоянию '
            'на 1 января 1991 г., включаемых в ФРСН и размещаемых в ФГИС ЦС '
            'в соответствии с пунктом 2 Постановления № 1452.\n'
            '»'
        )
    
    @pytest.fixture
    def parsed_node(self, handler, amendment_text):
        context = ParseContext(block=amendment_text)
        return handler.handle(context)
    
    # ═══════════════════════════════════════════════════════
    # 🔍 Базовые проверки
    # ═══════════════════════════════════════════════════════
    
    def test_is_add_section_amendment(self, parsed_node):
        """Узел — AddSectionAmendmentNode."""
        assert isinstance(parsed_node, AddSectionAmendmentNode)
        assert parsed_node.number == '71'
        assert parsed_node.action == 'add_section'
    
    def test_section_title(self, parsed_node):
        """Заголовок раздела извлечён."""
        assert 'XII' in parsed_node.section_title
        assert 'Особенности определения' in parsed_node.section_title
    
    # ═══════════════════════════════════════════════════════
    #  КЛЮЧЕВЫЕ ПРОВЕРКИ: new_content содержит пункты
    # ═══════════════════════════════════════════════════════
    
    def test_new_content_not_empty(self, parsed_node):
        """new_content не пуст."""
        assert len(parsed_node.new_content) > 0, \
            "new_content должен содержать хотя бы один элемент"
    
    def test_new_content_contains_section(self, parsed_node):
        """
        new_content содержит SectionNode.
        """
        sections = [
            item for item in parsed_node.new_content
            if isinstance(item, SectionNode)
        ]
        assert len(sections) >= 1, \
            "new_content должен содержать SectionNode"
    
    def test_new_content_contains_points_193_and_194(self, parsed_node):
        """
        🔑 КЛЮЧЕВОЙ ТЕСТ: new_content содержит пункты 193 и 194.
        
        Проверяем как прямые элементы new_content, так и детей SectionNode.
        """
        # Собираем все PointNode из new_content (прямые + вложенные в section)
        all_points = []
        
        for item in parsed_node.new_content:
            if isinstance(item, PointNode):
                all_points.append(item)
            elif isinstance(item, SectionNode):
                # Проверяем детей секции
                for child in item.children:
                    if isinstance(child, PointNode):
                        all_points.append(child)
        
        # 🔑 Должны быть пункты 193 и 194
        point_numbers = [p.number for p in all_points]
        
        assert '193' in point_numbers, \
            f"Пункт 193 не найден в new_content. Найдены: {point_numbers}"
        assert '194' in point_numbers, \
            f"Пункт 194 не найден в new_content. Найдены: {point_numbers}"
    