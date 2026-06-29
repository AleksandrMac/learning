# tests/test_utils/test_quote_analyzer.py
import pytest
from utils.quote_analyzer import QuoteAnalyzer, quote_analyzer


class TestQuoteAnalyzer:
    
    @pytest.fixture
    def analyzer(self):
        return QuoteAnalyzer()
    
    def test_analyze_short_designation(self, analyzer):
        """Короткая кавычка-обозначение — не цитата."""
        text = "подпункт «а» изложить"
        info = analyzer.analyze(text, text.index('«'))
        
        assert info['is_citation'] is False
        assert info['content'] == 'а'
    
    def test_analyze_name(self, analyzer):
        """Кавычка-название (однострочная, короткая) — не цитата."""
        text = "в сети «Интернет» размещена"
        info = analyzer.analyze(text, text.index('«'))
        
        assert info['is_citation'] is False
        assert info['content'] == 'Интернет'
    
    def test_analyze_multiline_citation(self, analyzer):
        """Многострочная кавычка — цитата."""
        text = "изложить в следующей редакции:\n«\nа) текст\nб) текст\n»"
        info = analyzer.analyze(text, text.index('«'))
        
        assert info['is_citation'] is True
        assert 'а) текст' in info['content']
    
    def test_analyze_long_citation(self, analyzer):
        """Длинная кавычка (>50 символов) — цитата."""
        text = "текст «это очень длинная цитата, которая содержит более пятидесяти символов для проверки»"
        info = analyzer.analyze(text, text.index('«'))
        
        assert info['is_citation'] is True
    
    def test_analyze_nested_with_long_content(self, analyzer):
        """Вложенные кавычки с длинным содержимым — цитата."""
        text = "изложить: «текст с «вложенной» кавычкой и длинным содержимым, которое превышает пятьдесят символов для проверки»"
        info = analyzer.analyze(text, text.index('«'))
        
        assert info['is_citation'] is True
        assert info['has_nested'] is True
    
    def test_is_inside_citation_long(self, analyzer):
        """Позиция внутри длинной цитаты."""
        text = (
            'а) текст до цитаты '
            '«б) это длинная цитата, которая содержит более пятидесяти символов '
            'и поэтому считается цитатой, а не названием или обозначением» '
            'в) после цитаты'
        )
        
        assert analyzer.is_inside_citation(text, text.index('а)')) is False
        assert analyzer.is_inside_citation(text, text.index('б)')) is True
        assert analyzer.is_inside_citation(text, text.index('в)')) is False
    
    def test_is_inside_citation_short_not_citation(self, analyzer):
        """Короткая однострочная кавычка — НЕ цитата."""
        text = 'а) текст «б) короткая» в) после'
        
        assert analyzer.is_inside_citation(text, text.index('а)')) is False
        assert analyzer.is_inside_citation(text, text.index('б)')) is False
        assert analyzer.is_inside_citation(text, text.index('в)')) is False
    
    def test_is_inside_citation_multiline(self, analyzer):
        """Многострочная кавычка — цитата."""
        text = (
            'а) текст до\n'
            '«\n'
            'б) первая строка цитаты\n'
            'в) вторая строка цитаты\n'
            '»\n'
            'г) после цитаты'
        )
        
        assert analyzer.is_inside_citation(text, text.index('а)')) is False
        assert analyzer.is_inside_citation(text, text.index('б)')) is True
        assert analyzer.is_inside_citation(text, text.index('в)')) is True
        assert analyzer.is_inside_citation(text, text.index('г)')) is False
    
    def test_extract_text_outside_quotes_simple(self, analyzer):
        """Простые кавычки."""
        # 🔑 Используем ДЛИННУЮ цитату (> 50 символов), которая точно считается цитатой
        text = "в пункте 10 «это длинная цитата, которая содержит более пятидесяти символов для проверки» и пункт 5"
        result = analyzer.extract_text_outside_quotes(text)
        assert result == "в пункте 10  и пункт 5"


    def test_extract_text_outside_quotes_short_name_preserved(self, analyzer):
        """Короткие кавычки (названия/обозначения) сохраняются."""
        # 🔑 Короткая кавычка "цитата" (7 символов) — это название, сохраняется
        text = "в пункте 10 «цитата» и пункт 5"
        result = analyzer.extract_text_outside_quotes(text)
        # 🔑 Кавычка сохранена, потому что она короткая и однострочная
        assert result == "в пункте 10 «цитата» и пункт 5"


    def test_extract_text_outside_quotes_internet_preserved(self, analyzer):
        """Название «Интернет» сохраняется."""
        text = "в сети «Интернет» размещена информация"
        result = analyzer.extract_text_outside_quotes(text)
        assert result == "в сети «Интернет» размещена информация"
    
    def test_extract_short_quotes_preserved(self, analyzer):
        """Короткие кавычки-обозначения сохраняются."""
        text = "подпункт «б» изложить"
        result = analyzer.extract_text_outside_quotes(text)
        assert result == "подпункт «б» изложить"
    
    def test_extract_name_preserved(self, analyzer):
        """Кавычки-названия сохраняются."""
        text = "в сети «Интернет» размещена"
        result = analyzer.extract_text_outside_quotes(text)
        assert result == "в сети «Интернет» размещена"
    
    def test_extract_mixed_quotes(self, analyzer):
        """Смешанные короткие и длинные кавычки."""
        text = "подпункт «а» изложить в редакции «длинная цитата, которая содержит более пятидесяти символов для проверки»"
        result = analyzer.extract_text_outside_quotes(text)
        assert result == "подпункт «а» изложить в редакции "

        
    def test_analyze_unbalanced_quotes(self, analyzer):
        """
        Несбалансированные кавычки (опечатка) не считаются цитатой.
        
        Текст: "слова «сеть «Интернет» заменить"
        Кавычки: 2 открывающих, 1 закрывающая → баланс ≠ 0
        """
        text = 'слова «сеть «Интернет» заменить словами «сеть «Интернет»)»'
        
        # Первая « перед "сеть"
        first_quote_pos = text.index('«')
        info = analyzer.analyze(text, first_quote_pos)
        
        # 🔑 Кавычка несбалансирована
        assert info['is_unbalanced'] is True
        assert info['is_citation'] is False


    def test_is_inside_citation_with_unbalanced(self, analyzer):
        """Несбалансированные кавычки не влияют на is_inside_citation."""
        text = (
            'а) слова «сеть «Интернет» заменить словами «сеть «Интернет»)»;\n'
            'б) подпункт «а» изложить в следующей редакции:\n'
            '«\n'
            'в) текст внутри цитаты\n'
            '»'
        )
        
        # Позиция "а)" — до любых кавычек
        pos_a = text.index('а)')
        assert analyzer.is_inside_citation(text, pos_a) is False
        
        # Позиция "б)" — после несбалансированных кавычек в строке "а)"
        pos_b = text.index('б)')
        # 🔑 Не должна считаться "внутри цитаты" из-за опечатки
        assert analyzer.is_inside_citation(text, pos_b) is False
        
        # Позиция "в)" — внутри настоящей цитаты
        pos_v = text.index('в)')
        assert analyzer.is_inside_citation(text, pos_v) is True


    def test_extract_text_with_unbalanced_quotes(self, analyzer):
        """Несбалансированные кавычки сохраняются как есть."""
        text = 'слова «сеть «Интернет» заменить'
        result = analyzer.extract_text_outside_quotes(text)
        
        # 🔑 Все символы сохранены, включая « и »
        assert '«сеть «Интернет»' in result
        assert 'заменить' in result


    def test_real_world_amendment_11a(self, analyzer):
        """
        Реальный текст из пункта 11.а) с опечаткой.
        """
        text = 'в абзаце первом слова «сеть «Интернет» заменить словами «сеть «Интернет»)»'
        
        # 🔑 Позиция "заменить" — должна быть доступна для парсинга
        replace_pos = text.index('заменить')
        
        # Не должна считаться внутри цитаты
        assert analyzer.is_inside_citation(text, replace_pos) is False
        
        # Извлечённый текст должен содержать "заменить"
        extracted = analyzer.extract_text_outside_quotes(text)
        assert 'заменить' in extracted
        assert 'словами' in extracted

@pytest.mark.parametrize("quote_content,expected_is_citation", [
    ('а', False),
    ('б', False),
    ('13', False),
    ('4.1', False),
    ('Интернет', False),
    ('ФГИС ЦС', False),
    ('Методика', False),
    ('это очень длинная цитата, которая содержит более пятидесяти символов для проверки', True),
    ('первая строка\nвторая строка', True),
])
def test_analyze_quote_criteria(quote_content, expected_is_citation):
    """Проверка критериев определения цитаты."""
    text = f'текст «{quote_content}» продолжение'
    info = quote_analyzer.analyze(text, text.index('«'))
    
    assert info['is_citation'] == expected_is_citation, \
        f"Для содержимого '{quote_content[:30]}...' ожидалось is_citation={expected_is_citation}"