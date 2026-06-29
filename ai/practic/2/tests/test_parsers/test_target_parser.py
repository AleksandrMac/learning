import pytest
from parsers.target_parser import TargetParser
from nodes.target import TargetAddress, ComponentType


class TestTargetParser:
    
    @pytest.fixture
    def parser(self):
        return TargetParser()
    
    @pytest.mark.parametrize("text,expected_components", [
        # Простые пункты
        ("в пункте 3", [
            (ComponentType.POINT, '3', 1),
        ]),
        
        # 🔑 Составные номера — теперь несколько POINT
        ("в пункте 4.1", [
            (ComponentType.POINT, '4', 1),
            (ComponentType.POINT, '1', 2),
        ]),
        ("в пункте 4.1.2", [
            (ComponentType.POINT, '4', 1),
            (ComponentType.POINT, '1', 2),
            (ComponentType.POINT, '2', 3),
        ]),
        
        # Диапазоны
        ("в пунктах 153 — 155", [
            (ComponentType.POINT, '153', 1),
            (ComponentType.POINT, '154', 1),
            (ComponentType.POINT, '155', 1),
        ]),
        
        # 🔑 Подпункты — теперь POINT с level=2
        ("в подпункте а пункта 4", [
            (ComponentType.POINT, '4', 1),
            (ComponentType.POINT, 'а', 2),
        ]),
        ("в подпункте 4.а", [
            (ComponentType.POINT, '4', 1),
            (ComponentType.POINT, 'а', 2),
        ]),
        ("в подпункте 4.1.а", [
            (ComponentType.POINT, '4', 1),
            (ComponentType.POINT, '1', 2),
            (ComponentType.POINT, 'а', 3),
        ]),
        
        # Абзацы
        ("в абзаце первом пункта 3", [
            (ComponentType.POINT, '3', 1),
            (ComponentType.PARAGRAPH, '1', None),
        ]),
        
        # Полная формулировка
        ("в абзаце первом подпункта а пункта 4", [
            (ComponentType.POINT, '4', 1),
            (ComponentType.POINT, 'а', 2),
            (ComponentType.PARAGRAPH, '1', None),
        ]),
    ])
    def test_parse_addresses(self, parser, text, expected_components):
        result = parser.parse(text)
        
        assert len(result.components) == len(expected_components), \
            f"Для '{text}': ожидалось {len(expected_components)}, получено {len(result.components)}"
        
        for component, (expected_type, expected_value, expected_level) in zip(
            result.components, expected_components
        ):
            assert component.type == expected_type
            assert component.value == expected_value
            if expected_level is not None:
                assert component.level == expected_level
    
    def test_get_point_property(self, parser):
        result = parser.parse("в пункте 80")
        assert result.get_component_at_level(1).value == '80'
    
    def test_get_subpoint_property(self, parser):
        result = parser.parse("в подпункте а пункта 4")
        assert result.get_component_at_level(2).value == 'а'
    
    def test_paragraph_number_property(self, parser):
        result = parser.parse("в абзаце четвертом пункта 80")
        assert result.paragraph_number == '4'
    
    def test_get_component_at_level(self, parser):
        result = parser.parse("в пункте 4.1.2")
        
        assert result.get_component_at_level(1).value == '4'
        assert result.get_component_at_level(2).value == '1'
        assert result.get_component_at_level(3).value == '2'
        assert result.get_component_at_level(4) is None
    
    def test_to_path(self, parser):
        result = parser.parse("в абзаце первом подпункта а пункта 4")
        assert result.to_path() == '4.а.para:1'
    
    def test_compound_point_path(self, parser):
        """Путь для составного номера."""
        result = parser.parse("в пункте 4.1")
        assert result.to_path() == '4.1'


    def test_parse_ignores_points_inside_quotes(self, parser):
        """Парсер игнорирует упоминания пунктов внутри кавычек."""
        # 🔑 Упрощаем: только один пункт вне кавычек
        text = "в пункте 10 «цитата с пунктом 13»"
        result = parser.parse(text)
        
        # 🔑 Должен найти только пункт 10, но не 13 (внутри кавычек)
        assert len(result.components) == 1
        assert result.components[0].value == '10'
        assert result.components[0].level == 1


    def test_parse_ignores_nested_quotes(self, parser):
        """Парсер игнорирует вложенные кавычки."""
        text = "в пункте 10 «цитата с «вложенной» кавычкой и пунктом 13»"
        result = parser.parse(text)
        
        assert len(result.components) == 1
        assert result.components[0].value == '10'


    def test_parse_complex_amendment_text(self, parser):
        """Реальный текст из composite-амendment с упоминанием пункта в цитате."""
        text = (
            "подпункт «б» изложить в следующей редакции:\n"
            "«\n"
            "б) базисно-индексным методом...\n"
            "в соответствии с пунктом 13 Методики;\n"
            "»"
        )
        
        result = parser.parse(text)
        
        # 🔑 Должен найти только подпункт «б», но не пункт 13
        assert len(result.components) == 1
        assert result.components[0].value == 'б'
        assert result.components[0].level == 1

class TestTargetParserPointsList:
    
    @pytest.fixture
    def parser(self):
        return TargetParser()
    
    def test_parse_two_points_with_and(self, parser):
        """'Пункты 15 и 16' → [POINT('15'), POINT('16')]."""
        result = parser.parse("Пункты 15 и 16 изложить в следующей редакции")
        
        assert len(result.components) == 2
        assert result.components[0].type == ComponentType.POINT
        assert result.components[0].value == '15'
        assert result.components[0].level == 1
        assert result.components[1].type == ComponentType.POINT
        assert result.components[1].value == '16'
        assert result.components[1].level == 1
        
        # 🔑 is_range = True
        assert result.is_range is True
    
    def test_parse_three_points_with_commas_and(self, parser):
        """'Пункты 15, 16 и 17' → [POINT('15'), POINT('16'), POINT('17')]."""
        result = parser.parse("Пункты 15, 16 и 17 изложить")
        
        assert len(result.components) == 3
        values = [c.value for c in result.components]
        assert values == ['15', '16', '17']
        assert result.is_range is True
    
    def test_parse_range_with_dash(self, parser):
        """'Пункты 15 — 16' → [POINT('15'), POINT('16')] (диапазон)."""
        result = parser.parse("в пунктах 15 — 16")
        
        assert len(result.components) == 2
        values = [c.value for c in result.components]
        assert values == ['15', '16']
        assert result.is_range is True
    
    def test_full_point_path_for_range(self, parser):
        """full_point_path для диапазона."""
        result = parser.parse("Пункты 15 и 16")
        assert result.full_point_path == '15.16'

    def test_target_parser_does_not_capture_next_word(self, parser):
        """TargetParser не захватывает 'следующего' как номер абзаца."""
        text = 'дополнить абзацем следующего содержания'
        result = parser.parse(text)
        
        # 🔑 Не должно быть PARAGRAPH('следующего')
        assert result.paragraph_number is None
        assert len(result.components) == 0


    def test_target_parser_captures_real_paragraph_number(self, parser):
        """TargetParser захватывает реальный номер абзаца."""
        text = 'в абзаце третьем пункта 10'
        result = parser.parse(text)
        
        assert result.paragraph_number == '3'
        assert result.get_component_at_level(1).value == '10'


    def test_target_parser_captures_word_numbers(self, parser):
        """TargetParser захватывает числительные как номера абзацев."""
        text = 'в абзаце пятом пункта 20'
        result = parser.parse(text)
        
        assert result.paragraph_number == '5'
        assert result.get_component_at_level(1).value == '20'