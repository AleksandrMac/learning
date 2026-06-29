import pytest
import re
from typing import List, Tuple
from handlers.base import ParseContext
from handlers.amendment_handler import AmendmentHandler
from parsers.amendment_parsers import ReplaceAmendmentParser, ExcludeAmendmentParser
from nodes.amendments import (
    ExcludeAmendmentNode, AddAmendmentNode, AmendmentNode,
    ReplaceWordsAmendmentNode, ReplaceAmendmentNode, RepealAmendmentNode,
    MultipleReplaceWordsAmendmentNode, AddParagraphAmendmentNode
)
from nodes.target import TargetAddress, TargetComponent, ComponentType


class TestExcludeAmendmentParser:
    
    @pytest.fixture
    def parser(self):
        return ExcludeAmendmentParser()
    
    @pytest.mark.parametrize("text,expected_old_text", [
        # Единственное число
        ('слово «ближайших» исключить', 'ближайших'),
        ('в абзаце третьем слово «ближайших» исключить', 'ближайших'),
        
        # Множественное число
        ('слова «старые данные» исключить', 'старые данные'),
        ('в пункте 5 слова «X» исключить', 'X'),
        
        # Родительный падеж (редко)
        ('из текста слов «лишнее» исключить', 'лишнее'),
    ])
    def test_parse_various_forms(self, parser, text, expected_old_text):
        """Парсер поддерживает разные формы слова 'слово/слова'."""
        target = TargetAddress(components=[
            TargetComponent(ComponentType.POINT, '14', level=1)
        ])
        
        assert parser.can_parse(text) is True, \
            f"Парсер не распознал текст: '{text}'"
        
        node = parser.parse(text, target)
        
        assert isinstance(node, ExcludeAmendmentNode)
        assert node.action == 'exclude'
        assert node.old_text == expected_old_text
    
    def test_parse_with_paragraph_in_target(self, parser):
        """
        Реальный кейс из пункта 11.г):
        "в абзаце третьем слово «ближайших» исключить"
        
        Target уже содержит PARAGRAPH('3'), добавленный TargetParser.
        """
        text = 'в абзаце третьем слово «ближайших» исключить'
        
        # 🔑 TargetParser уже извлёк абзац
        target = TargetAddress(components=[
            TargetComponent(ComponentType.POINT, '14', level=1),
            TargetComponent(ComponentType.PARAGRAPH, '3'),
        ])
        
        node = parser.parse(text, target)
        
        assert isinstance(node, ExcludeAmendmentNode)
        assert node.old_text == 'ближайших'
        
        # Target сохранён полностью
        assert node.target.get_component_at_level(1).value == '14'
        assert node.target.paragraph_number == '3'
    
    def test_does_not_match_replace_words(self, parser):
        """Парсер не должен матчить 'слова «X» заменить словами «Y»'."""
        # Это должен обрабатывать ReplaceWordsAmendmentParser
        text = 'слова «старые» заменить словами «новые»'
        
        # can_parse может вернуть True (т.к. "слова ... исключить" не матчит,
        # но если есть "исключить" в конце — то да)
        # Проверяем, что именно наш паттерн НЕ матчит
        match = parser.PATTERN.search(text)
        assert match is None, \
            "ExcludeAmendmentParser не должен матчить 'заменить'"

class TestReplaceAmendmentParser:
    
    @pytest.fixture
    def parser(self):
        return ReplaceAmendmentParser()
    
    def test_extract_balanced_quotes_simple(self, parser):
        """Простые кавычки без вложенности."""
        text = 'изложить в следующей редакции: «новый текст»'
        result = parser._extract_balanced_quotes(text)
        assert result == 'новый текст'
    
    def test_extract_balanced_quotes_nested(self, parser):
        """Вложенные кавычки."""
        text = 'изложить: «текст с «вложенными» кавычками»'
        result = parser._extract_balanced_quotes(text)
        assert result == 'текст с «вложенными» кавычками'
    
    def test_extract_balanced_quotes_multiple_nested(self, parser):
        """Несколько уровней вложенности."""
        text = '«уровень 1 «уровень 2 «уровень 3» конец 2» конец 1»'
        result = parser._extract_balanced_quotes(text)
        assert result == 'уровень 1 «уровень 2 «уровень 3» конец 2» конец 1'
    
    def test_parse_with_digit_number(self, parser):
        """Парсинг пункта с цифровым номером."""
        text = 'Пункт 5 изложить в следующей редакции: «5. Новый текст пункта.»'
        
        target = TargetAddress(components=[
            TargetComponent(ComponentType.POINT, '5')
        ])
        
        node = parser.parse(text, target)
        
        assert isinstance(node, ReplaceAmendmentNode)
        assert len(node.new_content) == 1
        assert node.new_content[0].number == '5'
        assert 'Новый текст пункта' in node.new_content[0].children[0].text
    
    def test_parse_with_letter_number(self, parser):
        """Парсинг подпункта с буквенным номером."""
        text = 'подпункт «б» изложить в следующей редакции: «\nб) Новый текст подпункта.\n»'
        
        target = TargetAddress(components=[
            TargetComponent(ComponentType.POINT, '10')
        ])
        
        node = parser.parse(text, target)
        
        assert isinstance(node, ReplaceAmendmentNode)
        assert len(node.new_content) == 1
        assert node.new_content[0].number == 'б'  # 🔑 Буквенный номер
        assert 'Новый текст подпункта' in node.new_content[0].children[0].text
    
    def test_parse_with_nested_quotes(self, parser):
        """Парсинг с вложенными кавычками (реальный кейс из теста)."""
        text = (
            'подпункт «б» изложить в следующей редакции:\n'
            '«\n'
            'б) базисно-индексным методом — с применением к сметной стоимости.\n'
            'До даты перехода ... постановления ... №1452 «О мониторинге цен '
            'строительных ресурсов» (далее — Постановление № 1452) ...\n'
            '»'
        )
        
        target = TargetAddress(components=[
            TargetComponent(ComponentType.POINT, '10')
        ])
        
        node = parser.parse(text, target)
        
        assert isinstance(node, ReplaceAmendmentNode)
        assert len(node.new_content) == 1
        
        new_point = node.new_content[0]
        assert new_point.number == 'б'
        
        # 🔑 Проверяем, что весь текст захвачен, включая часть после вложенных кавычек
        full_text = ' '.join(p.text for p in new_point.children)
        assert 'базисно-индексным методом' in full_text
        assert 'Постановление № 1452' in full_text
        assert 'О мониторинге цен строительных ресурсов' in full_text
    
    def test_parse_with_markdown_list(self, parser):
        """Парсинг с маркированным списком внутри."""
        text = (
            'Пункт 5 изложить в следующей редакции:\n'
            '«\n'
            '5. Текст пункта:\n'
            '- первый пункт списка;\n'
            '- второй пункт списка;\n'
            '- третий пункт списка.\n'
            '»'
        )
        
        target = TargetAddress()
        node = parser.parse(text, target)
        
        assert len(node.new_content) == 1
        full_text = ' '.join(p.text for p in node.new_content[0].children)
        assert 'первый пункт списка' in full_text
        assert 'второй пункт списка' in full_text
        assert 'третий пункт списка' in full_text
    
    def test_parse_complex_case(self, parser):
        """Полный реальный кейс с вложенными кавычками и длинным текстом."""
        # 🔑 Используем ПОЛНЫЙ текст без сокращений
        text = (
            'подпункт «б» изложить в следующей редакции:\n'
            '«\n'
            'б) базисно-индексным методом — с применением к сметной стоимости, '
            'определенной с использованием единичных расценок, в том числе их '
            'отдельных составляющих, сведения о которых включены в ФРСН, '
            'разработанных в базисном уровне цен, соответствующих индексов '
            'изменения сметной стоимости.\n'
            'До даты перехода на ресурсно-индексный метод определения сметной '
            'стоимости строительства в соответствии с требованиями постановления '
            'Правительства Российской Федерации от 23 декабря 2016 г. №1452 '
            '«О мониторинге цен строительных ресурсов» (Собрание законодательства '
            'Российской Федерации, 2017, № 1, ст. 184; 2022, № 16, ст. 2705) '
            '(далее — Постановление № 1452) в случае выполнения расчета '
            'базисно-индексным методом при отсутствии в ФЕР, ФЕРр, ФЕРм, ФЕРмр '
            'и ФЕРи единичных расценок на отдельные виды работ допускается '
            'калькулирование их стоимости с использованием сметных норм, сведения '
            'о которых включены в ФРСН, разработанных для применения '
            'ресурсно-индексным и ресурсным методами, с одновременным применением '
            'информации о сметных ценах на материальные ресурсы и оборудование, '
            'машины и механизмы в базисном уровне цен, включенных в ФССЦ и ФСЭМ '
            'по состоянию на 1 января 2000 г. в следующем порядке:\n'
            '- оплата труда рабочих и машинистов, пусконаладочного персонала в '
            'текущем уровне цен определяется на основании информации о сметных '
            'ценах на затраты труда рабочих и машинистов, размещенной в ФГИС ЦС, '
            'с учетом коэффициента инфляции на дату составления сметной документации;\n'
            '- при отсутствии в ФСЭМ сметных цен на эксплуатацию машин и механизмов '
            'их цены в базисном уровне цен по состоянию на 1 января 2000 г. '
            'определяются с использованием сметных цен на эксплуатацию машин и '
            'механизмов в уровне цен по состоянию на 1 января 2022 г.;\n'
            '- при отсутствии в ФССЦ сметных цен материальных ресурсов и оборудования '
            'их цены в текущем уровне цен определяются в соответствии с пунктом 13 '
            'Методики;\n'
            '- приведение текущих цен на оплату труда рабочих и машинистов, '
            'эксплуатацию машин и механизмов, материальные ресурсы и оборудование '
            'в базисный уровень цен по состоянию на 1 января 2000 г. осуществляется '
            'обратным счетом путем деления их текущих цен на индекс изменения '
            'сметной стоимости в соответствии с пунктами 11 и 45 Методики;\n'
            '- приведенная цена эксплуатации машин и механизмов в базисном уровне '
            'цен по состоянию на 1 января 2000 г. определяется с добавлением '
            'стоимости оплаты труда машинистов, приведенной в базисный уровень '
            'цен по состоянию на 1 января 2000 г.;\n'
            '- учет в сметной документации стоимости отдельных видов затрат, '
            'определенной указанным способом, выполняется в соответствии с пунктом '
            '38 Методики.\n'
            'Особенности определения сметной стоимости работ по сохранению объектов '
            'культурного наследия на этапе архитектурно-строительного проектирования '
            'приведены в разделе XII Методики. Положения раздела XII Методики '
            'применяются до включения в ФРСН сведений о соответствующих сметных '
            'нормативах на работы по сохранению объектов культурного наследия '
            '(памятников истории и культуры) народов Российской Федерации;\n'
            '»'
        )
        
        target = TargetAddress(components=[
            TargetComponent(ComponentType.POINT, '10')
        ])
        
        node = parser.parse(text, target)
        
        assert isinstance(node, ReplaceAmendmentNode)
        assert len(node.new_content) == 1
        
        new_point = node.new_content[0]
        assert new_point.number == 'б'
        
        # 🔑 Проверяем, что все части захвачены
        full_text = ' '.join(p.text for p in new_point.children)
        
        assert 'базисно-индексным методом' in full_text
        assert 'Постановление № 1452' in full_text
        assert 'оплата труда рабочих и машинистов' in full_text
        assert 'разделе XII Методики' in full_text
        assert 'О мониторинге цен строительных ресурсов' in full_text
        assert 'ФГИС ЦС' in full_text
        assert 'пунктом 13 Методики' in full_text
        assert 'пунктами 11 и 45 Методики' in full_text
        assert 'пунктом 38 Методики' in full_text
        assert 'памятников истории и культуры' in full_text

class TestFindCitationRanges:
    """Табличные тесты для _find_citation_ranges."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Создаём handler для каждого теста."""
        self.handler = AmendmentHandler()
    
    @pytest.mark.parametrize(
        "name, text, expected_count, expected_ranges",
        [
            # ═══════════════════════════════════════════════════════
            # 🔹 Базовые случаи
            # ═══════════════════════════════════════════════════════
            (
                "простая цитата после 'в следующей редакции:'",
                (
                    'подпункт «б» изложить в следующей редакции:\n'
                    '«\n'
                    'б) новый текст подпункта.\n'
                    '»'
                ),
                1,
                [
                    # (open_pos, close_pos, content_contains)
                    ('б) новый текст',)
                ]
            ),
            (
                "цитата после 'следующего содержания:'",
                (
                    'Дополнить Методику разделом XII следующего содержания:\n'
                    '«\n'
                    '## XII. Заголовок\n'
                    '193. Текст пункта.\n'
                    '»'
                ),
                1,
                [
                    ('## XII. Заголовок',)
                ]
            ),
            
            # ═══════════════════════════════════════════════════════
            # 🔹 Опечатки внутри цитаты
            # ═══════════════════════════════════════════════════════
            (
                "опечатка: лишняя » внутри цитаты (ССН- 84)»",
                (
                    'изложить в следующей редакции:\n'
                    '«\n'
                    '193. Текст с опечаткой (ССН- 84)» (далее — ССН-84).\n'
                    '194. Текст пункта 194.\n'
                    '»'
                ),
                1,
                [
                    # Должна найти ОДНУ цитату, включающую оба пункта
                    ('193. Текст с опечаткой', '194. Текст пункта 194')
                ]
            ),
            (
                "вложенные кавычки «Интернет» внутри цитаты",
                (
                    'изложить в следующей редакции:\n'
                    '«\n'
                    '15. Сайт в сети «Интернет» (при наличии).\n'
                    '16. Текст пункта 16.\n'
                    '»'
                ),
                1,
                [
                    ('15. Сайт в сети', '16. Текст пункта 16')
                ]
            ),
            (
                "много вложенных кавычек",
                (
                    'изложить в следующей редакции:\n'
                    '«\n'
                    '205. По строкам «ремонтно-реставрационные работы» и «пересчет»...\n'
                    '206. Текст пункта 206.\n'
                    '»'
                ),
                1,
                [
                    ('205. По строкам', '206. Текст пункта 206')
                ]
            ),
            
            # ═══════════════════════════════════════════════════════
            # 🔹 Несколько цитат в одном тексте
            # ═══════════════════════════════════════════════════════
            (
                "две цитаты подряд",
                (
                    'пункт 5 изложить в следующей редакции: «5. Новый текст пункта 5.».\n\n'
                    'пункт 6 изложить в следующей редакции: «6. Новый текст пункта 6.».'
                ),
                2,
                [
                    ('5. Новый текст пункта 5',),
                    ('6. Новый текст пункта 6',)
                ]
            ),
            
            # ═══════════════════════════════════════════════════════
            # 🔹 Случаи без цитат
            # ═══════════════════════════════════════════════════════
            (
                "нет ключевого слова — цитат нет",
                'слова «старое» заменить словами «новое».',
                0,
                []
            ),
            (
                "ключевое слово без кавычки — цитаты нет",
                'изложить в следующей редакции: текст без кавычек.',
                0,
                []
            ),
            
            # ═══════════════════════════════════════════════════════
            # 🔹 Разные ключевые слова
            # ═══════════════════════════════════════════════════════
            (
                "ключевое слово: 'в следующей формулировке:'",
                (
                    'изложить в следующей формулировке:\n'
                    '«\n'
                    'Новая формулировка.\n'
                    '»'
                ),
                1,
                [
                    ('Новая формулировка',)
                ]
            ),
        ],
        ids=[
            "простая_в_следующей_редакции",
            "следующего_содержания",
            "опечатка_ССН-84",
            "вложенные_кавычки_Интернет",
            "много_вложенных_кавычек",
            "две_цитаты_подряд",
            "нет_ключевого_слова",
            "ключевое_без_кавычки",
            "в_следующей_формулировке",
        ]
    )
    def test_find_citation_ranges(
        self,
        name: str,
        text: str,
        expected_count: int,
        expected_ranges: List[Tuple[str, ...]]
    ):
        """
        Параметризованный тест _find_citation_ranges.
        
        Проверяет:
        - Количество найденных цитат
        - Содержимое каждой цитаты (по ключевым словам)
        """
        ranges = self.handler._find_citation_ranges(text)
        
        # 🔹 Проверка количества
        assert len(ranges) == expected_count, (
            f"[{name}] Ожидалось {expected_count} цитат, найдено {len(ranges)}: "
            f"{[(text[o:c+1][:50]) for o, c in ranges]}"
        )
        
        # 🔹 Проверка содержимого каждой цитаты
        for i, (open_pos, close_pos) in enumerate(ranges):
            content = text[open_pos:close_pos + 1]
            expected_strings = expected_ranges[i]
            
            for expected in expected_strings:
                assert expected in content, (
                    f"[{name}] Цитата #{i+1} не содержит '{expected}':\n"
                    f"Содержимое: {content[:200]}..."
                )
    
    # ═══════════════════════════════════════════════════════
    # 🔹 Дополнительные проверки позиций
    # ═══════════════════════════════════════════════════════
    
    def test_citation_range_positions_are_correct(self):
        """Позиции открытия и закрытия указывают на « и »."""
        text = (
            'изложить в следующей редакции:\n'
            '«\n'
            'Текст цитаты.\n'
            '»'
        )
        
        ranges = self.handler._find_citation_ranges(text)
        assert len(ranges) == 1
        
        open_pos, close_pos = ranges[0]
        assert text[open_pos] == '«', f"Открытие должно быть «, получено: {text[open_pos]!r}"
        assert text[close_pos] == '»', f"Закрытие должно быть », получено: {text[close_pos]!r}"
    
    def test_citation_range_does_not_include_keyword(self):
        """Цитата начинается с «, а не с ключевого слова."""
        text = (
            'изложить в следующей редакции:\n'
            '«\n'
            'Текст.\n'
            '»'
        )
        
        ranges = ranges = self.handler._find_citation_ranges(text)
        open_pos, close_pos = ranges[0]
        
        # Открывающая позиция — это «
        assert text[open_pos] == '«'
        # Перед « нет ключевого слова в самом диапазоне
        content = text[open_pos:close_pos + 1]
        assert 'в следующей редакции' not in content
    
    def test_citation_range_handles_trailing_whitespace(self):
        """Цитата корректно закрывается, если после » есть пробелы."""
        text = (
            'изложить в следующей редакции:\n'
            '«\n'
            'Текст.\n'
            '»   \n'
        )
        
        ranges = ranges = self.handler._find_citation_ranges(text)
        assert len(ranges) == 1
        assert 'Текст.' in text[ranges[0][0]:ranges[0][1] + 1]

class TestAmendmentHandler:
    
    @pytest.fixture
    def handler(self):
        return AmendmentHandler()
    
    def test_handle_composite_amendment(self, handler):
        """Composite amendment с несколькими подпунктами."""
        context = ParseContext(
            block='2. В пункте 4:\n'
                  'а) слова «на работы по сохранению объектов культурного наследия,» исключить;\n'
                  'б) после слов «(далее — Положение № 87)» дополнить словами '
                  '«сметой на работы по сохранению объектов культурного наследия».'
        )
        
        node = handler.handle(context)
        
        assert node.number == '2'
        assert node.action == 'composite'
        
        # Проверяем адрес
        assert node.target.get_component_at_level(1).value == '4'
        assert len(node.target.components) == 1
        assert node.target.components[0].type == ComponentType.POINT
        
        # Подпункты
        assert len(node.children) == 2
        assert node.children[0].number == 'а'
        assert node.children[1].number == 'б'
        
        # Типы amendments
        assert isinstance(node.children[0].children[0], ExcludeAmendmentNode)
        assert isinstance(node.children[1].children[0], AddAmendmentNode)
    
    def test_handle_full_path_target(self, handler):
        """Полная формулировка адреса: абзац N подпункта X пункта Y."""
        context = ParseContext(
            block='37. Абзац четвертый пункта 80 изложить в следующей редакции: '
                  '«Новый текст абзаца».'
        )
        
        node = handler.handle(context)
        
        # Проверяем адрес
        assert len(node.target.components) == 2
        assert node.target.components[0].type == ComponentType.POINT
        assert node.target.components[0].value == '80'
        assert node.target.components[1].type == ComponentType.PARAGRAPH
        assert node.target.components[1].value == '4'
        
        assert node.target.to_path() == '80.para:4'
    
    def test_handle_subpoint_target(self, handler):
        """Целевой адрес с подпунктом."""
        context = ParseContext(
            block='1. В подпункте а пункта 4 слова «старое» заменить словами «новое».'
        )
        
        node = handler.handle(context)
        
        assert len(node.target.components) == 2
        assert node.target.components[0].type == ComponentType.POINT
        assert node.target.components[0].value == '4'
        assert node.target.components[1].type == ComponentType.POINT
        assert node.target.components[1].level == 2
        assert node.target.components[1].value == 'а'
    
    def test_handle_compound_point_target(self, handler):
        """Целевой адрес с составным номером пункта."""
        context = ParseContext(
            block='1. В пункте 4.1 слова «старое» заменить словами «новое».'
        )
        
        node = handler.handle(context)
        
        # 🔑 Теперь "4.1" — это два компонента POINT с разными уровнями
        assert len(node.target.components) == 2
        
        # Первый компонент — пункт level=1
        assert node.target.components[0].type == ComponentType.POINT
        assert node.target.components[0].value == '4'
        assert node.target.components[0].level == 1
        
        # Второй компонент — подпункт level=2
        assert node.target.components[1].type == ComponentType.POINT
        assert node.target.components[1].value == '1'
        assert node.target.components[1].level == 2
        
        # 🔑 Свойство get_component_at_level(1).value возвращает только верхний уровень
        assert node.target.get_component_at_level(1).value == '4'
        
        # 🔑 Альтернативные способы проверки составного адреса
        assert node.target.get_component_at_level(1).value == '4'
        assert node.target.get_component_at_level(2).value == '1'
        assert node.target.to_path() == '4.1'
    
    def test_handle_range_target(self, handler):
        """Целевой адрес — диапазон пунктов."""
        context = ParseContext(
            block='55. Пункты 153 — 155 изложить в следующей редакции: «...»'
        )
        
        node = handler.handle(context)
        
        assert node.target.is_range is True
        assert len(node.target.components) == 3
        assert [c.value for c in node.target.components] == ['153', '154', '155']

    def test_add_subpoint_parser_directly(self):
        """Прямой тест парсера AddSubpointParser."""
        from parsers.amendment_parsers import AddSubpointParser
        from nodes.target import TargetAddress, TargetComponent, ComponentType
        from nodes.amendments import AddSubpointAmendmentNode
        
        parser = AddSubpointParser()
        
        text = (
            'дополнить подпунктом «д» в следующей редакции: «\n'
            'д) сметные цены на эксплуатацию машин и механизмов.\n'
            '»'
        )
        
        assert parser.can_parse(text) is True
        
        target = TargetAddress(components=[
            TargetComponent(ComponentType.POINT, '8')
        ])
        
        node = parser.parse(text, target)
        
        assert isinstance(node, AddSubpointAmendmentNode)
        assert node.new_subpoint_number == 'д'
        assert len(node.new_content) == 1
        assert node.new_content[0].number == 'д'

    def test_replace_words_with_subpoint_parser(self):
        """Прямой тест ReplaceWordsAmendmentParser с подпунктом."""
        from parsers.amendment_parsers import ReplaceWordsAmendmentParser
        
        parser = ReplaceWordsAmendmentParser()
        text = 'в подпункте «г» слова «единичные расценки» заменить словами «единичные расценки;»'
        
        assert parser.can_parse(text) is True
        
        target = TargetAddress(components=[
            TargetComponent(ComponentType.POINT, '8', level=1)
        ])
        
        node = parser.parse(text, target)
        
        assert isinstance(node, ReplaceWordsAmendmentNode)
        assert node.old_text == 'единичные расценки'
        assert node.new_text == 'единичные расценки;'
        
        # 🔑 ИСПРАВЛЕНИЕ: проверяем через level, а не через type
        # В target теперь ДВА компонента POINT с разными level
        
        # Проверяем количество компонентов
        assert len(node.target.components) == 2
        
        # Проверяем через get_component_at_level()
        assert node.target.get_component_at_level(1).value == '8'   # пункт
        assert node.target.get_component_at_level(2).value == 'г'   # подпункт


    def test_extract_intro_text_with_subpoints(self, handler):
        """Извлечение вводной части из composite-амendment."""
        text = (
            'В пункте 10:\n'
            'а) в подпункте «а» ...\n'
            'б) подпункт «б» ...\n'
            'в) в подпункте «в» ...\n'
            'г) абзац пятый ...'
        )
        
        intro = handler._extract_intro_text(text)
        
        assert intro == 'В пункте 10:'
        assert 'подпункте' not in intro
        assert 'абзац' not in intro


    def test_extract_intro_text_without_subpoints(self, handler):
        """Извлечение вводной части из простого amendment."""
        text = 'В пункте 3 слова «старое» заменить словами «новое».'
        
        intro = handler._extract_intro_text(text)
        
        assert intro == text


    def test_extract_intro_text_with_nested_quotes(self, handler):
        """Вводная часть не обрезается на кавычках внутри подпунктов."""
        text = (
            'В пункте 8:\n'
            'а) дополнить подпунктом «д» в следующей редакции: «\n'
            'д) текст нового подпункта.\n'
            '»'
        )
        
        intro = handler._extract_intro_text(text)
        
        assert intro == 'В пункте 8:'
    
    def test_merge_targets_parent_point_child_subpoint(self, handler):
        """Объединение: родительский пункт + дочерний подпункт."""
        from nodes.target import TargetAddress, TargetComponent, ComponentType
        
        parent = TargetAddress(components=[
            TargetComponent(ComponentType.POINT, '10', level=1)
        ])
        child = TargetAddress(components=[
            TargetComponent(ComponentType.POINT, 'а', level=2)
        ])
        
        merged = handler._merge_targets(parent, child)
        
        assert len(merged.components) == 2
        assert merged.components[0].value == '10'
        assert merged.components[0].level == 1
        assert merged.components[1].value == 'а'
        assert merged.components[1].level == 2


    def test_merge_targets_parent_point_child_paragraph(self, handler):
        """Объединение: родительский пункт + дочерний абзац."""
        from nodes.target import TargetAddress, TargetComponent, ComponentType
        
        parent = TargetAddress(components=[
            TargetComponent(ComponentType.POINT, '10', level=1)
        ])
        child = TargetAddress(components=[
            TargetComponent(ComponentType.PARAGRAPH, '5')
        ])
        
        merged = handler._merge_targets(parent, child)
        
        assert len(merged.components) == 2
        assert merged.components[0].type == ComponentType.POINT
        assert merged.components[0].value == '10'
        assert merged.components[1].type == ComponentType.PARAGRAPH
        assert merged.components[1].value == '5'


    def test_merge_targets_no_duplicates(self, handler):
        """Объединение без дублей."""
        from nodes.target import TargetAddress, TargetComponent, ComponentType
        
        parent = TargetAddress(components=[
            TargetComponent(ComponentType.POINT, '10', level=1)
        ])
        child = TargetAddress(components=[
            TargetComponent(ComponentType.POINT, '10', level=1),
            TargetComponent(ComponentType.POINT, 'а', level=2)
        ])
        
        merged = handler._merge_targets(parent, child)
        
        # Не должно быть дублей
        assert len(merged.components) == 2


    def test_merge_targets_empty_child(self, handler):
        """Если дочерний target пустой — возвращаем родительский."""
        from nodes.target import TargetAddress, TargetComponent, ComponentType
        
        parent = TargetAddress(components=[
            TargetComponent(ComponentType.POINT, '10', level=1)
        ])
        child = TargetAddress.empty()
        
        merged = handler._merge_targets(parent, child)
        
        assert merged is parent
    
    # tests/test_handlers/test_amendment_handler.py

    def test_merge_child_point_level1_becomes_level2(self, handler):
        """
        Если child POINT level=1 не совпадает с parent POINT — 
        он становится подпунктом (level=2).
        """
        from nodes.target import TargetAddress, TargetComponent, ComponentType
        
        parent = TargetAddress(components=[
            TargetComponent(ComponentType.POINT, '10', level=1)
        ])
        # TargetParser создал POINT('а') с level=1, потому что не знает контекста
        child = TargetAddress(components=[
            TargetComponent(ComponentType.POINT, 'а', level=1)
        ])
        
        merged = handler._merge_targets(parent, child)
        
        assert len(merged.components) == 2
        assert merged.components[0].value == '10'
        assert merged.components[0].level == 1
        assert merged.components[1].value == 'а'
        assert merged.components[1].level == 2  # 🔑 Повышен до level=2


    def test_merge_matching_point_keeps_parent_level(self, handler):
        """Если child POINT совпадает с parent — level берётся из parent."""
        from nodes.target import TargetAddress, TargetComponent, ComponentType
        
        parent = TargetAddress(components=[
            TargetComponent(ComponentType.POINT, '10', level=1)
        ])
        child = TargetAddress(components=[
            TargetComponent(ComponentType.POINT, '10', level=1),
            TargetComponent(ComponentType.POINT, 'а', level=2)
        ])
        
        merged = handler._merge_targets(parent, child)
        
        assert len(merged.components) == 2
        assert merged.components[0].value == '10'
        assert merged.components[0].level == 1
        assert merged.components[1].value == 'а'
        assert merged.components[1].level == 2


    def test_merge_paragraph_with_parent_point(self, handler):
        """PARAGRAPH добавляется к parent POINT."""
        from nodes.target import TargetAddress, TargetComponent, ComponentType
        
        parent = TargetAddress(components=[
            TargetComponent(ComponentType.POINT, '10', level=1)
        ])
        child = TargetAddress(components=[
            TargetComponent(ComponentType.PARAGRAPH, '5')
        ])
        
        merged = handler._merge_targets(parent, child)
        
        assert len(merged.components) == 2
        assert merged.components[0].type == ComponentType.POINT
        assert merged.components[0].value == '10'
        assert merged.components[0].level == 1
        assert merged.components[1].type == ComponentType.PARAGRAPH
        assert merged.components[1].value == '5'


    def test_merge_deep_nesting(self, handler):
        """Глубокая вложенность: parent level=1, child level=2 → grandchild level=3."""
        from nodes.target import TargetAddress, TargetComponent, ComponentType
        
        parent = TargetAddress(components=[
            TargetComponent(ComponentType.POINT, '4', level=1),
            TargetComponent(ComponentType.POINT, '1', level=2),
        ])
        # Child содержит только "а" с level=1 (TargetParser не знает контекста)
        child = TargetAddress(components=[
            TargetComponent(ComponentType.POINT, 'а', level=1)
        ])
        
        merged = handler._merge_targets(parent, child)
        
        # Ожидаем: [POINT('4', 1), POINT('1', 2), POINT('а', 3)]
        assert len(merged.components) == 3
        assert merged.components[0].value == '4'
        assert merged.components[0].level == 1
        assert merged.components[1].value == '1'
        assert merged.components[1].level == 2
        assert merged.components[2].value == 'а'
        assert merged.components[2].level == 3  # 🔑 Повышен до level=3

    def test_parse_complex_composite_amendment_with_four_actions(self, handler):
        """
        Комплексное изменение с 4 типами действий.
        
        Проверяем:
        - Типы amendment-узлов
        - Содержимое amendments (old_text, new_text, anchor, new_content)
        - 🔑 Количество и состав компонентов в target для каждого amendment
        """
        context = ParseContext(
            block='7. В пункте 10:\n'
                'а) в подпункте «а» после слов «сметных цен строительных ресурсов» '
                'дополнить словами «в текущем уровне цен»;\n'
                'б) подпункт «б» изложить в следующей редакции:\n'
                '«\n'
                'б) базисно-индексным методом — с применением к сметной стоимости, определенной с использованием единичных расценок, в том числе их отдельных составляющих, сведения о которых включены в ФРСН, разработанных в базисном уровне цен, соответствующих индексов изменения сметной стоимости.\n'
                'До даты перехода на ресурсно-индексный метод определения сметной стоимости строительства в соответствии с требованиями постановления Правительства Российской Федерации от 23 декабря 2016 г. №1452 «О мониторинге цен строительных ресурсов» (Собрание законодательства Российской Федерации, 2017, № 1, ст. 184; 2022, № 16, ст. 2705) (далее — Постановление № 1452) в случае выполнения расчета базисно-индексным методом при отсутствии в ФЕР, ФЕРр, ФЕРм, ФЕРмр и ФЕРи единичных расценок на отдельные виды работ допускается калькулирование их стоимости с использованием сметных норм, сведения о которых включены в ФРСН, разработанных для применения ресурсно-индексным и ресурсным методами, с одновременным применением информации о сметных ценах на материальные ресурсы и оборудование, машины и механизмы в базисном уровне цен, включенных в ФССЦ и ФСЭМпо состоянию на 1 января 2000 г. в следующем порядке:\n'
                '- оплата труда рабочих и машинистов, пусконаладочного персонала в текущем уровне цен определяется на основании информации о сметных ценах на затраты труда рабочих и машинистов, размещенной в ФГИС ЦС, с учетом коэффициента инфляции на дату составления сметной документации, определяемого поквартально путем извлечения корня четвертой степени из величины годового показателя инфляции на соответствующий год, согласно данным прогноза социально-экономического развития Российской Федерации, опубликованным Министерством экономического развития Российской Федерации, по строке «Индекс потребительских цен в среднем загод» (базовый вариант) на текущий год;\n'
                '- при отсутствии в ФСЭМ сметных цен на эксплуатацию машин и механизмов их цены в базисном уровне цен по состоянию Ha 1 января 2000 г. определяются с использованием сметных цен на эксплуатацию машин и механизмов в уровне цен по состоянию на 1 января 2022 г. с приведением в текущий уровень цен индексом прогнозных  индексов-дефляторов и инфляции по строке «Продукция машиностроения (26, 27, 28, 29, 30, 33)», публикуемых Министерством экономического развития Российской Федерации в составе прогноза индексов дефляторов и индексов цен производителей по видам экономической деятельности (по полному кругу предприятий без НДС, косвенных — налогов, торгово-транспортной наценки);\n'
                '- при отсутствии в ФССЦ сметных цен материальных ресурсов и оборудования их цены в текущем уровне цен определяются в соответствии с пунктом 13 Методики;\n'
                '- приведение текущих цен на оплату труда рабочих и машинистов, эксплуатацию машин и механизмов, материальные ресурсы и оборудование в базисный уровень цен по состоянию на 1 января 2000 г. осуществляется обратным счетом путем деления их текущих цен на индекс изменения сметной стоимости в соответствии с пунктами 11 и 45 Методики;\n'
                '- приведенная цена эксплуатации машин и механизмов в базисном уровне цен по состоянию на 1 января 2000 г. определяется с добавлением стоимости оплаты труда машинистов, приведенной в базисный уровень цен по состоянию на 1 января 2000 г.;\n'
                '- учет в сметной документации стоимости отдельных видов затрат, определенной указанным способом, выполняется в соответствии с пунктом 38 Методики.\n'
                'Особенности определения сметной стоимости работ по сохранению объектов культурного наследия на этапе архитектурно-строительного проектирования приведены в разделе XII Методики. Положения раздела XII Методики применяются до включения в ФРСН сведений о соответствующих сметных нормативах на работы по сохранению объектов культурного наследия (памятников истории и культуры) народов Российской Федерации;\n'
                '»\n'
                'в) в подпункте «в» слова «к составляющим единичных расценок» заменить '
                'словами «к группам однородных строительных ресурсов»;\n'
                'г) абзац пятый признать утратившим силу.'
        )
        
        node = handler.handle(context)
        
        # ═══════════════════════════════════════════════════════
        # 🔍 Проверка родительского узла
        # ═══════════════════════════════════════════════════════
        assert isinstance(node, AmendmentNode)
        assert node.number == '7'
        assert node.action == 'composite'
        assert len(node.children) == 4
        
        # Родительский target — только пункт 10
        assert len(node.target.components) == 1
        assert node.target.get_component_at_level(1).value == '10'
        
        # ═══════════════════════════════════════════════════════
        # 🔍 а) add — target: пункт 10 + подпункт «а»
        # ═══════════════════════════════════════════════════════
        amendment_a = node.children[0].children[0]
        assert isinstance(amendment_a, AddAmendmentNode)
        assert amendment_a.anchor == 'сметных цен строительных ресурсов'
        assert amendment_a.new_text == 'в текущем уровне цен'
        
        # 🔑 Проверка target: 2 компонента (пункт + подпункт)
        assert len(amendment_a.target.components) == 2
        assert amendment_a.target.get_component_at_level(1).value == '10'
        assert amendment_a.target.get_component_at_level(2).value == 'а'
        assert amendment_a.target.to_path() == '10.а'
        
        # Проверяем типы компонентов
        assert amendment_a.target.components[0].type == ComponentType.POINT
        assert amendment_a.target.components[0].level == 1
        assert amendment_a.target.components[1].type == ComponentType.POINT
        assert amendment_a.target.components[1].level == 2
        
        # 
        # 🔍 б) replace — target: пункт 10 + подпункт «б»
        # ═══════════════════════════════════════════════════════
        amendment_b = node.children[1].children[0]
        assert isinstance(amendment_b, ReplaceAmendmentNode)
        assert len(amendment_b.new_content) >= 1
        assert amendment_b.new_content[0].number == 'б'
        
        # 🔑 Проверка target: 2 компонента (пункт + подпункт)
        assert len(amendment_b.target.components) == 2
        assert amendment_b.target.get_component_at_level(1).value == '10'
        assert amendment_b.target.get_component_at_level(2).value == 'б'
        assert amendment_b.target.to_path() == '10.б'
        
        # Проверяем типы компонентов
        assert amendment_b.target.components[0].type == ComponentType.POINT
        assert amendment_b.target.components[0].level == 1
        assert amendment_b.target.components[1].type == ComponentType.POINT
        assert amendment_b.target.components[1].level == 2
        
        # ═══════════════════════════════════════════════════════
        # 🔍 в) replace_words — target: пункт 10 + подпункт «в»
        # ═══════════════════════════════════════════════════════
        amendment_v = node.children[2].children[0]
        assert isinstance(amendment_v, ReplaceWordsAmendmentNode)
        assert amendment_v.old_text == 'к составляющим единичных расценок'
        assert amendment_v.new_text == 'к группам однородных строительных ресурсов'
        
        # 🔑 Проверка target: 2 компонента (пункт + подпункт)
        assert len(amendment_v.target.components) == 2
        assert amendment_v.target.get_component_at_level(1).value == '10'
        assert amendment_v.target.get_component_at_level(2).value == 'в'
        assert amendment_v.target.to_path() == '10.в'
        
        # Проверяем типы компонентов
        assert amendment_v.target.components[0].type == ComponentType.POINT
        assert amendment_v.target.components[0].level == 1
        assert amendment_v.target.components[1].type == ComponentType.POINT
        assert amendment_v.target.components[1].level == 2
        
        # ═══════════════════════════════════════════════════════
        # 🔍 г) repeal — target: пункт 10 + абзац 5
        # ═══════════════════════════════════════════════════════
        amendment_g = node.children[3].children[0]
        assert isinstance(amendment_g, RepealAmendmentNode)
        assert amendment_g.action == 'repeal'
        
        # 🔑 Проверка target: 2 компонента (пункт + абзац)
        assert len(amendment_g.target.components) == 2
        assert amendment_g.target.get_component_at_level(1).value == '10'
        assert amendment_g.target.paragraph_number == '5'
        assert amendment_g.target.to_path() == '10.para:5'
        
        # Проверяем типы компонентов
        assert amendment_g.target.components[0].type == ComponentType.POINT
        assert amendment_g.target.components[0].level == 1
        assert amendment_g.target.components[1].type == ComponentType.PARAGRAPH

    def test_repeal_paragraph_parser_directly(self):
        """Прямой тест RepealParagraphParser."""
        from parsers.amendment_parsers import RepealParagraphParser
        
        parser = RepealParagraphParser()
        text = 'абзац пятый признать утратившим силу'
        
        assert parser.can_parse(text) is True
        
        target = TargetAddress(components=[
            TargetComponent(ComponentType.POINT, '10')
        ])
        
        node = parser.parse(text, target)
        
        assert isinstance(node, RepealAmendmentNode)
        assert node.action == 'repeal'
        
        # 🔑 Целевой абзац в target.components
        target_values = {c.type: c.value for c in node.target.components}
        assert target_values[ComponentType.POINT] == '10'
        assert target_values[ComponentType.PARAGRAPH] == '5'


    def test_repeal_with_genitive_case(self):
        """Тест родительного падежа: 'абзаца пятого'."""
        from parsers.amendment_parsers import RepealParagraphParser
        from nodes.target import TargetAddress
        
        parser = RepealParagraphParser()
        
        # В родительном падеже
        text = 'из абзаца пятого пункта 10 исключить слова'
        # Этот паттерн не сработает, т.к. "признать утратившим силу" отсутствует
        assert parser.can_parse(text) is False


    def test_repeal_all_word_numbers(self):
        """Тест всех числительных для 'признать утратившим силу'."""
        from parsers.amendment_parsers import RepealParagraphParser
        from nodes.target import TargetAddress
        
        parser = RepealParagraphParser()
        
        test_cases = [
            ('первый', '1'),
            ('второй', '2'),
            ('третий', '3'),
            ('четвертый', '4'),
            ('пятый', '5'),
            ('шестой', '6'),
            ('седьмой', '7'),
            ('восьмой', '8'),
            ('девятый', '9'),
            ('десятый', '10'),
        ]
        
        for word, expected_number in test_cases:
            text = f'абзац {word} признать утратившим силу'
            
            assert parser.can_parse(text) is True, \
                f"Парсер не распознал текст: '{text}'"
            
            target = TargetAddress()
            node = parser.parse(text, target)
            
            assert node.target.paragraph_number == expected_number, \
                f"Для слова '{word}' ожидался номер '{expected_number}', получен '{node.target.paragraph_number}'"


    def test_parse_amendment_with_nested_quotes_in_text(self, handler):
            """Пункт 11: вложенные кавычки «сеть «Интернет»»."""
            context = ParseContext(
                block='11. В пункте 14:\n'
                    'а) в абзаце первом слова «сеть «Интернет»» заменить '
                    'словами «сеть «Интернет»)»;\n'
                    'б) подпункт «а» изложить в следующей редакции:\n'
                    '«\n'
                    'а) материальных ресурсов и оборудования: копиями или оригиналами '
                    '(при наличии) прейскурантов, коммерческих предложений, '
                    'технико-коммерческих предложений (далее — ТКП), '
                    'размещенной в информационно-телекоммуникационной сети «Интернет», '
                    'используемой при проведении конъюнктурного анализа;\n'
                    '»\n'
                    'в) в подпункте «б» после слов «в форме публичной оферты» '
                    'дополнить словами «, коммерческих предложений»;\n'
                    'г) в абзаце третьем слово «ближайших» исключить.'
            )
            
            node = handler.handle(context)
            
            assert isinstance(node, AmendmentNode)
            assert node.number == '11'
            assert node.action == 'composite'
            assert node.target.get_component_at_level(1).value == '14'
            assert len(node.children) == 4
            
            letters = [c.number for c in node.children]
            assert letters == ['а', 'б', 'в', 'г']
            
            # а) replace_words
            amendment_a = node.children[0].children[0]
            assert isinstance(amendment_a, ReplaceWordsAmendmentNode)
            assert 'сеть' in amendment_a.old_text
            assert 'Интернет' in amendment_a.old_text
            
            # б) replace
            amendment_b = node.children[1].children[0]
            assert isinstance(amendment_b, ReplaceAmendmentNode)
            assert len(amendment_b.new_content) >= 1
            
            full_text = ' '.join(p.text for p in amendment_b.new_content[0].children)
            assert 'Интернет' in full_text
            assert 'конъюнктурного анализа' in full_text
            
            # в) add
            amendment_v = node.children[2].children[0]
            assert isinstance(amendment_v, AddAmendmentNode)
            
            # г) exclude
            amendment_g = node.children[3].children[0]
            assert isinstance(amendment_g, ExcludeAmendmentNode)
            assert amendment_g.old_text == 'ближайших'


    def test_replace_amendment_with_markdown_list(self, handler):
        """
        ReplaceAmendmentNode с маркированным списком внутри кавычек.
        """
        context = ParseContext(
            block='1. Пункт 5 изложить в следующей редакции:\n'
                '«\n'
                '5. Текст пункта:\n'
                '- первый пункт списка;\n'
                '- второй пункт списка;\n'
                '- третий пункт списка.\n'
                '»'
        )
        
        node = handler.handle(context)
        
        assert isinstance(node, ReplaceAmendmentNode)
        assert node.target.get_component_at_level(1).value == '5'
        assert len(node.new_content) == 1
        
        new_point = node.new_content[0]
        assert new_point.number == '5'
        
        # Проверяем, что маркированный список сохранён в тексте
        full_text = ' '.join(p.text for p in new_point.children)
        assert 'первый пункт списка' in full_text
        assert 'второй пункт списка' in full_text
        assert 'третий пункт списка' in full_text
    
    def test_parse_amendment_with_nested_quotes_in_text(self, handler):
        """
        Пункт 11: вложенные кавычки «сеть «Интернет»» в тексте amendments.
        
        🔑 Кавычки «Интернет» — это название, а не цитата.
        Они не должны ломать парсинг.
        """
        context = ParseContext(
            block='11. В пункте 14:\n'
                'а) в абзаце первом слова «сеть «Интернет»» заменить '
                'словами «сеть «Интернет»)»;\n'
                'б) подпункт «а» изложить в следующей редакции:\n'
                '«\n'
                'а) материальных ресурсов и оборудования: копиями или оригиналами '
                '(при наличии) прейскурантов, коммерческих предложений, '
                'технико-коммерческих предложений (далее — ТКП), '
                'размещенной в информационно-телекоммуникационной сети «Интернет», '
                'используемой при проведении конъюнктурного анализа;\n'
                '»\n'
                'в) в подпункте «б» после слов «в форме публичной оферты» '
                'дополнить словами «, коммерческих предложений»;\n'
                'г) в абзаце третьем слово «ближайших» исключить.'
        )
        
        node = handler.handle(context)
        
        # Проверяем структуру
        assert isinstance(node, AmendmentNode)
        assert node.number == '11'
        assert node.action == 'composite'
        assert node.target.get_component_at_level(1).value == '14'
        
        # 🔑 Должно быть 4 подпункта (а, б, в, г)
        assert len(node.children) == 4, \
            f"Ожидалось 4 подпункта, получено {len(node.children)}: " \
            f"{[c.number for c in node.children]}"
        
        letters = [c.number for c in node.children]
        assert letters == ['а', 'б', 'в', 'г']
        
        # Проверяем каждый подпункт
        # а) replace_words
        amendment_a = node.children[0].children[0]
        assert isinstance(amendment_a, ReplaceWordsAmendmentNode)
        # 🔑 «Интернет» не должно ломать парсинг
        assert 'сеть' in amendment_a.old_text
        assert 'Интернет' in amendment_a.old_text
        
        # б) replace
        amendment_b = node.children[1].children[0]
        assert isinstance(amendment_b, ReplaceAmendmentNode)
        assert len(amendment_b.new_content) >= 1
        
        # 🔑 «Интернет» внутри цитаты не должно закрывать её
        full_text = ' '.join(p.text for p in amendment_b.new_content[0].children)
        assert 'Интернет' in full_text
        assert 'конъюнктурного анализа' in full_text
        
        # в) add
        amendment_v = node.children[2].children[0]
        assert isinstance(amendment_v, AddAmendmentNode)
        
        # г) exclude
        amendment_g = node.children[3].children[0]
        assert isinstance(amendment_g, ExcludeAmendmentNode)
        assert amendment_g.old_text == 'ближайших'
        
    
    def test_parser_priority_for_exclude(self):
        """
        Проверяем, что 'слово «X» исключить' обрабатывается
        именно ExcludeAmendmentParser, а не другими.
        """
        from parsers.amendment_parsers import (
            ExcludeAmendmentParser,
            ReplaceWordsAmendmentParser,
            AddAmendmentParser,
        )
        
        text = 'в абзаце третьем слово «ближайших» исключить'
        
        exclude_parser = ExcludeAmendmentParser()
        replace_words_parser = ReplaceWordsAmendmentParser()
        add_parser = AddAmendmentParser()
        
        # Только ExcludeAmendmentParser должен матчить
        assert exclude_parser.can_parse(text) is True
        assert replace_words_parser.can_parse(text) is False
        assert add_parser.can_parse(text) is False


    def test_parser_priority_for_replace_words(self):
        """
        Проверяем, что 'слова «X» заменить словами «Y»' обрабатывается
        ReplaceWordsAmendmentParser, а не ExcludeAmendmentParser.
        """
        from parsers.amendment_parsers import (
            ExcludeAmendmentParser,
            ReplaceWordsAmendmentParser,
        )
        
        text = 'слова «старые» заменить словами «новые»'
        
        exclude_parser = ExcludeAmendmentParser()
        replace_words_parser = ReplaceWordsAmendmentParser()
        
        # Только ReplaceWordsAmendmentParser должен матчить
        assert exclude_parser.can_parse(text) is False
        assert replace_words_parser.can_parse(text) is True

    def test_parse_amendment_11_composite_with_nested_quotes(self, handler):
        """
        Пункт 11: composite amendment с вложенными кавычками «сеть «Интернет»».
        
        Проверяет:
        - 4 подпункта разных типов (replace_words, replace, add, exclude)
        - Вложенные кавычки в тексте amendments
        - Единственное число "слово" в exclude
        """
        context = ParseContext(
            block='11. В пункте 14:\n'
                  'а) в абзаце первом слова «сеть «Интернет»» заменить '
                  'словами «сеть «Интернет»)»;\n'
                  'б) подпункт «а» изложить в следующей редакции:\n'
                  '«\n'
                  'а) материальных ресурсов и оборудования: копиями или оригиналами '
                  '(при наличии) прейскурантов, коммерческих предложений, '
                  'технико-коммерческих предложений (далее — ТКП), '
                  'размещенной в информационно-телекоммуникационной сети «Интернет», '
                  'используемой при проведении конъюнктурного анализа;\n'
                  '»\n'
                  'в) в подпункте «б» после слов «в форме публичной оферты» '
                  'дополнить словами «, коммерческих предложений»;\n'
                  'г) в абзаце третьем слово «ближайших» исключить.'
        )
        
        node = handler.handle(context)
        
        # ═══════════════════════════════════════════════════════
        # Проверка родительского узла
        # ═══════════════════════════════════════════════════════
        assert isinstance(node, AmendmentNode)
        assert node.number == '11'
        assert node.action == 'composite'
        assert node.target.get_component_at_level(1).value == '14'
        assert len(node.children) == 4
        
        letters = [c.number for c in node.children]
        assert letters == ['а', 'б', 'в', 'г']
        
        # ═══════════════════════════════════════════════════════
        # а) replace_words с вложенными кавычками
        # ═══════════════════════════════════════════════════════
        amendment_a = node.children[0].children[0]
        assert isinstance(amendment_a, ReplaceWordsAmendmentNode)
        assert 'сеть' in amendment_a.old_text
        assert 'Интернет' in amendment_a.old_text
        assert 'сеть' in amendment_a.new_text
        assert 'Интернет' in amendment_a.new_text
        
        # ═══════════════════════════════════════════════════════
        # б) replace с длинной цитатой
        # ═══════════════════════════════════════════════════════
        amendment_b = node.children[1].children[0]
        assert isinstance(amendment_b, ReplaceAmendmentNode)
        assert len(amendment_b.new_content) >= 1
        
        full_text = ' '.join(p.text for p in amendment_b.new_content[0].children)
        assert 'Интернет' in full_text
        assert 'конъюнктурного анализа' in full_text
        assert 'ТКП' in full_text
        
        # ═══════════════════════════════════════════════════════
        # в) add
        # ═══════════════════════════════════════════════════════
        amendment_v = node.children[2].children[0]
        assert isinstance(amendment_v, AddAmendmentNode)
        assert amendment_v.anchor == 'в форме публичной оферты'
        assert amendment_v.new_text == ', коммерческих предложений'
        
        # ═══════════════════════════════════════════════════════
        # г) exclude (единственное число "слово")
        # ═══════════════════════════════════════════════════════
        amendment_g = node.children[3].children[0]
        assert isinstance(amendment_g, ExcludeAmendmentNode)
        assert amendment_g.action == 'exclude'
        assert amendment_g.old_text == 'ближайших'
        
        # # 🔑 Проверяем, что target содержит абзац
        # assert amendment_g.target.paragraph_number == '3'
    
    # ═══════════════════════════════════════════════════════
    # 🔍 Пункт 12: range replace (НОВЫЙ КЕЙС)
    # ═══════════════════════════════════════════════════════
    def test_parse_amendment_12_range_replace(self, handler):
        """
        Пункт 12: "Пункты 15 и 16 изложить в следующей редакции".
        
        🔑 КЛЮЧЕВОЙ КЕЙС: один amendment, но target указывает на ДВА пункта.
        
        Ожидаемая структура:
        ReplaceAmendmentNode
        ├── target: [POINT('15', 1), POINT('16', 1)]  ← is_range = True
        └── new_content:
            ├── PointNode (15)
            │   └── ParagraphNode (1)
            └── PointNode (16)
                └── ParagraphNode (1)
        """
        context = ParseContext(
            block='12. Пункты 15 и 16 изложить в следующей редакции:\n'
                  '«\n'
                  '15. В документах, обосновывающих стоимость в текущем уровне цен '
                  'соответствующих материальных ресурсов, оборудования и отдельных '
                  'видов работ и услуг, предоставляемых производителями (поставщиками) '
                  'или формируемых на основании данных из открытых и (или) официальных '
                  'источников, указанных в пункте 14 Методики, должна содержаться '
                  'следующая информация: наименование производителя (поставщика), его '
                  'идентификационный номер налогоплательщика (далее — ИНН), контактные '
                  'данные, сайт в информационно-телекоммуникационной сети «Интернет» '
                  '(при наличии).\n'
                  '16. Данные, указанные в пункте 15 Методики, отсутствующие в '
                  'документах, обосновывающих стоимость в текущем уровне цен '
                  'соответствующих материальных ресурсов, оборудования, отдельных '
                  'видов работ и услуг, могут быть дополнены и подписаны '
                  'уполномоченным лицом заказчика при оформлении обоснований '
                  'результатов конъюнктурного анализа.\n'
                  '»'
        )
        
        node = handler.handle(context)
        
        # ═══════════════════════════════════════════════════════
        # 🔑 Это НЕ composite, а replace с range target
        # ═══════════════════════════════════════════════════════
        assert isinstance(node, ReplaceAmendmentNode)
        assert node.number == '12'
        assert node.action == 'replace'
        
        # ═══════════════════════════════════════════════════════
        # 🔑 Target содержит ДВА пункта
        # ═══════════════════════════════════════════════════════
        assert len(node.target.components) == 2
        
        # Оба компонента — POINT с level=1
        assert node.target.components[0].type == ComponentType.POINT
        assert node.target.components[0].value == '15'
        assert node.target.components[0].level == 1
        
        assert node.target.components[1].type == ComponentType.POINT
        assert node.target.components[1].value == '16'
        assert node.target.components[1].level == 1
        
        # 🔑 is_range = True (все компоненты — POINT level=1)
        assert node.target.is_range is True
        
        # 🔑 full_point_path = '15.16'
        assert node.target.full_point_path == '15.16'
        
        # ═══════════════════════════════════════════════════════
        # 🔑 new_content содержит ДВА пункта
        # ═══════════════════════════════════════════════════════
        assert len(node.new_content) == 2
        
        # Пункт 15
        point_15 = node.new_content[0]
        assert point_15.number == '15'
        assert len(point_15.children) >= 1
        text_15 = ' '.join(p.text for p in point_15.children)
        assert 'В документах, обосновывающих стоимость' in text_15
        assert 'наименование производителя' in text_15
        assert 'ИНН' in text_15
        # 🔑 Название «Интернет» не должно ломать структуру
        assert 'Интернет' in text_15
        
        # Пункт 16
        point_16 = node.new_content[1]
        assert point_16.number == '16'
        assert len(point_16.children) >= 1
        text_16 = ' '.join(p.text for p in point_16.children)
        assert 'Данные, указанные в пункте 15' in text_16
        assert 'конъюнктурного анализа' in text_16

    def test_parse_amendment_60_composite_without_subpoints(self, handler):
        """
        Пункт 60: composite из двух действий БЕЗ подпунктов.
        
        Действия:
        1. MultipleReplaceWords — две замены слов
        2. AddParagraph — дополнение абзацем
        """
        context = ParseContext(
            block='60. В пункте 167:\n'
                'слова «(графы 4, 5, 6)» заменить словами «(графы 4, 5, 6 и 7)», '
                'слова «(графы 7, 8)» заменить словами «(графы 7 и 8)»;\n'
                'дополнить абзацем следующего содержания:\n'
                '«\n'
                'В главе 9 сводного сметного расчета дополнительно к затратам '
                'на осуществление функций строительного контроля, определяемым '
                'в соответствии с пунктом 166 Методики, могут учитываться затраты, '
                'связанные с проведением дополнительного строительного контроля '
                'заказчика инструментальными и лабораторными методами в объемах, '
                'предусмотренных действующими документами в области стандартизации '
                'и технического регулирования соответствующих работ, а также '
                'нормативными правовыми актами Российской Федерации, в случае '
                'если такое решение принято заказчиком.\n'
                '»'
        )
        
        node = handler.handle(context)
        
        # Это composite amendment
        assert isinstance(node, AmendmentNode)
        assert node.number == '60'
        assert node.action == 'composite'
        
        # Target — только пункт 167
        assert node.target.get_component_at_level(1).value == '167'
        assert node.target.paragraph_number is None
        
        # 🔑 Должно быть 2 действия (ПРЯМЫЕ дети, без PointNode)
        assert len(node.children) == 2
        
        # 🔑 Действие 1: MultipleReplaceWords (ПРЯМОЙ ребёнок)
        from nodes.amendments import MultipleReplaceWordsAmendmentNode
        action_1 = node.children[0]  # ← НЕ .children[0]
        assert isinstance(action_1, MultipleReplaceWordsAmendmentNode), \
            f"Ожидался MultipleReplaceWordsAmendmentNode, получен {type(action_1).__name__}"
        
        # Действие 2: AddParagraph (ПРЯМОЙ ребёнок)
        from nodes.amendments import AddParagraphAmendmentNode
        action_2 = node.children[1]  # ← НЕ .children[1]
        assert isinstance(action_2, AddParagraphAmendmentNode), \
            f"Ожидался AddParagraphAmendmentNode, получен {type(action_2).__name__}"
        
        # Проверяем содержимое MultipleReplaceWords
        assert len(action_1.replacements) == 2
        assert action_1.replacements[0].old_text == '(графы 4, 5, 6)'
        assert action_1.replacements[0].new_text == '(графы 4, 5, 6 и 7)'
        assert action_1.replacements[1].old_text == '(графы 7, 8)'
        assert action_1.replacements[1].new_text == '(графы 7 и 8)'
        
        # Проверяем содержимое AddParagraph
        assert len(action_2.new_content) >= 1
        assert 'В главе 9 сводного сметного расчета' in action_2.new_content[0].text

    
    def test_amendment_handler_multiple_replace(self, handler):
        """AmendmentHandler корректно обрабатывает множественные замены."""
        context = ParseContext(
            block='50. В абзаце втором пункта 50:\n'
                'слова «(графы 4, 5, 6)» заменить словами «(графы 4, 5, 6 и 7)», '
                'слова «(графы 7, 8)» заменить словами «(графы 7 и 8)».'
        )
        
        node = handler.handle(context)
        
        # 🔑 Теперь это MultipleReplaceWordsAmendmentNode напрямую
        from nodes.amendments import MultipleReplaceWordsAmendmentNode
        assert isinstance(node, MultipleReplaceWordsAmendmentNode)
        assert node.number == '50'
        assert len(node.replacements) == 2
        assert node.replacements[0].old_text == '(графы 4, 5, 6)'
        assert node.replacements[0].new_text == '(графы 4, 5, 6 и 7)'
        assert node.replacements[1].old_text == '(графы 7, 8)'
        assert node.replacements[1].new_text == '(графы 7 и 8)'


    def test_amendment_handler_mixed_actions_creates_composite(self, handler):
        """Разнородные действия → composite с несколькими детьми."""
        context = ParseContext(
            block='60. В пункте 167:\n'
                'слова «(графы 4, 5, 6)» заменить словами «(графы 4, 5, 6 и 7)», '
                'слова «(графы 7, 8)» заменить словами «(графы 7 и 8)»;\n'
                'дополнить абзацем следующего содержания:\n'
                '«\n'
                'В главе 9 сводного сметного расчета...\n'
                '»'
        )
        
        node = handler.handle(context)
        
        from nodes.amendments import AmendmentNode
        assert isinstance(node, AmendmentNode)
        assert node.action == 'composite'
        assert len(node.children) == 2
        
        # Первое действие — множественная замена
        from nodes.amendments import MultipleReplaceWordsAmendmentNode
        action_1 = node.children[0].children[0]
        assert isinstance(action_1, MultipleReplaceWordsAmendmentNode)
        assert len(action_1.replacements) == 2
        
        # Второе действие — дополнение абзацем
        from nodes.amendments import AddParagraphAmendmentNode
        action_2 = node.children[1].children[0]
        assert isinstance(action_2, AddParagraphAmendmentNode)


    def test_amendment_handler_single_replace_stays_single(self, handler):
        """Одиночная замена остаётся ReplaceWordsAmendmentNode."""
        context = ParseContext(
            block='50. В пункте 50:\n'
                'слова «старое» заменить словами «новое».'
        )
        
        node = handler.handle(context)
        
        from nodes.amendments import ReplaceWordsAmendmentNode
        assert isinstance(node, ReplaceWordsAmendmentNode)
        assert node.old_text == 'старое'
        assert node.new_text == 'новое'

    # tests/test_handlers/test_amendment_handler.py

    def test_split_into_actions_mixed(self, handler):
        """Разбиение разнородных действий."""
        text = (
            'слова «(графы 4, 5, 6)» заменить словами «(графы 4, 5, 6 и 7)», '
            'слова «(графы 7, 8)» заменить словами «(графы 7 и 8)»;\n'
            'дополнить абзацем следующего содержания:\n'
            '«В главе 9...»'
        )
        
        actions = handler._split_into_actions(text)
        
        # 🔑 Должно быть РОВНО 2 действия
        assert len(actions) == 2, \
            f"Ожидалось 2 действия, получено {len(actions)}: {actions}"
        
        assert 'слова «(графы 4, 5, 6)» заменить' in actions[0]
        assert 'слова «(графы 7, 8)» заменить' in actions[0]
        assert 'дополнить абзацем' in actions[1]


    def test_split_into_actions_multiple_replaces(self, handler):
        """Несколько замен слов через запятую — одно действие."""
        text = (
            'слова «A» заменить словами «B», '
            'слова «C» заменить словами «D», '
            'слова «E» заменить словами «F»'
        )
        
        actions = handler._split_into_actions(text)
        
        # 🔑 Все замены — одно действие (разделены запятыми, не `;`)
        assert len(actions) == 1
        assert 'A' in actions[0]
        assert 'C' in actions[0]
        assert 'E' in actions[0]


    def test_split_into_actions_no_extra_split_on_semicolon_newline(self, handler):
        """`;` + `\n` не дают двойное разбиение."""
        text = (
            'слова «A» заменить словами «B»;\n'
            'дополнить абзацем следующего содержания:\n'
            '«Текст»'
        )
        
        actions = handler._split_into_actions(text)
        
        # 🔑 Должно быть 2 действия, а не 3
        assert len(actions) == 2, \
            f"Ожидалось 2 действия, получено {len(actions)}: {actions}"
        
        assert 'A' in actions[0]
        assert 'дополнить абзацем' in actions[1]
    
    def test_split_into_actions_ignores_semicolons_inside_quotes(self, handler):
        """`;` внутри кавычек не разделяют действия."""
        text = (
            'Пункт 5 изложить в следующей редакции:\n'
            '«\n'
            '5. Текст пункта:\n'
            '- первый пункт списка;\n'
            '- второй пункт списка;\n'
            '- третий пункт списка.\n'
            '»'
        )
        
        actions = handler._split_into_actions(text)
        
        # 🔑 Должно быть 1 действие (все `;` внутри кавычек)
        assert len(actions) == 1, \
            f"Ожидалось 1 действие, получено {len(actions)}: {actions}"
        assert 'изложить в следующей редакции' in actions[0]
        assert 'первый пункт списка' in actions[0]


    def test_split_into_actions_respects_semicolons_outside_quotes(self, handler):
        """`;` вне кавычек разделяют действия."""
        text = (
            'слова «A» заменить словами «B»; '
            'слова «C» заменить словами «D»'
        )
        
        actions = handler._split_into_actions(text)
        
        # 🔑 `;` вне кавычек → 2 действия
        assert len(actions) == 2
        assert 'A' in actions[0]
        assert 'C' in actions[1]


    def test_replace_amendment_with_markdown_list(self, handler):
        """ReplaceAmendmentNode с маркированным списком внутри кавычек."""
        context = ParseContext(
            block='1. Пункт 5 изложить в следующей редакции:\n'
                '«\n'
                '5. Текст пункта:\n'
                '- первый пункт списка;\n'
                '- второй пункт списка;\n'
                '- третий пункт списка.\n'
                '»'
        )
        
        node = handler.handle(context)
        
        from nodes.amendments import ReplaceAmendmentNode
        assert isinstance(node, ReplaceAmendmentNode)
        assert node.number == '1'
        assert node.action == 'replace'
        
        # Проверяем содержимое
        assert len(node.new_content) == 1
        point = node.new_content[0]
        assert point.number == '5'
        
        # Проверяем, что маркированный список сохранён
        full_text = ' '.join(p.text for p in point.children)
        assert 'Текст пункта' in full_text
        assert 'первый пункт списка' in full_text
        assert 'второй пункт списка' in full_text
        assert 'третий пункт списка' in full_text


    def test_amendment_handler_mixed_actions_creates_composite(self, handler):
        """Разнородные действия → composite с несколькими детьми."""
        context = ParseContext(
            block='60. В пункте 167:\n'
                'слова «(графы 4, 5, 6)» заменить словами «(графы 4, 5, 6 и 7)», '
                'слова «(графы 7, 8)» заменить словами «(графы 7 и 8)»;\n'
                'дополнить абзацем следующего содержания:\n'
                '«\n'
                'В главе 9 сводного сметного расчета...\n'
                '»'
        )
        
        node = handler.handle(context)
        
        from nodes.amendments import AmendmentNode
        assert isinstance(node, AmendmentNode)
        assert node.action == 'composite'
        assert len(node.children) == 2
        
        # 🔑 Первое действие — множественная замена (ПРЯМОЙ ребёнок, без PointNode)
        from nodes.amendments import MultipleReplaceWordsAmendmentNode
        action_1 = node.children[0]
        assert isinstance(action_1, MultipleReplaceWordsAmendmentNode), \
            f"Ожидался MultipleReplaceWordsAmendmentNode, получен {type(action_1).__name__}"
        
        # Второе действие — добавление абзаца (ПРЯМОЙ ребёнок, без PointNode)
        from nodes.amendments import AddParagraphAmendmentNode
        action_2 = node.children[1]
        assert isinstance(action_2, AddParagraphAmendmentNode), \
            f"Ожидался AddParagraphAmendmentNode, получен {type(action_2).__name__}"
