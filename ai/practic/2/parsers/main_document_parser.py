import re
from typing import List
from .base import BaseDocumentParser
from handlers.section_handler import SectionHandler
from handlers.paragraph_handler import ParagraphHandler


class MainDocumentParser(BaseDocumentParser):
    """Парсер для основного документа."""
    
    def __init__(self):
        super().__init__()
        # 🔑 ИЗМЕНЕНИЕ: AmendmentHandler регистрируется ПЕРЕД ParagraphHandler
        self.register_handler(SectionHandler())
        self.register_handler(ParagraphHandler())
    
    def _split_into_blocks(self, source: str) -> List[str]:
        """Разбиение основного документа на блоки."""
        blocks = []
        
        has_sections = re.search(r'^##\s+[IVX]+\.', source, re.MULTILINE)
        
        if not has_sections:
            return self._split_by_paragraphs(source)
        
        lines = source.split('\n')
        content_start = 0
        
        for i, line in enumerate(lines):
            if line.startswith('## '):
                content_start = i
                break
        
        content = '\n'.join(lines[content_start:])
        
        section_pattern = re.compile(
            r'(^##\s+[IVX]+\..+?)(?=^##|\Z)', 
            re.MULTILINE | re.DOTALL
        )
        
        sections = section_pattern.findall(content)
        
        for section in sections:
            section_lines = section.split('\n')
            header = section_lines[0]
            body = '\n'.join(section_lines[1:])
            
            blocks.append(header)
            
            paragraph_blocks = self._split_section_into_paragraphs(body)
            blocks.extend(paragraph_blocks)
        
        return blocks
    
    def _split_by_paragraphs(self, text: str) -> List[str]:
        """
        Разбивает текст на блоки по номерам пунктов.
        
        🔑 ИСПРАВЛЕНИЕ: использует простую проверку баланса кавычек.
        Несбалансированные кавычки (опечатки) не блокируют разбиение.
        """
        blocks = []
        
        # Паттерн для поиска номеров пунктов
        para_pattern = re.compile(r'(^|\n)(\d+\.\s+)', re.MULTILINE)
        matches = list(para_pattern.finditer(text))
        
        if not matches:
            if text.strip():
                blocks.append(text.strip())
            return blocks
        
        # 🔑 Фильтруем матчи, которые находятся ВНУТРИ сбалансированных кавычек
        valid_matches = []
        for match in matches:
            if not self._is_inside_balanced_quotes(text, match.start()):
                valid_matches.append(match)
        
        if not valid_matches:
            if text.strip():
                blocks.append(text.strip())
            return blocks
        
        # Собираем блоки
        for i, match in enumerate(valid_matches):
            start = match.start()
            if i + 1 < len(valid_matches):
                end = valid_matches[i + 1].start()
            else:
                end = len(text)
            
            block = text[start:end].strip()
            if block:
                blocks.append(block)
        
        return blocks
    
    def _is_inside_balanced_quotes(self, text: str, pos: int) -> bool:
        """
        🔑 ПРОСТАЯ проверка: находится ли позиция внутри сбалансированных кавычек.
        
        Считает баланс « и » до позиции.
        Если баланс > 0 И кавычки сбалансированы после позиции — внутри.
        Если баланс > 0 И кавычки НЕ сбалансированы — опечатка, не внутри.
        """
        prefix = text[:pos]
        open_count = prefix.count('«')
        close_count = prefix.count('»')
        balance = open_count - close_count
        
        # Если баланс 0 — точно не внутри
        if balance == 0:
            return False
        
        # Если баланс > 0 — проверяем, закрываются ли кавычки после позиции
        suffix = text[pos:]
        suffix_open = suffix.count('«')
        suffix_close = suffix.count('»')
        
        # Если в оставшемся тексте больше закрывающих, чем открывающих —
        # значит, кавычки закроются, и мы действительно внутри
        if suffix_close > suffix_open:
            return True
        
        # Если баланс > 0 и кавычки не закрываются — это опечатка
        # Считаем, что мы НЕ внутри цитаты
        return False
    
    def _split_section_into_paragraphs(self, section_text: str) -> List[str]:
        """Разбивает раздел на отдельные пункты."""
        return self._split_by_paragraphs(section_text)