import re
from .base import BaseHandler, ParseContext
from nodes.registry import NodeRegistry
from nodes.base import BaseNode


class SectionHandler(BaseHandler):
    """Обработчик разделов (глав)."""
    
    SECTION_PATTERN = re.compile(r'^##\s+([IVX]+)\.\s*(.+)$', re.MULTILINE)
    
    def can_handle(self, context: ParseContext) -> bool:
        """Проверяем, начинается ли блок с заголовка раздела."""
        return bool(self.SECTION_PATTERN.match(context.block.strip()))
    
    def handle(self, context: ParseContext) -> BaseNode:
        """Извлекаем номер и название раздела."""
        match = self.SECTION_PATTERN.match(context.block.strip())
        if not match:
            raise ValueError(f"Не удалось распарсить раздел: {context.block}")
        
        number = match.group(1)
        title = match.group(2).strip()
        
        return NodeRegistry.create(
            'section',
            number=number,
            title=title
        )