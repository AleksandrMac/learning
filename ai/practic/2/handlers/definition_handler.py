import re
from typing import List, Dict
from .base import BaseHandler, ParseContext
from nodes.base import BaseNode


class DefinitionHandler(BaseHandler):
    """Обработчик определений переменных."""
    
    # Паттерн для извлечения определений из markdown-списка
    DEFINITION_PATTERN = re.compile(
        r'-\s*\$([^$]+)\$\s*[-–—]?\s*(.+?)(?=;\s*$|;\s*-\s*\$|\Z)',
        re.MULTILINE | re.DOTALL
    )
    
    def can_handle(self, context: ParseContext) -> bool:
        """Этот обработчик обычно не используется напрямую."""
        return False
    
    def handle(self, context: ParseContext) -> BaseNode:
        """Не используется напрямую."""
        raise NotImplementedError("Используйте extract_definitions")
    
    def extract_definitions(self, text: str) -> List[Dict[str, str]]:
        """Извлекает определения переменных из текста."""
        definitions = []
        
        matches = self.DEFINITION_PATTERN.findall(text)
        for term, description in matches:
            # Очищаем терм от LaTeX-команд
            clean_term = self._clean_latex(term)
            # Очищаем описание
            clean_desc = description.strip().rstrip(';').strip()
            
            definitions.append({
                'term': clean_term,
                'description': clean_desc
            })
        
        return definitions
    
    def _clean_latex(self, text: str) -> str:
        """Удаляет LaTeX-команды из текста."""
        # Удаляем \text{}, \mathrm{} и подобные
        text = re.sub(r'\\text\{([^}]+)\}', r'\1', text)
        text = re.sub(r'\\mathrm\{([^}]+)\}', r'\1', text)
        # Удаляем оставшиеся обратные слеши
        text = text.replace('\\', '')
        return text.strip()