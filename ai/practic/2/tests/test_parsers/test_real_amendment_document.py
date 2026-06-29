# tests/test_parsers/test_real_amendment_document.py
import pytest, re
from parsers.amendment_document_parser import AmendmentDocumentParser
from nodes.amendments import (
    AmendmentNode, ReplaceAmendmentNode, ReplaceWordsAmendmentNode,
    AddAmendmentNode, ExcludeAmendmentNode
)
from nodes.target import ComponentType


class TestRealAmendmentDocument:
    """
    Интеграционные тесты на реальном фрагменте документа.
    
    Содержит три пункта с разными типами amendments и опечатками:
    - Пункт 11: composite с 4 подпунктами разных типов + опечатки
    - Пункт 12: range replace (пункты 15 и 16)
    - Пункт 62: add с опечаткой (лишняя «)
    """
    
    @pytest.fixture
    def parser(self):
        return AmendmentDocumentParser()
    
    @pytest.fixture
    def real_document_text(self):
        """Реальный фрагмент документа с тремя пунктами amendments."""
        return (
            '11. В пункте 14:\n'
            'а) в абзаце первом слова «сеть «Интернет» заменить словами «сеть «Интернет»)»;\n'
            'б) подпункт «а» изложить в следующей редакции:\n'
            '«\n'
            'а) материальных ресурсов и оборудования: копиями или оригиналами (при наличии) '
            'прейскурантов, коммерческих предложений, технико-коммерческих предложений '
            '(далее — ТКП), расчетно-калькуляционных цен (далее — РКЦ), цен офсетных '
            'контрактов, а также информацией, принятой по данным, размещенной в '
            'информационно-телекоммуникационной сети «Интернет», используемой при '
            'проведении конъюнктурного анализа;\n'
            '»\n'
            'в) в подпункте «б»: - после слов «в форме публичной оферты» дополнить '
            'словами «, коммерческих предложений»;\n'
            'г) в абзаце третьем слово «ближайших» исключить.\n'
            '12. Пункты 15 и 16 изложить в следующей редакции:\n'
            '«\n'
            '15. В документах, обосновывающих стоимость в текущем уровне цен '
            'соответствующих материальных ресурсов, оборудования и отдельных видов '
            'работ и услуг, предоставляемых производителями (поставщиками) или '
            'формируемых на основании данных из открытых и (или) официальных '
            'источников, указанных в пункте 14 Методики, должна содержаться следующая '
            'информация: наименование производителя (поставщика), его идентификационный '
            'номер налогоплательщика (далее — ИНН), контактные данные, сайт в '
            'информационно-телекоммуникационной сети «Интернет» (при наличии), об '
            'исполнителе (исполнителях) (при наличии) такого обосновывающего документа '
            'с указанием фамилий и инициалов либо иных реквизитов, необходимых для '
            'идентификации этих лиц, а также о дате составления документа, дате и (или) '
            'сроках действия ценовых предложений, об учете (или не учете) в ценах '
            'отдельных затрат (в частности, на перевозку, шефмонтаж, шефналадку) и '
            'налога на добавленную стоимость (далее — НДС).\n'
            '16. Данные, указанные в пункте 15 Методики, отсутствующие в документах, '
            'обосновывающих стоимость в текущем уровне цен соответствующих материальных '
            'ресурсов, оборудования, отдельных видов работ и услуг, могут быть дополнены '
            'и подписаны уполномоченным лицом заказчика при оформлении обоснований '
            'результатов конъюнктурного анализа.\n'
            '»\n'
            '62. Пункт 176 после слов «некоторые акты Правительства Российской '
            'Федерации» (Собрание законодательства Российской Федерации, 2017, № 21, '
            'ст. 3015; 2020, № 2, ст. 190)» дополнить словами «, на проведение '
            'государственной историко-культурной экспертизы — в соответствии с '
            'Положением о государственной историко-культурной экспертизе, утвержденным '
            'постановлением Правительства Российской Федерации от 15 июля 2009 г. №569 '
            '(Собрание законодательства Российской Федерации, 2009, № 30, ст. 3812; '
            '2021, № 39, ст. 6710)».'
        )
    
    # ═══════════════════════════════════════════════════════
    # 🔍 Основной интеграционный тест
    # ═══════════════════════════════════════════════════════
    def test_parse_real_document_three_amendments(self, parser, real_document_text):
        """
        Парсинг трёх пунктов amendments (11, 12, 62) с разными типами
        действий и опечатками в исходном тексте.
        
        🔑 КЛЮЧЕВОЙ ТЕСТ: проверяет, что парсер корректно разделяет
        пункты, несмотря на опечатки с кавычками.
        """
        nodes = parser.parse(real_document_text)
        
        # ═══════════════════════════════════════════════════════
        # 🔍 Должно быть ровно 3 узла
        # ═══════════════════════════════════════════════════════
        assert len(nodes) == 3, (
            f"Ожидалось 3 узла, получено {len(nodes)}: "
            f"{[(type(n).__name__, getattr(n, 'number', 'N/A'), getattr(n, 'action', 'N/A')) for n in nodes]}"
        )
        
        # ═══════════════════════════════════════════════════════
        # 🔍 Пункт 11 — composite amendment
        # ═══════════════════════════════════════════════════════
        node_11 = nodes[0]
        assert isinstance(node_11, AmendmentNode), \
            f"Пункт 11 должен быть AmendmentNode, получен {type(node_11).__name__}"
        assert node_11.number == '11'
        assert node_11.action == 'composite'
        
        # Target: пункт 14
        assert node_11.target.get_component_at_level(1).value == '14'
        
        # 4 подпункта (а, б, в, г)
        assert len(node_11.children) == 4, \
            f"В пункте 11 ожидалось 4 подпункта, получено {len(node_11.children)}"
        
        letters = [c.number for c in node_11.children]
        assert letters == ['а', 'б', 'в', 'г']
        
        # ═══════════════════════════════════════════════════════
        # 🔍 Пункт 12 — range replace
        # ═══════════════════════════════════════════════════════
        node_12 = nodes[1]
        assert isinstance(node_12, ReplaceAmendmentNode), \
            f"Пункт 12 должен быть ReplaceAmendmentNode, получен {type(node_12).__name__}"
        assert node_12.number == '12'
        assert node_12.action == 'replace'
        
        # 🔑 Target содержит ДВА пункта (15 и 16)
        assert len(node_12.target.components) == 2
        assert node_12.target.components[0].value == '15'
        assert node_12.target.components[0].level == 1
        assert node_12.target.components[1].value == '16'
        assert node_12.target.components[1].level == 1
        assert node_12.target.is_range is True
        
        # 🔑 new_content содержит ДВА пункта
        assert len(node_12.new_content) == 2
        assert node_12.new_content[0].number == '15'
        assert node_12.new_content[1].number == '16'
        
        # Проверяем содержимое пунктов
        text_15 = ' '.join(p.text for p in node_12.new_content[0].children)
        assert 'В документах, обосновывающих стоимость' in text_15
        assert 'наименование производителя' in text_15
        assert 'ИНН' in text_15
        assert 'НДС' in text_15
        
        text_16 = ' '.join(p.text for p in node_12.new_content[1].children)
        assert 'Данные, указанные в пункте 15' in text_16
        assert 'конъюнктурного анализа' in text_16
        
        # ═══════════════════════════════════════════════════════
        # 🔍 Пункт 62 — add amendment
        # ═══════════════════════════════════════════════════════
        node_62 = nodes[2]
        assert isinstance(node_62, AddAmendmentNode), \
            f"Пункт 62 должен быть AddAmendmentNode, получен {type(node_62).__name__}"
        assert node_62.number == '62'
        assert node_62.action == 'add'
        
        # Target: пункт 176
        assert node_62.target.get_component_at_level(1).value == '176'
        
        # Якорь и новый текст
        assert 'некоторые акты Правительства Российской Федерации' in node_62.anchor
        assert 'государственной историко-культурной экспертизы' in node_62.new_text
        assert 'Положением о государственной историко-культурной экспертизе' in node_62.new_text
        assert '№569' in node_62.new_text
    
    # ═══════════════════════════════════════════════════════
    # 🔍 Детальные тесты для каждого пункта
    # ═══════════════════════════════════════════════════════
    def test_parse_amendment_11_subpoints(self, parser, real_document_text):
        """Детальная проверка подпунктов пункта 11."""
        nodes = parser.parse(real_document_text)
        node_11 = nodes[0]
        
        # а) replace_words (с опечаткой в кавычках)
        amendment_a = node_11.children[0].children[0]
        assert isinstance(amendment_a, ReplaceWordsAmendmentNode)
        assert 'сеть' in amendment_a.old_text
        assert 'Интернет' in amendment_a.old_text
        
        # б) replace (длинная цитата)
        amendment_b = node_11.children[1].children[0]
        assert isinstance(amendment_b, ReplaceAmendmentNode)
        assert len(amendment_b.new_content) >= 1
        text_b = ' '.join(p.text for p in amendment_b.new_content[0].children)
        assert 'материальных ресурсов и оборудования' in text_b
        assert 'конъюнктурного анализа' in text_b
        
        # в) add (с лишним `-` в тексте)
        amendment_v = node_11.children[2].children[0]
        assert isinstance(amendment_v, AddAmendmentNode)
        assert amendment_v.anchor == 'в форме публичной оферты'
        assert amendment_v.new_text == ', коммерческих предложений'
        
        # г) exclude (единственное число "слово")
        amendment_g = node_11.children[3].children[0]
        assert isinstance(amendment_g, ExcludeAmendmentNode)
        assert amendment_g.old_text == 'ближайших'
    
    def test_parse_amendment_12_range_target(self, parser, real_document_text):
        """Детальная проверка range target пункта 12."""
        nodes = parser.parse(real_document_text)
        node_12 = nodes[1]
        
        # Проверяем структуру target
        assert node_12.target.is_range is True
        assert node_12.target.full_point_path == '15.16'
        
        # Проверяем, что оба пункта есть в new_content
        point_numbers = [p.number for p in node_12.new_content]
        assert '15' in point_numbers
        assert '16' in point_numbers
    
    def test_parse_amendment_62_with_typo(self, parser, real_document_text):
        """
        Пункт 62 с опечаткой (лишняя « перед "дополнить").
        
        Проверяет, что парсер корректно обрабатывает опечатку
        и всё равно распознаёт add amendment.
        """
        nodes = parser.parse(real_document_text)
        node_62 = nodes[2]
        
        assert isinstance(node_62, AddAmendmentNode)
        assert node_62.number == '62'
        
        # Якорь должен содержать текст до опечатки
        assert 'некоторые акты Правительства' in node_62.anchor
        
        # Новый текст должен содержать добавляемую часть
        assert 'на проведение государственной историко-культурной экспертизы' in node_62.new_text