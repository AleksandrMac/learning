# handlers/amendment_handler.py

import re
from typing import List, Optional, Tuple
from handlers.base import ParseContext
from nodes.target import TargetAddress, TargetComponent, ComponentType
from parsers.target_parser import TargetParser
from parsers.amendment_parsers import AmendmentParserFactory
from nodes.registry import NodeRegistry
from nodes.base import BaseNode


class AmendmentHandler:
    """
    Парсер одного блока amendment.
    
    🔑 ПРАВИЛЬНАЯ АРХИТЕКТУРА:
    1. Извлекаем intro_text ("7. В пункте 10:")
    2. Парсим intro_target из intro
    3. Извлекаем action_text (всё ПОСЛЕ intro)
    4. Разбиваем action_text на действия
    5. Передаём action_text в AmendmentParserFactory
    6. Объединяем targets через _merge_targets
    """

    def can_handle(self, context: ParseContext) -> bool:
        """
        Проверяет, может ли handler обработать блок.
        
        🔑 AmendmentHandler обрабатывает блоки, начинающиеся с номера (1., 2., ...).
        """
        text = context.block.strip()
        return bool(re.match(r'\d+\.\s+', text))
    
    def handle(self, context: ParseContext) -> BaseNode:
        text = context.block.strip()
        
        # Извлекаем номер
        number_match = re.match(r'(\d+)\.\s+', text)
        if not number_match:
            raise ValueError(f"Не найден номер amendment: {text[:50]}...")
        number = number_match.group(1)
        
        # Извлекаем intro_text
        intro_text = self._extract_intro_text(text)
        
        # Парсим target из intro
        intro_target = TargetParser().parse(intro_text)
        
        # 🔑 Разбиваем ПОЛНЫЙ текст на действия (не только action_text)
        actions = self._split_into_actions(text)
        
        if len(actions) > 1:
            return self._create_composite_amendment(number, intro_target, actions)
        
        # Одно действие — передаём ПОЛНЫЙ текст в фабрику
        try:
            action_node = AmendmentParserFactory.parse(text, intro_target)
            
            # Объединяем targets
            merged_target = self._merge_targets(intro_target, action_node.target)
            if hasattr(action_node, 'target'):
                action_node.target = merged_target
            if hasattr(action_node, 'number'):
                action_node.number = number
            
            return action_node
        except Exception as e:
            print(f"[DEBUG] Фабрика не смогла выбрать парсер: {e}")
            return NodeRegistry.create(
                'amendment',
                text=text,
                target=intro_target,
                action='unknown',
                number=number
            )
    
    def _extract_intro_text(self, text: str) -> str:
        """
        Извлекает вступительную часть (target) amendment.
        
        🔑 Логика:
        1. Если есть `:` → берём до него (многострочные случаи)
        2. Если текст многострочный → берём первую строку
        3. Иначе (однострочный) → возвращаем ВЕСЬ текст
        """
        # 1. Ищем `:` только до первой открывающей кавычки
        first_quote = text.find('«')
        search_area = text[:first_quote] if first_quote != -1 else text
        
        colon_pos = search_area.find(':')
        if colon_pos != -1:
            return text[:colon_pos + 1].strip()
        
        # 2. Если текст многострочный — берём первую строку
        if '\n' in text:
            return text.split('\n')[0].strip()
        
        # 3. Однострочный текст — возвращаем ВЕСЬ
        return text.strip()
    
    def _split_into_actions(self, text: str) -> List[str]:
        """Разбивает текст на отдельные действия."""
        citation_ranges = self._find_citation_ranges(text)
        
        # 1. Подпункты (а), б), в))
        subpoint_pattern = re.compile(r'\n([а-яё])\)\s+', re.MULTILINE)
        subpoint_matches = list(subpoint_pattern.finditer(text))
        
        # 🔑 2. Разделитель ; — только если после него идёт действие
        # Ищем ; за которой следует: пробелы и (ключевое слово ИЛИ открывающая кавычка)
        semicolon_pattern = re.compile(
            r';(?=\s*(?:'
            r'слова|дополнить|заменить|исключить|признать|изложить|'
            r'в\s+пункте|в\s+абзаце|подпункт|«'
            r'))',
            re.IGNORECASE
        )
        semicolon_matches = list(semicolon_pattern.finditer(text))
        
        # Собираем точки разбиения
        split_points = []
        
        for match in subpoint_matches:
            pos = match.start()
            if not self._is_in_any_range(pos, citation_ranges):
                split_points.append(pos)
        
        for match in semicolon_matches:
            pos = match.start()
            if not self._is_in_any_range(pos, citation_ranges):
                split_points.append(pos + 1)  # Разбиваем ПОСЛЕ ;
        
        split_points = sorted(set(split_points))
        
        if not split_points:
            return [text.strip()]
        
        # Разбиваем текст
        actions = []
        start = 0
        for pos in split_points:
            action = text[start:pos].strip()
            if action:
                actions.append(action)
            start = pos
        
        if start < len(text):
            action = text[start:].strip()
            if action:
                actions.append(action)
        
        # Объединяем блоки, состоящие только из »
        merged_actions = []
        for action in actions:
            action = action.strip()
            if action.strip('»\n\t ') == '' and merged_actions:
                merged_actions[-1] += '\n' + action
            else:
                merged_actions.append(action)
        
        return merged_actions if merged_actions else [text.strip()]
    
    def _create_composite_amendment(self, number: str, intro_target: TargetAddress, 
                                     actions: List[str]) -> 'BaseNode':
        """Создаёт composite amendment из нескольких действий."""
        # Ключевые слова amendment
        amendment_keywords = [
            r'исключить', r'дополнить', r'изложить', r'заменить',
            r'внести', r'признать', r'утративш',
        ]
        keyword_pattern = re.compile('|'.join(amendment_keywords), re.IGNORECASE)
        
        # Паттерн для подпунктов в начале действия
        subpoint_start_pattern = re.compile(r'^([а-яё])\)\s*(.*)', re.DOTALL)
        
        # Фильтруем валидные действия
        valid_actions = []
        for action in actions:
            if not action.strip():
                continue
            if not keyword_pattern.search(action):
                print(f"[DEBUG] Пропускаем невалидное действие: {action[:50]}...")
                continue
            valid_actions.append(action)
        
        if not valid_actions:
            return NodeRegistry.create(
                'amendment',
                text='\n'.join(actions),
                target=intro_target,
                action='unknown',
                number=number
            )
        
        # Создаём composite
        composite = NodeRegistry.create(
            'amendment',
            text='\n'.join(valid_actions),
            target=intro_target,
            action='composite',
            number=number
        )
        
        # Парсим каждое действие
        for action_text in valid_actions:
            try:
                subpoint_match = subpoint_start_pattern.match(action_text.strip())
                
                if subpoint_match:
                    # Действие начинается с подпункта (а), б), в))
                    subpoint_letter = subpoint_match.group(1)
                    action_body = subpoint_match.group(2)
                    
                    # 🔑 Извлекаем target из action_body
                    action_target = self._extract_target_from_action(action_body)
                    merged_target = self._merge_targets(intro_target, action_target)
                    
                    # Создаём PointNode
                    subpoint_node = NodeRegistry.create('point', number=subpoint_letter)
                    
                    # Парсим действие
                    action_node = AmendmentParserFactory.parse(action_body, intro_target)
                    
                    # 🔑 Устанавливаем объединённый target
                    if hasattr(action_node, 'target'):
                        action_node.target = merged_target
                    
                    subpoint_node.add_child(action_node)
                    composite.add_child(subpoint_node)
                else:
                    # Обычное действие без подпункта
                    action_target = self._extract_target_from_action(action_text)
                    merged_target = self._merge_targets(intro_target, action_target)
                    
                    action_node = AmendmentParserFactory.parse(action_text, intro_target)
                    
                    if hasattr(action_node, 'target'):
                        action_node.target = merged_target
                    
                    composite.add_child(action_node)
            
            except Exception as e:
                print(f"[DEBUG] Не удалось распарсить действие: {e}")
                print(f"[DEBUG] Текст: {action_text[:100]}...")
        
        return composite
    
    def _extract_target_from_action(self, action_text: str) -> Optional[TargetAddress]:
        """
        Извлекает целевой адрес из начала текста действия.
        
        Примеры:
        - "в подпункте «а» после слов..." → POINT('а')
        - "подпункт «б» изложить..." → POINT('б')
        - "в абзаце третьем..." → PARAGRAPH('3')
        """
        text = action_text.strip()
        
        # Паттерн 1: "в подпункте «X»" или "подпункт «X»"
        match = re.match(r'(?:в\s+)?подпункт(?:е)?\s+«([а-яё])»', text, re.IGNORECASE)
        if match:
            return TargetAddress(components=[
                TargetComponent(ComponentType.POINT, match.group(1), level=1)
            ])
        
        # Паттерн 2: "в пункте X" или "пункт X"
        match = re.match(r'(?:в\s+)?пункт(?:е)?\s+(\d+)', text, re.IGNORECASE)
        if match:
            return TargetAddress(components=[
                TargetComponent(ComponentType.POINT, match.group(1), level=1)
            ])
        
        # Паттерн 3: "в абзаце X" или "абзац X" (все падежи)
        match = re.match(
            r'(?:в\s+)?абзац(?:е)?\s+'
            r'('
            r'первый|второй|третий|четвертый|пятый|шестой|седьмой|восьмой|девятый|десятый|'
            r'первого|второго|третьего|четвертого|пятого|шестого|седьмого|восьмого|девятого|десятого|'
            r'первому|второму|третьему|четвертому|пятому|шестому|седьмому|восьмому|девятому|десятому|'
            r'первым|вторым|третьим|четвертым|пятым|шестым|седьмым|восьмым|девятым|десятым|'
            r'первом|втором|третьем|четвертом|пятом|шестом|седьмом|восьмом|девятом|десятом|'
            r'\d+'
            r')',
            text,
            re.IGNORECASE
        )
        if match:
            value = match.group(1)
            ordinal_map = {
                'первый': '1', 'второй': '2', 'третий': '3', 'четвертый': '4', 'пятый': '5',
                'шестой': '6', 'седьмой': '7', 'восьмой': '8', 'девятый': '9', 'десятый': '10',
                'первого': '1', 'второго': '2', 'третьего': '3', 'четвертого': '4', 'пятого': '5',
                'шестого': '6', 'седьмого': '7', 'восьмого': '8', 'девятого': '9', 'десятого': '10',
                'первому': '1', 'второму': '2', 'третьему': '3', 'четвертому': '4', 'пятому': '5',
                'шестому': '6', 'седьмому': '7', 'восьмому': '8', 'девятому': '9', 'десятому': '10',
                'первым': '1', 'вторым': '2', 'третьим': '3', 'четвертым': '4', 'пятым': '5',
                'шестым': '6', 'седьмым': '7', 'восьмым': '8', 'девятым': '9', 'десятым': '10',
                'первом': '1', 'втором': '2', 'третьем': '3', 'четвертом': '4', 'пятом': '5',
                'шестом': '6', 'седьмом': '7', 'восьмом': '8', 'девятом': '9', 'десятом': '10',
            }
            value = ordinal_map.get(value.lower(), value)
            return TargetAddress(components=[
                TargetComponent(ComponentType.PARAGRAPH, value, level=1)
            ])
        
        return None
    
    def _merge_targets(self, intro_target: TargetAddress, 
                       action_target: Optional[TargetAddress]) -> TargetAddress:
        """
        Объединяет target из intro с target из действия.
        
        🔑 Повышает level дочерних POINT, если они совпадают с уровнем parent.
        """
        if action_target is None or not action_target.components:
            return intro_target
        
        if intro_target is None or not intro_target.components:
            return action_target
        
        max_parent_level = max(c.level for c in intro_target.components)
        
        adjusted = []
        for comp in action_target.components:
            # Проверяем дубликат
            is_dup = any(
                p.type == comp.type and p.value == comp.value
                for p in intro_target.components
            )
            if is_dup:
                continue
            
            # 🔑 Повышаем level, если совпадает с максимальным уровнем родителя
            new_level = comp.level if comp.level > max_parent_level else max_parent_level + 1
            adjusted.append(TargetComponent(comp.type, comp.value, new_level))
        
        merged = intro_target.components + adjusted
        
        # Убираем дубликаты
        seen = set()
        unique = []
        for c in merged:
            key = (c.type, c.value, c.level)
            if key not in seen:
                seen.add(key)
                unique.append(c)
        
        return TargetAddress(components=unique)
    
    def _find_citation_ranges(self, text: str) -> List[Tuple[int, int]]:
        """Находит все цитаты (от ключевого слова до »)."""
        keyword_pattern = re.compile(
            r'(?:'
            r'в\s+следующей\s+редакции'
            r'|следующем\s+содержании'
            r'|следующего\s+содержания'
            r'|следующую\s+редакцию'
            r'|в\s+следующей\s+формулировке'
            r')\s*:\s*«',
            re.IGNORECASE
        )
        
        ranges = []
        closes = [m.start() for m in re.finditer(r'»', text)]
        
        for match in keyword_pattern.finditer(text):
            open_pos = match.end() - 1
            close_pos = self._find_balanced_close_for_citation(text, open_pos, closes)
            if close_pos != -1:
                ranges.append((open_pos, close_pos))
        
        return ranges
    
    def _find_balanced_close_for_citation(self, text: str, open_pos: int, 
                                           all_closes: List[int]) -> int:
        """Находит закрывающую кавычку через балансировку."""
        balance = 0
        for i in range(open_pos, len(text)):
            if text[i] == '«':
                balance += 1
            elif text[i] == '»':
                balance -= 1
                if balance < 0:
                    balance = 0
                    continue
                if balance == 0:
                    after = text[i + 1:i + 50]
                    if after.startswith('\n') or not after.strip():
                        return i
        
        last_close = text.rfind('»')
        return last_close if last_close > open_pos else -1
    
    def _is_in_any_range(self, pos: int, ranges: List[Tuple[int, int]]) -> bool:
        """Проверяет, находится ли позиция внутри любой из валидных кавычек."""
        for open_pos, close_pos in ranges:
            if open_pos < pos < close_pos:
                return True
        return False