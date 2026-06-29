# parsers/amendment_document_parser.py
import re
from typing import List, Tuple
from .base import BaseDocumentParser
from handlers.amendment_handler import AmendmentHandler


class AmendmentDocumentParser(BaseDocumentParser):
    """Парсер для документов-изменений."""
    
    def __init__(self):
        super().__init__()
        self.register_handler(AmendmentHandler())
    
    def _split_into_blocks(self, text: str) -> List[str]:
        """
        Разбивает текст изменений на отдельные пункты (amendments).
        
        🔑 ИСПРАВЛЕНИЕ: разбиваем ТОЛЬКО по номерам пунктов (\n\d+\.),
        НЕ разбиваем по подпунктам (а), б), в)).
        
        Подпункты обрабатываются в AmendmentHandler._split_into_actions().
        """
        # Находим все валидные пары кавычек
        valid_ranges = self._find_valid_quote_ranges(text)
        
        # 🔑 Паттерн ТОЛЬКО для номеров пунктов (1., 2., ...)
        # НЕ включаем подпункты (а), б), в))
        para_pattern = re.compile(r'(?:^|\n)(\d+\.\s+)', re.MULTILINE)
        matches = list(para_pattern.finditer(text))
        
        if not matches:
            return [text.strip()] if text.strip() else []
        
        # Фильтруем позиции, которые внутри валидных кавычек
        valid_matches = []
        for match in matches:
            pos = match.start()
            if not self._is_in_any_range(pos, valid_ranges):
                valid_matches.append(match)
        
        if not valid_matches:
            return [text.strip()] if text.strip() else []
        
        # Собираем блоки
        blocks = []
        for i, match in enumerate(valid_matches):
            start = match.start()
            end = valid_matches[i + 1].start() if i + 1 < len(valid_matches) else len(text)
            block = text[start:end].strip()
            if block:
                blocks.append(block)
        
        return blocks

    def _is_in_any_range(self, pos: int, ranges: List[Tuple[int, int]]) -> bool:
        """Проверяет, находится ли позиция внутри любой из валидных кавычек."""
        for open_pos, close_pos in ranges:
            if open_pos < pos < close_pos:
                return True
        return False
    
    # parsers/amendment_document_parser.py

    # parsers/amendment_document_parser.py

    def _find_valid_quote_ranges(self, text: str) -> List[Tuple[int, int]]:
        """
        Находит все валидные пары кавычек «...».
        
        🔑 ИСПРАВЛЕНИЕ: проверяем, что ключевое слово находится ДО кавычки,
        а не после неё.
        """
        new_point_pattern = re.compile(r'\n\s*\d+\.\s')
        quote_intro_pattern = re.compile(
            r'(?:'
            r'в\s+следующей\s+редакции'
            r'|следующем\s+содержании'
            r'|следующего\s+содержания'
            r'|следующую\s+редакцию'
            r'|в\s+следующей\s+формулировке'
            r')\s*:',
            re.IGNORECASE
        )
        
        opens = [m.start() for m in re.finditer(r'«', text)]
        closes = [m.start() for m in re.finditer(r'»', text)]
        
        # ШАГ 1: Находим "большие" цитаты (после ключевого слова)
        big_quotes = []
        used_opens = set()
        used_closes = set()
        
        for open_pos in opens:
            prefix = text[max(0, open_pos - 150):open_pos]
            keyword_match = quote_intro_pattern.search(prefix)
            
            if not keyword_match:
                continue
            
            #  КРИТИЧЕСКАЯ ПРОВЕРКА: ключевое слово должно быть ДО кавычки
            keyword_end_in_full_text = max(0, open_pos - 150) + keyword_match.end()
            if keyword_end_in_full_text > open_pos:
                # Ключевое слово находится ПОСЛЕ кавычки — пропускаем
                continue
            
            # Проверяем, что между ключевым словом и кавычкой только пробелы
            between = text[keyword_end_in_full_text:open_pos]
            if not re.match(r'^\s*$', between):
                continue
            
            # Проверяем, что между ключевым словом и кавычкой нет других кавычек
            has_other_quotes = '«' in between or '»' in between
            if has_other_quotes:
                continue
            
            # Нашли открывающую после ключевого слова — ищем закрывающую
            close_pos = self._find_balanced_close_for_citation(text, open_pos, closes)
            
            if close_pos != -1 and close_pos not in used_closes:
                big_quotes.append((open_pos, close_pos))
                used_opens.add(open_pos)
                used_closes.add(close_pos)
        
        # ШАГ 2: Находим короткие кавычки
        short_quotes = []
        for open_pos in opens:
            if open_pos in used_opens:
                continue
            
            for close_pos in closes:
                if close_pos <= open_pos or close_pos in used_closes:
                    continue
                
                segment = text[open_pos:close_pos]
                segment_length = len(segment)
                has_new_point = bool(new_point_pattern.search(segment))
                
                if segment_length < 500 and not has_new_point:
                    short_quotes.append((open_pos, close_pos))
                    used_closes.add(close_pos)
                    break
        
        # ШАГ 3: Объединяем и сортируем
        valid_ranges = big_quotes + short_quotes
        valid_ranges.sort(key=lambda x: x[0])
        
        return valid_ranges

    def _find_balanced_close_for_citation(self, text: str, open_pos: int, 
                                       all_closes: List[int]) -> int:
        """
        Находит закрывающую кавычку для цитаты после ключевого слова.
        
        🔑 ЭВРИСТИКА: различаем короткие цитаты (заканчиваются на ».) 
        и длинные (содержат новые пункты \n\d+\.).
        """
        balance = 0
        candidates = []
        
        # 🔹 Шаг 1: собираем все позиции, где баланс становится 0
        for i in range(open_pos, len(text)):
            if text[i] == '«':
                balance += 1
            elif text[i] == '»':
                balance -= 1
                if balance < 0: 
                    balance = 0  # защита от опечаток
                if balance == 0:
                    candidates.append(i)
        
        if not candidates:
            return text.rfind('»', open_pos)
        
        # 🔹 Шаг 2: выбираем правильный кандидат по эвристике
        for cand in candidates:
            segment = text[open_pos:cand]
            # Проверяем, есть ли внутри цитаты новые пункты
            has_new_points = bool(re.search(r'\n\s*\d+\.', segment))
            after = text[cand + 1:cand + 50]
            
            if has_new_points:
                #  ДЛИННАЯ ЦИТАТА: закрывается перед \n или в конце текста
                # (игнорируем внутренние »., чтобы не обрезать пункт 206)
                if after.startswith('\n') or not after.strip():
                    return cand
            else:
                # 📝 КОРОТКАЯ ЦИТАТА: закрывается перед . или \n
                # (позволяет разделить пункты 3, 4, 5)
                if after.startswith('.') or after.startswith('\n') or not after.strip():
                    return cand
        
        # 🔹 Шаг 3: фоллбэк — последний кандидат (для сложных краевых случаев)
        return candidates[-1]
