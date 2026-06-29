import pytest
from handlers.definition_handler import DefinitionHandler


class TestDefinitionHandler:
    """Тесты обработчика определений."""
    
    @pytest.fixture
    def handler(self):
        return DefinitionHandler()
    
    def test_extract_single_definition(self, handler):
        """Извлечение одного определения."""
        text = '- $\\text{Ц}_\\text{a}$ - цена услуг на предоставление ' \
               'несерийных строительных машин, руб./сут.'
        
        definitions = handler.extract_definitions(text)
        
        assert len(definitions) == 1
        assert 'Ц' in definitions[0]['term']
        assert 'цена услуг' in definitions[0]['description']
    
    def test_extract_multiple_definitions(self, handler):
        """Извлечение нескольких определений."""
        text = ('где:\n'
                '- $\\text{Ц}_\\text{a}$ - цена услуг, руб./сут.;\n'
                '- $\\text{Т}_\\text{c}$ - продолжительность работы, ч./сут.')
        
        definitions = handler.extract_definitions(text)
        
        assert len(definitions) == 2
        assert any('Ц' in d['term'] for d in definitions)
        assert any('Т' in d['term'] for d in definitions)
    
    def test_extract_definition_with_complex_description(self, handler):
        """Извлечение определения со сложным описанием."""
        text = ('- $\\text{Ц}_\\text{a}$ - цена услуг на предоставление '
                'несерийных строительных машин во временную эксплуатацию, '
                'руб./сут. (определяется делением цены коммерческих предложений '
                'соответствующих юридических лиц на срок временной эксплуатации, '
                'указанный в коммерческом предложении);')
        
        definitions = handler.extract_definitions(text)
        
        assert len(definitions) == 1
        assert 'коммерческих предложений' in definitions[0]['description']
        assert 'руб./сут' in definitions[0]['description']