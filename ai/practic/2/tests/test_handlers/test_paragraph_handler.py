import pytest
from handlers.base import ParseContext
from handlers.paragraph_handler import ParagraphHandler
from nodes.concrete import ParagraphNode, PointNode, FormulaNode, DefinitionNode


class TestParagraphHandler:
    
    @pytest.fixture
    def handler(self):
        return ParagraphHandler()
    
    def test_can_handle_numbered_paragraph(self, handler):
        context = ParseContext(block='83. Сметная цена на эксплуатацию машин')
        assert handler.can_handle(context) is True
    
    def test_cannot_handle_unnumbered_text(self, handler):
        context = ParseContext(block='Это просто текст без номера')
        assert handler.can_handle(context) is False
    
    def test_handle_simple_point(self, handler):
        """Одноабзацный пункт."""
        context = ParseContext(block='1. Методика определяет единые методы.')
        
        node = handler.handle(context)
        
        assert isinstance(node, PointNode)
        assert node.number == '1'
        assert len(node.children) == 1
        assert isinstance(node.children[0], ParagraphNode)
        assert 'Методика определяет' in node.children[0].text
    
    def test_handle_multi_paragraph_point(self, handler):
        """Многоабзацный пункт без списков."""
        context = ParseContext(
            block='6. Первый абзац.\n'
                  'Второй абзац.\n'
                  'Третий абзац.'
        )
        
        node = handler.handle(context)
        
        assert isinstance(node, PointNode)
        assert node.number == '6'
        assert len(node.children) == 3
        
        assert all(isinstance(c, ParagraphNode) for c in node.children)
        assert [c.number for c in node.children] == ['1', '2', '3']
    
    # 🔑 ОБНОВЛЁННЫЕ ТЕСТЫ — новая структура со списками
    
    def test_handle_point_with_list_at_start(self, handler):
        """Пункт 8: список идёт сразу после вводной строки."""
        context = ParseContext(
            block='8. При определении сметной стоимости применяются:\n'
                  '    а) сметные нормы;\n'
                  '    б) федеральные единичные расценки;\n'
                  '    в) территориальные единичные расценки.'
        )
        
        node = handler.handle(context)
        
        assert isinstance(node, PointNode)
        assert node.number == '8'
        
        # 🔑 Все элементы на одном уровне
        assert len(node.children) == 4  # 1 intro + 3 subpoints
        
        # Первый ребёнок — вводная строка (ParagraphNode)
        intro = node.children[0]
        assert isinstance(intro, ParagraphNode)
        assert intro.number == '1'
        assert 'применяются' in intro.text
        
        # Остальные — подпункты (PointNode)
        subpoints = node.children[1:]
        assert len(subpoints) == 3
        assert all(isinstance(sp, PointNode) for sp in subpoints)
        assert [sp.number for sp in subpoints] == ['а', 'б', 'в']
        
        # Текст подпунктов — в их дочерних ParagraphNode
        assert 'сметные нормы' in subpoints[0].children[0].text
        assert 'федеральные единичные расценки' in subpoints[1].children[0].text
        assert 'территориальные единичные расценки' in subpoints[2].children[0].text
    
    def test_handle_point_with_list_in_middle(self, handler):
        """Пункт 29: абзац до списка, абзац со списком, абзац после списка."""
        context = ParseContext(
            block='29. Каждому сметному расчету присваивается шифр, содержащий '
                  'буквенное обозначение и номер.\n'
                  'Буквенное обозначение отражает вид сметного расчета (сметы):\n'
                  '    а) СР - сметный расчет на отдельные виды затрат;\n'
                  '    б) ЛСР (ЛС) - локальный сметный расчет (смета);\n'
                  '    в) ОСР (ОС) - объектный сметный расчет (смета);\n'
                  '    г) ССРСС - сводный сметный расчет стоимости строительства.\n'
                  'Сквозная нумерация сметных расчетов на отдельные виды затрат '
                  'производится целыми числами в порядке их включения в сметную '
                  'документацию. Например, СР-1.'
        )
        
        node = handler.handle(context)
        
        assert isinstance(node, PointNode)
        assert node.number == '29'
        
        # 🔑 Все элементы на одном уровне
        assert len(node.children) == 7  # 1 + 1 + 4 + 1
        
        # Первый абзац — обычный текст
        assert isinstance(node.children[0], ParagraphNode)
        assert node.children[0].number == '1'
        assert 'Каждому сметному расчету' in node.children[0].text
        
        # Второй абзац — вводная строка списка
        assert isinstance(node.children[1], ParagraphNode)
        assert node.children[1].number == '2'
        assert 'Буквенное обозначение' in node.children[1].text
        
        # Подпункты — прямые дети PointNode
        subpoints = node.children[2:6]
        assert len(subpoints) == 4
        assert all(isinstance(sp, PointNode) for sp in subpoints)
        assert [sp.number for sp in subpoints] == ['а', 'б', 'в', 'г']
        
        assert 'СР' in subpoints[0].children[0].text
        assert 'ЛСР' in subpoints[1].children[0].text
        assert 'ОСР' in subpoints[2].children[0].text
        assert 'ССРСС' in subpoints[3].children[0].text
        
        # Последний абзац — обычный текст (не потерялся!)
        assert isinstance(node.children[6], ParagraphNode)
        assert node.children[6].number == '3'
        assert 'Сквозная нумерация' in node.children[6].text
        assert 'СР-1' in node.children[6].text
    
    def test_handle_point_with_multiple_lists(self, handler):
        """Пункт с несколькими списками в разных абзацах."""
        context = ParseContext(
            block='15. Первая часть:\n'
                  '    а) пункт а;\n'
                  '    б) пункт б.\n'
                  'Вторая часть:\n'
                  '    а) пункт а;\n'
                  '    б) пункт б.'
        )
        
        node = handler.handle(context)
        
        assert isinstance(node, PointNode)
        assert node.number == '15'
        
        # 🔑 Все элементы на одном уровне
        # 1 intro + 2 items + 1 intro + 2 items = 6
        assert len(node.children) == 6
        
        # Проверяем структуру
        assert isinstance(node.children[0], ParagraphNode)  # Первая часть
        assert isinstance(node.children[1], PointNode)      # а)
        assert isinstance(node.children[2], PointNode)      # б)
        assert isinstance(node.children[3], ParagraphNode)  # Вторая часть
        assert isinstance(node.children[4], PointNode)      # а)
        assert isinstance(node.children[5], PointNode)      # б)
    
    # tests/test_handlers/test_paragraph_handler.py
    def test_handle_point_with_formula(self, handler):
        """Пункт 79 с формулой и определениями."""
        context = ParseContext(
            block='79. Размер средств на оплату труда рабочих ($\\text{ОТ}_{тек}$) '
                'определяется в текущем уровне цен [по формуле (1)](#formula-1):\n'
                '<a id="formula-1"></a>\n'
                '$$\n'
                '\\text{ОТ}_{тек} = \\sum_{i=1}^I\\text{ЗТ}_i × \\text{СЦ}_{\\text{тек}i}^\\text{ЗТ}\\cdot V_i \\tag{1}\n'
                '$$\n'
                'где:\n'
                '- $\\text{ЗТ}_i$ - затраты труда рабочих, чел.-ч;\n'
                '- $\\text{СЦ}_{\\text{тек}i}^\\text{ЗТ}$ - сметная цена на затраты труда, руб./ чел.-ч;\n'
                '- $V_i$ - объем работ по $i$-ой сметной норме.'
        )
        
        node = handler.handle(context)
        
        assert isinstance(node, PointNode)
        assert node.number == '79'
        
        # Проверяем структуру
        assert len(node.children) == 2  # 1 абзац + 1 формула
        
        # Первый ребёнок — вводный текст
        assert isinstance(node.children[0], ParagraphNode)
        assert 'Размер средств на оплату труда' in node.children[0].text
        
        # Второй ребёнок — FormulaNode
        formula = node.children[1]
        assert isinstance(formula, FormulaNode)
        assert formula.number == '1'
        
        # 🔑 Формула должна содержать определения как детей
        definitions = [c for c in formula.children if c.node_type == 'definition']
        assert len(definitions) >= 3
        
        # Проверяем содержимое определений
        assert any('ЗТ' in d.term for d in definitions)
        assert any('СЦ' in d.term for d in definitions)
        assert any('V' in d.term for d in definitions)
        
        # 🔑 НЕ должно быть отдельного ParagraphNode с определениями
        paragraphs = [c for c in node.children if c.node_type == 'paragraph']
        assert len(paragraphs) == 1  # Только вводный текст

    def test_handle_multiline_list_items(self, handler):
        """Пункты списка г и д содержат по два абзаца."""
        context = ParseContext(
            block='8. Состав затрат, учитываемых в коммерческих предложениях:\n'
                '    а) стоимость временной эксплуатации или аренда несерийных строительных машин...;\n'
                '    б) техническое обслуживание (в том числе стоимость комплекта запасных частей)...;\n'
                '    в) оплата труда машинистов (в том числе инженерно-технические работники)...;\n'
                '    г) перебазировка. В тех случаях, когда перебазировка не учтена...\n'
                '    Данные затраты могут быть учтены единым коммерческим предложением вместе с затратами на приведение в рабочее состояние и разборка при перебазировке;\n'
                '    д) приведение в рабочее состояние и разборка при перебазировке. В тех случаях...\n'
                '    Данные затраты могут быть учтены единым коммерческим предложением вместе с затратами на перебазировку;\n'
                '    е) энергоносители, смазочные материалы и другие технические жидкости на время эксплуатации.'
        )
        
        node = handler.handle(context)
        assert node.number == "8"  # Нет номера пункта, только текст заголовка в children[0]
        
        # Находим пункт "г"
        point_g = next(c for c in node.children if getattr(c, 'number', None) == 'г')
        
        # 🔑 Проверяем: у пункта "г" должно быть 2 дочерних абзаца
        assert len(point_g.children) == 2
        assert isinstance(point_g.children[0], ParagraphNode)
        assert point_g.children[0].number == '1'
        assert 'перебазировка' in point_g.children[0].text
        
        assert isinstance(point_g.children[1], ParagraphNode)
        assert point_g.children[1].number == '2'
        assert 'Данные затраты могут быть учтены' in point_g.children[1].text
        
        # То же самое для пункта "д"
        point_d = next(c for c in node.children if getattr(c, 'number', None) == 'д')
        assert len(point_d.children) == 2
        assert 'приведение в рабочее состояние' in point_d.children[0].text
        assert 'Данные затраты могут быть учтены' in point_d.children[1].text

    def test_handle_list_with_following_paragraphs_no_indent(self, handler):
        """Абзацы после списка без отступа — отдельные узлы."""
        # 🔑 ИСПРАВЛЕНИЕ: добавляем номер пункта в начало
        context = ParseContext(
            block='8. Состав затрат:\n'
                '    а) пункт а;\n'
                '    б) пункт б;\n'
                '    е) энергоносители.\n'
                'Первый абзац после списка.\n'
                'Второй абзац после списка.'
        )
        
        node = handler.handle(context)
        
        # 🔑 Теперь node — это PointNode с номером 8
        assert isinstance(node, PointNode)
        assert node.number == '8'
        
        # Первый ребёнок — вводная строка "Состав затрат:"
        assert node.children[0].node_type == 'paragraph'
        assert 'Состав затрат' in node.children[0].text
        
        # Пункты списка — PointNode
        point_a = next(c for c in node.children if getattr(c, 'number', None) == 'а')
        point_b = next(c for c in node.children if getattr(c, 'number', None) == 'б')
        point_e = next(c for c in node.children if getattr(c, 'number', None) == 'е')
        
        # Пункт "е" — только 1 абзац
        assert len(point_e.children) == 1
        assert 'энергоносители' in point_e.children[0].text
        
        # 🔑 Последующие абзацы без отступа — отдельные ParagraphNode
        paragraphs_after_list = [
            c for c in node.children 
            if c.node_type == 'paragraph' and c.number not in [None, '1']
        ]
        
        # Или проще — проверяем по содержимому
        all_text = [c.text for c in node.children if c.node_type == 'paragraph']
        assert any('Первый абзац после списка' in t for t in all_text)
        assert any('Второй абзац после списка' in t for t in all_text)