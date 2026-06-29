import pytest
from handlers.base import ParseContext
from handlers.formula_handler import FormulaHandler
from nodes.concrete import FormulaNode, DefinitionNode


class TestFormulaHandler:
    """Тесты обработчика формул."""
    
    @pytest.fixture
    def handler(self):
        return FormulaHandler()
    
    def test_can_handle_formula_block(self, handler):
        """Обработчик распознаёт блок с формулой."""
        context = ParseContext(
            block='83. Сметная цена определяется по формуле (3.1):\n'
                  '$$\n'
                  'С_маш.р = Ц_а / Т_с \\tag{3.1}\n'
                  '$$\n'
                  'где:\n'
                  'Ц_а - цена услуг.'
        )
        
        assert handler.can_handle(context) is True
    
    def test_cannot_handle_text_without_formula(self, handler):
        """Обработчик не распознаёт текст без формулы."""
        context = ParseContext(
            block='83. Сметная цена определяется на основании данных ФГИС ЦС.'
        )
        
        assert handler.can_handle(context) is False
    
    def test_handle_formula_with_definitions(self, handler):
        """Парсинг формулы с определениями переменных."""
        context = ParseContext(
            block='83. Сметная цена на эксплуатацию машин и механизмов '
                  '($\\text{СЦэм}_\\text{тек}^k$) определяется на основании '
                  'данных ФГИС ЦС. Сметные цены в текущем уровне цен на '
                  'несерийные строительные машины определяются по формуле (3.1):\n'
                  '$$\n'
                  '\\text{С}_\\text{маш.р}=\\text{Ц}_\\text{a}/\\text{T}_\\text{c} '
                  '\\tag{3.1}\n'
                  '$$\n'
                  'где:\n'
                  '- $\\text{Ц}_\\text{a}$ - цена услуг на предоставление '
                  'несерийных строительных машин во временную эксплуатацию, руб./сут.;\n'
                  '- $\\text{T}_\\text{c}$ - продолжительность работы в соответствии '
                  'с режимом, установленным в ПОС, ч./сут.'
        )
        
        node = handler.handle(context)
        
        assert isinstance(node, FormulaNode)
        assert node.number == '3.1'
        assert 'С_маш.р' in node.expression or 'С' in node.expression
        
        # Проверяем определения
        assert len(node.children) >= 2
        definitions = [c for c in node.children if isinstance(c, DefinitionNode)]
        assert len(definitions) >= 2
        
        # Проверяем первую переменную
        assert any('Ц' in d.term for d in definitions)
        assert any('цена услуг' in d.description for d in definitions)
    
    def test_handle_formula_without_where(self, handler):
        """Парсинг формулы без блока "где:"."""
        context = ParseContext(
            block='Размер средств определяется по формуле (1.1):\n'
                  '$$\n'
                  'ОТм_тек = \\sum ЗТ_ki × СЦ_k \\cdot V_i \\tag{1.1}\n'
                  '$$'
        )
        
        node = handler.handle(context)
        
        assert isinstance(node, FormulaNode)
        assert node.number == '1.1'
        # Определений может не быть
        assert len(node.children) == 0 or all(
            not isinstance(c, DefinitionNode) for c in node.children
        )