import re
from .base import BaseHandler, ParseContext
from .definition_handler import DefinitionHandler
from nodes.registry import NodeRegistry
from nodes.base import BaseNode


class FormulaHandler(BaseHandler):
    """Обработчик формул."""
    
    FORMULA_PATTERN = re.compile(
        r'\$\$\s*([\s\S]+?)\s*\\tag\{(\d+(?:\.\d+)?)\}\s*\$\$',
        re.DOTALL
    )
    WHERE_PATTERN = re.compile(r'где:', re.IGNORECASE)
    
    def can_handle(self, context: ParseContext) -> bool:
        """Проверяем наличие формулы."""
        return bool(self.FORMULA_PATTERN.search(context.block))
    
    def handle(self, context: ParseContext) -> BaseNode:
        """Парсим формулу с определениями."""
        match = self.FORMULA_PATTERN.search(context.block)
        if not match:
            raise ValueError(f"Не удалось распарсить формулу: {context.block}")
        
        expression = match.group(1).strip()
        number = match.group(2)
        
        # Создаём узел формулы
        formula = NodeRegistry.create(
            'formula',
            number=number,
            expression=expression
        )
        
        # Если есть "где:", извлекаем определения
        if self.WHERE_PATTERN.search(context.block):
            def_handler = DefinitionHandler()
            definitions = def_handler.extract_definitions(context.block)
            
            for def_data in definitions:
                def_node = NodeRegistry.create('definition', **def_data)
                formula.add_child(def_node)
        
        return formula