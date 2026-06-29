import pytest
from parsers.main_document_parser import MainDocumentParser
from nodes.concrete import ParagraphNode, PointNode, SectionNode, FormulaNode


class TestMainDocumentParser:
    
    @pytest.fixture
    def parser(self):
        return MainDocumentParser()
    
    def test_parse_simple_point(self, parser):
        text = '1. Методика определяет единые методы.'
        
        nodes = parser.parse(text)
        
        assert len(nodes) == 1
        assert isinstance(nodes[0], PointNode)
        assert nodes[0].number == '1'
    
    def test_parse_multi_paragraph_point(self, parser):
        text = ('6. Стоимость строительных работ включает сметные прямые затраты.\n'
                'Сметные прямые затраты учитывают сметную стоимость материалов.\n'
                'Накладные расходы определяются в соответствии со сметными нормативами.')
        
        nodes = parser.parse(text)
        
        assert len(nodes) == 1
        point = nodes[0]
        assert isinstance(point, PointNode)
        assert point.number == '6'
        assert len(point.children) == 3
    
    def test_parse_point_with_list(self, parser):
        """Пункт со списком: все элементы на одном уровне."""
        text = ('8. При определении сметной стоимости применяются:\n'
                '    а) сметные нормы;\n'
                '    б) федеральные единичные расценки;\n'
                '    в) территориальные единичные расценки.')
        
        nodes = parser.parse(text)
        
        assert len(nodes) == 1
        point = nodes[0]
        
        assert isinstance(point, PointNode)
        assert point.number == '8'
        
        # 🔑 Все элементы на одном уровне
        assert len(point.children) == 4  # 1 intro + 3 subpoints
        
        # Первый ребёнок — вводная строка (ParagraphNode)
        assert isinstance(point.children[0], ParagraphNode)
        assert 'применяются' in point.children[0].text
        
        # Остальные — подпункты (PointNode)
        subpoints = point.children[1:]
        assert len(subpoints) == 3
        assert all(isinstance(sp, PointNode) for sp in subpoints)
        assert [sp.number for sp in subpoints] == ['а', 'б', 'в']
    
    def test_parse_point_with_list_in_middle(self, parser):
        """Пункт 29: абзац до списка, список, абзац после списка."""
        text = ('29. Каждому сметному расчету присваивается шифр, содержащий '
                'буквенное обозначение и номер.\n'
                'Буквенное обозначение отражает вид сметного расчета (сметы):\n'
                '    а) СР - сметный расчет на отдельные виды затрат;\n'
                '    б) ЛСР (ЛС) - локальный сметный расчет (смета);\n'
                '    в) ОСР (ОС) - объектный сметный расчет (смета);\n'
                '    г) ССРСС - сводный сметный расчет стоимости строительства.\n'
                'Сквозная нумерация сметных расчетов на отдельные виды затрат '
                'производится целыми числами в порядке их включения в сметную '
                'документацию. Например, СР-1.')
        
        nodes = parser.parse(text)
        
        assert len(nodes) == 1
        point = nodes[0]
        
        assert isinstance(point, PointNode)
        assert point.number == '29'
        
        # 🔑 Все элементы на одном уровне
        assert len(point.children) == 7
        
        # Проверяем типы
        assert isinstance(point.children[0], ParagraphNode)  # Первый абзац
        assert isinstance(point.children[1], ParagraphNode)  # Вводная строка
        assert isinstance(point.children[2], PointNode)      # а)
        assert isinstance(point.children[3], PointNode)      # б)
        assert isinstance(point.children[4], PointNode)      # в)
        assert isinstance(point.children[5], PointNode)      # г)
        assert isinstance(point.children[6], ParagraphNode)  # Последний абзац
        
        # Проверяем содержимое
        assert 'Каждому сметному расчету' in point.children[0].text
        assert 'Буквенное обозначение' in point.children[1].text
        assert 'СР' in point.children[2].children[0].text
        assert 'Сквозная нумерация' in point.children[6].text
    
    def test_parse_section(self, parser):
        text = '## I.Общие положения\n1. Первый пункт раздела.\n2. Второй пункт.'
        
        nodes = parser.parse(text)
        
        assert len(nodes) == 1
        section = nodes[0]
        assert isinstance(section, SectionNode)
        assert section.number == 'I'
        
        points = [n for n in section.children if isinstance(n, PointNode)]
        assert len(points) == 2
        assert points[0].parent_id == section.id
    
    def test_parse_full_section(self, parser, main_document_sample):
        lines = main_document_sample.split('\n')
        section_start = next(i for i, line in enumerate(lines) 
                            if '## I.Общие положения' in line)
        section_end = next((i for i, line in enumerate(lines[section_start+1:], 
                            section_start+1) 
                          if line.startswith('## ')), len(lines))
        
        section_text = '\n'.join(lines[section_start:section_end])
        
        nodes = parser.parse(section_text)
        
        assert len(nodes) == 1
        section = nodes[0]
        assert isinstance(section, SectionNode)
        
        points = [n for n in section.children if isinstance(n, PointNode)]
        assert len(points) >= 3
        
        # 🔑 Пункт 8 должен содержать список на одном уровне
        point_8 = next(p for p in points if p.number == '8')
        subpoints = [c for c in point_8.children if isinstance(c, PointNode)]
        assert len(subpoints) >= 3  # а, б, в, г
