# tests/test_handlers/test_amendment_handler.py
import pytest
from handlers.base import ParseContext
from parsers.amendment_document_parser import AmendmentDocumentParser
from handlers.amendment_handler import AmendmentHandler
from nodes.concrete import PointNode, ParagraphNode
from nodes.amendments import (
    AmendmentNode, ExcludeAmendmentNode, AddAmendmentNode,
    ReplaceWordsAmendmentNode, ReplaceAmendmentNode
)
from nodes.target import ComponentType


class TestAmendmentHandler:
    
    @pytest.fixture
    def handler(self):
        return AmendmentHandler()

    @pytest.fixture
    def parser(self):
        return AmendmentDocumentParser()
    
    def test_parse_amendment_with_subpoints(self, handler):
        """
        Парсинг составного изменения с подпунктами.
        
        Структура:
        AmendmentNode (2., composite, target=POINT('4'))
        ├── PointNode (а)
        │   └── ExcludeAmendmentNode (old_text='на работы...')
        └── PointNode (б)
            └── AddAmendmentNode (anchor='(далее...)', new_text='сметой...')
        """
        context = ParseContext(
            block='2. В пункте 4:\n'
                  'а) слова «на работы по сохранению объектов культурного наследия,» '
                  'исключить;\n'
                  'б) после слов «(далее — Положение № 87)» дополнить словами '
                  '«сметой на работы по сохранению объектов культурного наследия».'
        )
        
        node = handler.handle(context)
        
        # 🔑 Проверка родительского узла
        assert isinstance(node, AmendmentNode)
        assert node.number == '2'
        assert node.action == 'composite'
        
        # 🔑 Проверка целевого адреса
        assert node.target is not None
        assert len(node.target.components) == 1
        assert node.target.components[0].type == ComponentType.POINT
        assert node.target.components[0].value == '4'
        assert node.target.get_component_at_level(1).value == '4'
        
        # 🔑 Проверка количества подпунктов
        assert len(node.children) == 2
        
        # 🔑 Проверка подпункта а) — exclude
        subpoint_a = node.children[0]
        assert isinstance(subpoint_a, PointNode)
        assert subpoint_a.number == 'а'
        assert len(subpoint_a.children) == 1
        
        exclude_amendment = subpoint_a.children[0]
        assert isinstance(exclude_amendment, ExcludeAmendmentNode)
        assert exclude_amendment.action == 'exclude'
        assert exclude_amendment.old_text == 'на работы по сохранению объектов культурного наследия,'
        # Целевой адрес наследуется от родителя
        assert exclude_amendment.target.get_component_at_level(1).value == '4'
        
        # 🔑 Проверка подпункта б) — add
        subpoint_b = node.children[1]
        assert isinstance(subpoint_b, PointNode)
        assert subpoint_b.number == 'б'
        assert len(subpoint_b.children) == 1
        
        add_amendment = subpoint_b.children[0]
        assert isinstance(add_amendment, AddAmendmentNode)
        assert add_amendment.action == 'add'
        assert add_amendment.anchor == '(далее — Положение № 87)'
        assert add_amendment.new_text == 'сметой на работы по сохранению объектов культурного наследия'
        assert add_amendment.target.get_component_at_level(1).value == '4'
    
    def test_parse_amendment_with_three_subpoints(self, handler):
        """Три подпункта в одном изменении — все с корректными формулировками."""
        context = ParseContext(
            block='5. В пункте 10:\n'
                'а) слова «старые» заменить словами «новые»;\n'
                'б) слова «лишние» исключить;\n'
                'в) после слов «действующие» дополнить словами «дополнительные».'
        )
        
        node = handler.handle(context)
        
        assert node.action == 'composite'
        assert len(node.children) == 3
        
        # а) — replace_words
        replace_a = node.children[0].children[0]
        assert isinstance(replace_a, ReplaceWordsAmendmentNode)
        assert replace_a.old_text == 'старые'
        assert replace_a.new_text == 'новые'
        
        # б) — exclude
        exclude_b = node.children[1].children[0]
        assert isinstance(exclude_b, ExcludeAmendmentNode)
        assert exclude_b.old_text == 'лишние'
        
        # 🔑 в) — add С ЯКОРЕМ (корректная формулировка)
        add_c = node.children[2].children[0]
        assert isinstance(add_c, AddAmendmentNode)
        assert add_c.anchor == 'действующие'
        assert add_c.new_text == 'дополнительные'
    
    def test_parse_amendment_with_subpoints_and_paragraph_target(self, handler):
        """Составное изменение с указанием абзаца."""
        from nodes.target import ComponentType
        
        context = ParseContext(
            block='10. В абзаце первом пункта 80:\n'
                'а) слова «старые» заменить словами «новые»;\n'
                'б) дополнить словами «дополнительные».'
        )
        
        node = handler.handle(context)
        
        assert node.action == 'composite'
        
        # Проверяем, что целевой адрес содержит и пункт, и абзац
        assert len(node.target.components) >= 2
        assert node.target.components[0].type == ComponentType.POINT
        assert node.target.components[0].value == '80'
        assert node.target.components[1].type == ComponentType.PARAGRAPH
        assert node.target.components[1].value == '1'
        
        # Проверяем, что подпункты получили тот же адрес
        for child in node.children:
            sub_amendment = child.children[0]
            assert sub_amendment.target.get_component_at_level(1).value == '80'
            
            # 🔑 ИСПРАВЛЕНИЕ: используем поиск по типу компонента
            paragraph_comp = next(
                (c for c in sub_amendment.target.components 
                if c.type == ComponentType.PARAGRAPH),
                None
            )
            assert paragraph_comp is not None, \
                f"В target должен быть компонент PARAGRAPH: {sub_amendment.target.components}"
            assert paragraph_comp.value == '1', \
                f"Номер абзаца должен быть '1', получен '{paragraph_comp.value}'"
    
    def test_parse_amendment_with_subpoints_and_subpoint_target(self, handler):
        """Составное изменение с указанием подпункта."""
        context = ParseContext(
            block='15. В подпункте а пункта 4:\n'
                  'а) слова «старые» заменить словами «новые»;\n'
                  'б) дополнить словами «дополнительные».'
        )
        
        node = handler.handle(context)
        
        assert node.action == 'composite'
        
        # 🔑 Проверяем целевой адрес: пункт + подпункт
        assert len(node.target.components) == 2
        assert node.target.components[0].type == ComponentType.POINT
        assert node.target.components[0].value == '4'
        assert node.target.components[1].type == ComponentType.POINT
        assert node.target.components[1].level == 2
        assert node.target.components[1].value == 'а'

    def test_split_blocks_amendment_17_and_18(self, parser):
        """Пункты 17 и 18 разделяются корректно."""
        text = (
            '17. Пункт 24 Методики изложить в следующей редакции:\n'
            '«\n'
            '24. Вместо кода группы допускается указывать код раздела '
            '(части, книги) с указанием нулей в недостающих группах цифр, '
            'например, 64.4.00.00. Для материальных ресурсов и оборудования, '
            'не подлежащих включению в КСР, вместо кода группы указывается '
            'следующая комбинация цифр: 101 — для технологического оборудования '
            '102 — для материальных — ресурсов индивидуального изготовления, '
            '103 — для инженерного оборудования индивидуального изготовления, '
            '104 — для производственного и хозяйственного инвентаря, в том числе '
            'мебели, 105 — для лабораторного оборудования, 106 — для транспортных '
            'средств, 107 — для инструмента, используемого в целях. осуществления '
            'технологических процессов.\n'
            '»\n'
            '18. В пункте 27 слова «и являются ее неотъемлемыми частями» исключить.'
        )
        
        blocks = parser._split_into_blocks(text)
        
        # 🔑 Должно быть 2 блока
        assert len(blocks) == 2, \
            f"Ожидалось 2 блока, получено {len(blocks)}: " \
            f"{[b[:50] for b in blocks]}"
        
        assert blocks[0].startswith('17.')
        assert blocks[1].startswith('18.')


    def test_find_valid_quote_ranges_amendment_17(self, parser):
        """Цитата пункта 17 распознаётся как валидная."""
        text = (
            '17. Пункт 24 Методики изложить в следующей редакции:\n'
            '«\n'
            '24. Вместо кода группы ...\n'
            '»'
        )
        
        ranges = parser._find_valid_quote_ranges(text)
        
        # 🔑 Должна быть одна валидная пара
        assert len(ranges) == 1
        start, end = ranges[0]
        assert text[start] == '«'
        assert text[end] == '»'
        
        # Проверяем, что внутри есть \n24.
        segment = text[start:end]
        assert '\n24.' in segment


    def test_find_valid_quote_ranges_amendment_18(self, parser):
        """Короткая кавычка в пункте 18 распознаётся как валидная."""
        text = 'В пункте 27 слова «и являются ее неотъемлемыми частями» исключить.'
        
        ranges = parser._find_valid_quote_ranges(text)
        
        # 🔑 Должна быть одна валидная пара
        assert len(ranges) == 1
        start, end = ranges[0]
        assert text[start:end+1] == '«и являются ее неотъемлемыми частями»'


    def test_parse_amendments_17_and_18(self, parser):
        """Интеграционный тест: пункты 17 и 18 парсятся отдельно."""
        from nodes.amendments import ReplaceAmendmentNode, ExcludeAmendmentNode
        
        text = (
            '17. Пункт 24 Методики изложить в следующей редакции:\n'
            '«\n'
            '24. Вместо кода группы допускается указывать код раздела '
            '(части, книги) с указанием нулей в недостающих группах цифр, '
            'например, 64.4.00.00.\n'
            '»\n'
            '18. В пункте 27 слова «и являются ее неотъемлемыми частями» исключить.'
        )
        
        nodes = parser.parse(text)
        
        # 🔑 Должно быть 2 узла
        assert len(nodes) == 2, \
            f"Ожидалось 2 узла, получено {len(nodes)}: " \
            f"{[(type(n).__name__, getattr(n, 'number', 'N/A')) for n in nodes]}"
        
        # Пункт 17 — replace
        node_17 = nodes[0]
        assert isinstance(node_17, ReplaceAmendmentNode)
        assert node_17.number == '17'
        assert len(node_17.new_content) >= 1
        assert node_17.new_content[0].number == '24'
        
        # Пункт 18 — exclude
        node_18 = nodes[1]
        assert isinstance(node_18, ExcludeAmendmentNode)
        assert node_18.number == '18'
        assert node_18.old_text == 'и являются ее неотъемлемыми частями'

    def test_parse_add_points_amendment(self):
        """Парсер для 'дополнить пунктами X — Y'."""
        from parsers.amendment_parsers import AddPointsParser
        from nodes.target import TargetAddress
        from nodes.amendments import AddPointsAmendmentNode
        
        parser = AddPointsParser()
        
        text = (
            'Дополнить пунктами 190 — 192 следующего содержания:\n'
            '«\n'
            '190. В случае принятия застройщиком или техническим заказчиком '
            'решения о консервации объекта капитального строительства затраты '
            'на проведение работ по консервацию такого объекта определяются '
            'с использованием сметных нормативов.\n'
            '191. В случае принятия застройщиком или техническим заказчиком '
            'решения о возобновлении строительства (реконструкции) законсервированного '
            'объекта проводится техническое обследование объекта.\n'
            'Затраты на проведение технического обследования объекта и разработку '
            '(корректировку) проектной документации определяются с использованием '
            'сметных нормативов.\n'
            '192. Если строительство (реконструкция) объекта было приостановлено '
            'на срок более 6 месяцев, то осуществляются мероприятия, установленные '
            'пунктами 12, 13 Правил проведения консервации ОКС.\n'
            '»'
        )
        
        target = TargetAddress.empty()
        
        assert parser.can_parse(text) is True
        
        node = parser.parse(text, target)
        
        assert isinstance(node, AddPointsAmendmentNode)
        assert node.action == 'add_points'
        assert node.point_range == ('190', '192')
        
        # 🔑 Должно быть 3 пункта
        assert len(node.new_content) == 3
        
        # Проверяем номера пунктов
        point_numbers = [p.number for p in node.new_content]
        assert point_numbers == ['190', '191', '192']
        
        # Проверяем содержимое
        point_190 = node.new_content[0]
        assert 'консервации объекта капитального строительства' in point_190.children[0].text
        
        point_191 = node.new_content[1]
        # 🔑 Пункт 191 содержит 2 абзаца
        assert len(point_191.children) == 2
        assert 'техническое обследование объекта' in point_191.children[0].text
        assert 'Затраты на проведение технического обследования' in point_191.children[1].text
        
        point_192 = node.new_content[2]
        assert 'приостановлено на срок более 6 месяцев' in point_192.children[0].text


    def test_amendment_handler_add_points(self):
        """AmendmentHandler корректно обрабатывает 'дополнить пунктами'."""
        from handlers.amendment_handler import AmendmentHandler
        from handlers.base import ParseContext
        from nodes.amendments import AddPointsAmendmentNode
        
        handler = AmendmentHandler()
        
        context = ParseContext(
            block='70. Дополнить пунктами 190 — 192 следующего содержания:\n'
                '«\n'
                '190. Текст пункта 190.\n'
                '191. Текст пункта 191.\n'
                '192. Текст пункта 192.\n'
                '»'
        )
        
        node = handler.handle(context)
        
        assert isinstance(node, AddPointsAmendmentNode)
        assert node.number == '70'
        assert node.action == 'add_points'
        assert node.point_range == ('190', '192')
        assert len(node.new_content) == 3

    def test_split_blocks_amendment_70_add_points(self, parser):
        """Пункт 70 с 'дополнить пунктами ... следующего содержания:'."""
        text = (
            '70. Дополнить пунктами 190 — 192 следующего содержания:\n'
            '«\n'
            '190. В случае принятия застройщиком или техническим заказчиком '
            'решения о консервации объекта капитального строительства затраты '
            'на проведение работ по консервацию такого объекта определяются '
            'с использованием сметных нормативов.\n'
            '191. В случае принятия застройщиком или техническим заказчиком '
            'решения о возобновлении строительства (реконструкции) законсервированного '
            'объекта проводится техническое обследование объекта.\n'
            'Затраты на проведение технического обследования объекта и разработку '
            '(корректировку) проектной документации определяются с использованием '
            'сметных нормативов.\n'
            '192. Если строительство (реконструкция) объекта было приостановлено '
            'на срок более 6 месяцев, то осуществляются мероприятия, установленные '
            'пунктами 12, 13 Правил проведения консервации ОКС.\n'
            '»'
        )
        
        blocks = parser._split_into_blocks(text)
        
        # 🔑 Должен быть 1 блок (весь пункт 70 целиком)
        assert len(blocks) == 1, \
            f"Ожидалось 1 блок, получено {len(blocks)}: {[b[:50] for b in blocks]}"
        
        # 🔑 Блок должен содержать всю цитату
        assert '190. В случае принятия' in blocks[0]
        assert '191. В случае принятия' in blocks[0]
        assert '192. Если строительство' in blocks[0]
        assert '»' in blocks[0]


    def test_find_valid_quote_ranges_following_content(self, parser):
        """Кавычка после 'следующего содержания:' валидна."""
        text = (
            'Дополнить пунктами 190 — 192 следующего содержания:\n'
            '«\n'
            '190. Текст пункта.\n'
            '»'
        )
        
        ranges = parser._find_valid_quote_ranges(text)
        
        # 🔑 Должна быть одна валидная пара
        assert len(ranges) == 1
        start, end = ranges[0]
        assert text[start] == '«'
        assert text[end] == '»'


    def test_parse_amendment_70_full_flow(self, parser):
        """Полный поток парсинга пункта 70."""
        from nodes.amendments import AddPointsAmendmentNode
        
        text = (
            '70. Дополнить пунктами 190 — 192 следующего содержания:\n'
            '«\n'
            '190. Текст пункта 190.\n'
            '191. Текст пункта 191.\n'
            '192. Текст пункта 192.\n'
            '»'
        )
        
        nodes = parser.parse(text)
        
        assert len(nodes) == 1
        node = nodes[0]
        
        assert isinstance(node, AddPointsAmendmentNode)
        assert node.number == '70'
        assert node.point_range == ('190', '192')
        assert len(node.new_content) == 3


    def test_quote_intro_pattern_various_forms(self, parser):
        """Проверка всех форм ключевых слов."""
        test_cases = [
            ('изложить в следующей редакции:\n«текст»', True),
            ('дополнить абзацем следующего содержания:\n«текст»', True),
            ('дополнить пунктами 190 — 192 следующего содержания:\n«текст»', True),
            ('в следующей формулировке:\n«текст»', True),
        ]
        
        for text, expected_valid in test_cases:
            ranges = parser._find_valid_quote_ranges(text)
            is_valid = len(ranges) > 0
            assert is_valid == expected_valid, \
                f"Для '{text[:40]}...' ожидалось valid={expected_valid}, получено {is_valid}"
    
    def test_parse_add_section_amendment(self):
        """Парсер для 'дополнить разделом XII'."""
        from parsers.amendment_parsers import AddSectionParser
        from nodes.target import TargetAddress
        from nodes.amendments import AddSectionAmendmentNode
        
        parser = AddSectionParser()
        
        text = (
            'Дополнить Методику разделом XII следующего содержания:\n'
            '«\n'
            '## XII. Особенности определения сметной стоимости работ по сохранению '
            'объектов культурного наследия\n'
            '193. Определение сметной стоимости работ по сохранению объектов '
            'культурного наследия на этапе архитектурно-строительного проектирования '
            'базисно-индексным методом осуществляется с применением Сборника цен '
            'на научно-проектные работы по памятникам истории и культуры '
            '(далее — Сборник СЦНПР-91).\n'
            '194. Пересчет в текущий уровень цен стоимости научно-проектных работ '
            'по памятникам истории и культуры выполняется с применением индексов '
            'изменения сметной стоимости.\n'
            '»'
        )
        
        target = TargetAddress.empty()
        
        assert parser.can_parse(text) is True
        
        node = parser.parse(text, target)
        
        assert isinstance(node, AddSectionAmendmentNode)
        assert node.action == 'add_section'
        assert 'XII' in node.section_title
        assert 'Особенности определения' in node.section_title
        
        # 🔑 Должно быть: SectionNode + 2 PointNode
        assert len(node.new_content) >= 2
        
        # Проверяем наличие пунктов
        points = [n for n in node.new_content if getattr(n, 'number', None) in ['193', '194']]
        assert len(points) == 2
        
        point_193 = next(p for p in points if p.number == '193')
        assert 'Сборник СЦНПР-91' in point_193.children[0].text
        
        point_194 = next(p for p in points if p.number == '194')
        assert 'Пересчет в текущий уровень цен' in point_194.children[0].text


    def test_parse_add_section_with_double_close_quote(self):
        """Обработка опечатки с двойной закрывающей кавычкой."""
        from parsers.amendment_parsers import AddSectionParser
        from nodes.target import TargetAddress
        from nodes.amendments import AddSectionAmendmentNode
        
        parser = AddSectionParser()
        
        # 🔑 Текст с опечаткой: две закрывающие »
        text = (
            'Дополнить Методику разделом XII следующего содержания:\n'
            '«\n'
            '## XII. Заголовок раздела\n'
            '193. Текст пункта 193.\n'
            '194. Текст пункта 194.»\n'
            '\n'
            '«'  # ← лишняя открывающая кавычка (опечатка)
        )
        
        target = TargetAddress.empty()
        
        # 🔑 Парсер должен обработать опечатку
        node = parser.parse(text, target)
        
        assert isinstance(node, AddSectionAmendmentNode)
        assert len(node.new_content) >= 2


    def test_amendment_handler_add_section(self):
        """AmendmentHandler корректно обрабатывает 'дополнить разделом'."""
        from handlers.amendment_handler import AmendmentHandler
        from handlers.base import ParseContext
        from nodes.amendments import AddSectionAmendmentNode
        
        handler = AmendmentHandler()
        
        context = ParseContext(
            block='71. Дополнить Методику разделом XII следующего содержания:\n'
                '«\n'
                '## XII. Особенности определения сметной стоимости работ по сохранению '
                'объектов культурного наследия\n'
                '193. Текст пункта 193.\n'
                '194. Текст пункта 194.\n'
                '»'
        )
        
        node = handler.handle(context)
        
        assert isinstance(node, AddSectionAmendmentNode)
        assert node.number == '71'
        assert node.action == 'add_section'
        assert 'XII' in node.section_title

    def test_parse_add_section_with_double_close_quote(self):
        """Двойная закрывающая » в конце обрабатывается корректно."""
        from parsers.amendment_parsers import AddSectionParser
        from nodes.target import TargetAddress
        
        parser = AddSectionParser()
        
        text = (
            'Дополнить Методику разделом XII следующего содержания:\n'
            '«\n'
            '## XII. Заголовок\n'
            '193. Текст.\n'
            '»»'  # ← двойная закрывающая (опечатка)
        )
        
        node = parser.parse(text, TargetAddress.empty())
        
        # Обе » должны быть удалены
        points = [n for n in node.new_content if hasattr(n, 'number') and n.number == '193']
        assert len(points) == 1
        text_193 = ' '.join(p.text for p in points[0].children)
        assert '»' not in text_193

    def test_debug_split_blocks_amendment_71(self, parser):
        """Отладка: что происходит при разбиении блока пункта 71."""
        text = (
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
        
        print("\n" + "=" * 80)
        print("ОТЛАДКА: РАЗБИЕНИЕ БЛОКА ПУНКТА 71")
        print("=" * 80)
        
        # 🔍 1. Находим все « и »
        import re
        opens = [m.start() for m in re.finditer(r'«', text)]
        closes = [m.start() for m in re.finditer(r'»', text)]
        
        print(f"\n1. НАЙДЕНО КАВЫЧЕК:")
        print(f"   Открывающих «: {len(opens)} на позициях {opens}")
        print(f"   Закрывающих »: {len(closes)} на позициях {closes}")
        
        for pos in opens:
            context = text[max(0, pos-20):pos+30].replace('\n', '\\n')
            print(f"   « на {pos}: ...{context}...")
        
        for pos in closes:
            context = text[max(0, pos-20):pos+30].replace('\n', '\\n')
            print(f"   » на {pos}: ...{context}...")
        
        # 🔍 2. Проверяем _find_valid_quote_ranges
        print(f"\n2. ВАЛИДНЫЕ ПАРЫ КАВЫЧЕК:")
        ranges = parser._find_valid_quote_ranges(text)
        print(f"   Найдено {len(ranges)} валидных пар:")
        for open_pos, close_pos in ranges:
            content_preview = text[open_pos:close_pos+1][:80].replace('\n', '\\n')
            print(f"   [{open_pos}:{close_pos}] {content_preview}...")
        
        # 🔍 3. Проверяем разбиение на блоки
        print(f"\n3. РАЗБИЕНИЕ НА БЛОКИ:")
        blocks = parser._split_into_blocks(text)
        print(f"   Найдено {len(blocks)} блоков:")
        for i, block in enumerate(blocks):
            preview = block[:150].replace('\n', '\\n')
            print(f"\n   Блок {i+1} (длина {len(block)}):")
            print(f"   {preview}...")
        
        # 🔍 4. Проверяем, что содержит первый блок
        print(f"\n4. СОДЕРЖИМОЕ ПЕРВОГО БЛОКА:")
        if blocks:
            block = blocks[0]
            print(f"   Содержит '193.': {'193.' in block}")
            print(f"   Содержит '(далее — Сборники ССН-84)': {'(далее — Сборники ССН-84)' in block}")
            print(f"   Содержит '194.': {'194.' in block}")
            print(f"   Содержит 'Постановления № 1452': {'Постановления № 1452' in block}")
        
        print("=" * 80 + "\n")
        
        # Базовая проверка
        assert len(blocks) == 1, f"Ожидалось 1 блок, получено {len(blocks)}"

    def test_split_blocks_three_separate_amendments(self, parser):
        """Три пункта (3, 4, 5) разделяются на три блока."""
        text = (
            '3. Пункт 5 изложить в следующей редакции: «5. В сметной стоимости '
            'строительства учитываются затраты...».\n\n'
            '4. Пункт 6 изложить в следующей редакции: «Стоимость строительно-монтажных '
            'работ и пусконаладочных работ включает...».\n\n'
            '5. В пункте 8:\n'
            'а) в подпункте «г» слова «единичные расценки» заменить словами «единичные расценки;»;\n'
            'б) дополнить подпунктом «д» в следующей редакции: «\n'
            'д) сметные цены на эксплуатацию машин...\n'
            '»'
        )
        
        blocks = parser._split_into_blocks(text)
        
        # 🔑 Должно быть 3 блока
        assert len(blocks) == 3, \
            f"Ожидалось 3 блока, получено {len(blocks)}: {[b[:50] for b in blocks]}"
        
        assert blocks[0].startswith('3.')
        assert blocks[1].startswith('4.')
        assert blocks[2].startswith('5.')
    
    def test_split_blocks_amendment_71_with_nested_quotes(self, parser):
        """Пункт 71 с вложенными кавычками и пунктом 206."""
        text = (
            '71. Дополнить Методику разделом XII следующего содержания:\n'
            '«\n'
            '## XII. Заголовок\n'
            '193. Текст с опечаткой (ССН- 84)» (далее — ССН-84).\n'
            '205. Текст с «вложенной кавычкой» и «ещё одной вложенной».\n'
            '206. Текст пункта 206.\n'
            '»'
        )
        
        blocks = parser._split_into_blocks(text)
        
        # 🔑 Должен быть 1 блок
        assert len(blocks) == 1, \
            f"Ожидалось 1 блок, получено {len(blocks)}"
        
        assert '193.' in blocks[0]
        assert '205.' in blocks[0]
        assert '206.' in blocks[0]
    
    def test_debug_split_blocks_with_typo_in_193(self, parser):
        """Отладка: как опечатка » в пункте 193 влияет на разбиение блока."""
        text = (
            '71. Дополнить Методику разделом XII следующего содержания:\n'
            '«\n'
            '## XII. Заголовок\n'
            '193. Текст с опечаткой (ССН- 84)» (далее — ССН-84).\n'
            '194. Текст пункта 194.\n'
            '195. При определении сметной стоимости... выполняется расчет:\n'
            'а) накладных расходов...;\n'
            'б) накладных расходов...;\n'
            'в) сметной прибыли...;\n'
            'г) расходов на эксплуатацию...\n'
            '196. Текст пункта 196.\n'
            '»'
        )
        
        print("\n" + "=" * 80)
        print("ОТЛАДКА: ОПЕЧАТКА » В ПУНКТЕ 193")
        print("=" * 80)
        
        # 1. Все кавычки
        import re
        opens = [m.start() for m in re.finditer(r'«', text)]
        closes = [m.start() for m in re.finditer(r'»', text)]
        
        print(f"\n1. ВСЕ КАВЫЧКИ:")
        print(f"   Открывающих «: {len(opens)} на позициях {opens}")
        print(f"   Закрывающих »: {len(closes)} на позициях {closes}")
        
        for pos in closes:
            context = text[max(0, pos-30):pos+30].replace('\n', '\\n')
            print(f"   » на {pos}: ...{context}...")
        
        # 2. Валидные диапазоны
        print(f"\n2. ВАЛИДНЫЕ ДИАПАЗОНЫ:")
        ranges = parser._find_valid_quote_ranges(text)
        print(f"   Найдено {len(ranges)} пар:")
        for i, (open_pos, close_pos) in enumerate(ranges):
            print(f"   Пара {i+1}: [{open_pos}:{close_pos}]")
            print(f"      Открытие: {text[open_pos:open_pos+50]!r}")
            print(f"      Закрытие: {text[close_pos-30:close_pos+10]!r}")
        
        # 3. Позиции подпунктов
        print(f"\n3. ПОЗИЦИИ ПОДПУНКТОВ:")
        subpoint_pattern = re.compile(r'(?:^|\n)([а-яё])\)\s+', re.MULTILINE)
        subpoint_matches = list(subpoint_pattern.finditer(text))
        
        for match in subpoint_matches:
            pos = match.start()
            letter = match.group(1)
            in_range = parser._is_in_any_range(pos, ranges)
            print(f"   Подпункт {letter}) на позиции {pos}: {'ВНУТРИ КАВЫЧКИ' if in_range else 'СВОБОДНО'}")
            print(f"      Контекст: {text[pos:pos+40]!r}")
        
        # 4. Разбиение на блоки
        print(f"\n4. РАЗБИЕНИЕ НА БЛОКИ:")
        blocks = parser._split_into_blocks(text)
        print(f"   Найдено {len(blocks)} блоков:")
        for i, block in enumerate(blocks):
            print(f"\n   Блок {i+1} (длина {len(block)}):")
            print(f"   {block[:150]!r}...")
        
        print("=" * 80 + "\n")
        
        assert len(blocks) == 1, f"Ожидалось 1 блок, получено {len(blocks)}"