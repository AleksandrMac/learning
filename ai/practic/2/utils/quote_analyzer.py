# utils/quote_analyzer.py
import re
from typing import Dict


class QuoteAnalyzer:
    """
    Утилитарный класс для анализа кавычек «...».
    
    🔑 Теперь корректно обрабатывает несбалансированные кавычки
    (опечатки в исходных документах).
    """
    
    QUOTE_INTRO_PATTERNS = [
        r'в\s+следующей\s+редакции\s*:\s*',
        r'следующем\s+содержании\s*:\s*',
        r'дополнить\s+словами\s*:\s*',
        r'изложить\s+в\s+следующей\s+редакции\s*:\s*',
    ]
    
    def analyze(self, text: str, start_pos: int) -> Dict:
        """
        Анализирует кавычку и определяет её тип.
        
        🔑 ИСПРАВЛЕНИЕ: если кавычка не закрывается до конца строки
        или до следующего ключевого слова — это опечатка, не цитата.
        """
        # 🔑 Ищем закрывающую кавычку с учётом вложенности
        balance = 1
        j = start_pos + 1
        has_nested = False
        found_close = False
        
        # 🔑 Ограничение: ищем только до конца текущей строки
        # или до следующего ключевого слова amendment
        line_end = text.find('\n', start_pos)
        if line_end == -1:
            line_end = len(text)
        
        while j < len(text) and balance > 0:
            # 🔑 Если вышли за пределы строки и баланс не нулевой — опечатка
            if j > line_end and balance > 0:
                # Проверяем, нет ли ключевого слова после строки
                next_line = text[line_end + 1:line_end + 100]
                if self._is_amendment_boundary(next_line):
                    # Достигли границы amendment — кавычка не закрылась
                    break
            
            if text[j] == '«':
                balance += 1
                has_nested = True
            elif text[j] == '»':
                balance -= 1
                if balance == 0:
                    found_close = True
            j += 1
        
        # 🔑 Если кавычка не закрылась — это опечатка, не цитата
        if not found_close:
            return {
                'is_citation': False,  # 🔑 Не считаем цитатой
                'end_pos': start_pos + 1,  # Пропускаем только открывающую «
                'content': '',
                'has_nested': False,
                'is_unbalanced': True,  # 🔑 Флаг опечатки
            }
        
        content = text[start_pos + 1:j - 1]
        
        # Критерии цитаты
        is_multiline = '\n' in content
        is_long = len(content.strip()) > 50
        is_after_intro = self._is_after_quote_intro(text, start_pos)
        
        if has_nested and (is_multiline or is_long):
            is_citation = True
        elif is_multiline or is_long:
            is_citation = True
        elif is_after_intro and len(content.strip()) > 10:
            is_citation = True
        else:
            is_citation = False
        
        return {
            'is_citation': is_citation,
            'end_pos': j,
            'content': content,
            'has_nested': has_nested,
            'is_unbalanced': False,
        }
    
    def _is_amendment_boundary(self, text: str) -> bool:
        """
        Проверяет, начинается ли текст с границы amendment.
        
        Границы:
        - Новый пункт: "12.", "13." и т.д.
        - Ключевые слова: "заменить", "исключить", "дополнить", "изложить"
        """
        # Новый пункт amendment
        if re.match(r'^\s*\d+\.\s+', text):
            return True
        
        # Ключевые слова amendments
        keywords = ['заменить', 'исключить', 'дополнить', 'изложить']
        text_lower = text.lower()
        return any(kw in text_lower for kw in keywords)
    
    def _is_after_quote_intro(self, text: str, pos: int) -> bool:
        """Проверяет, стоит ли перед позицией ключевое слово цитаты."""
        prefix = text[max(0, pos - 50):pos]
        for pattern in self.QUOTE_INTRO_PATTERNS:
            if re.search(pattern + r'$', prefix, re.IGNORECASE):
                return True
        return False
    
    def is_inside_citation(self, text: str, pos: int) -> bool:
        """
        Проверяет, находится ли позиция внутри кавычки-ЦИТАТЫ.
        
        🔑 ИСПРАВЛЕНИЕ: несбалансированные кавычки игнорируются.
        """
        i = 0
        
        while i < pos:
            if text[i] == '«':
                quote_info = self.analyze(text, i)
                
                # 🔑 Если кавычка несбалансирована — пропускаем её
                if quote_info.get('is_unbalanced'):
                    i += 1
                    continue
                
                if quote_info['is_citation']:
                    if i < pos < quote_info['end_pos']:
                        return True
                i = quote_info['end_pos']
            else:
                i += 1
        
        return False
    
    def extract_text_outside_quotes(self, text: str) -> str:
        """
        Извлекает текст вне кавычек-ЦИТАТ.
        
        🔑 ИСПРАВЛЕНИЕ: несбалансированные кавычки сохраняются как есть.
        """
        result = []
        i = 0
        
        while i < len(text):
            char = text[i]
            
            if char == '«':
                quote_info = self.analyze(text, i)
                
                # 🔑 Несбалансированная кавычка — сохраняем как обычный символ
                if quote_info.get('is_unbalanced'):
                    result.append(char)
                    i += 1
                    continue
                
                if quote_info['is_citation']:
                    # Цитата — пропускаем
                    i = quote_info['end_pos']
                else:
                    # Обозначение или название — сохраняем
                    result.append(text[i:quote_info['end_pos']])
                    i = quote_info['end_pos']
            else:
                result.append(char)
                i += 1
        
        return ''.join(result)


# Глобальный экземпляр
quote_analyzer = QuoteAnalyzer()