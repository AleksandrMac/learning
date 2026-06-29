# parsers/target_parser.py
import re
from typing import List, Optional
from nodes.target import TargetAddress, TargetComponent, ComponentType
from utils.quote_analyzer import quote_analyzer  # 🔑 Используем общий анализатор


class TargetParser:
    """Парсер адресов целевых элементов."""
    
    WORD_NUMBERS = {
        # ... (оставляем как было)
        'первый': '1', 'второй': '2', 'третий': '3', 'четвертый': '4',
        'пятый': '5', 'шестой': '6', 'седьмой': '7', 'восьмой': '8',
        'девятый': '9', 'десятый': '10',
        'первого': '1', 'второго': '2', 'третьего': '3', 'четвертого': '4',
        'пятого': '5', 'шестого': '6', 'седьмого': '7', 'восьмого': '8',
        'девятого': '9', 'десятого': '10',
        'первому': '1', 'второму': '2', 'третьему': '3', 'четвертому': '4',
        'пятому': '5', 'шестому': '6', 'седьмому': '7', 'восьмому': '8',
        'первым': '1', 'вторым': '2', 'третьим': '3', 'четвертым': '4',
        'пятым': '5', 'шестым': '6', 'седьмым': '7', 'восьмым': '8',
        'первом': '1', 'втором': '2', 'третьем': '3', 'четвертом': '4',
        'пятом': '5', 'шестом': '6', 'седьмом': '7', 'восьмом': '8',
    }
    
    POINT_PATTERN = re.compile(
        r'(?:в\s+)?(?<!под)пункт\w*\s+(\d+(?:\.\d+)*)',
        re.IGNORECASE
    )
    
    SUBPOINT_PATTERN = re.compile(
        r'(?:в\s+)?подпункт\w*\s+(?:«([а-я])»|([а-я])(?!\w)|(\d+(?:\.\d+)*(?:\.[а-я])?))',
        re.IGNORECASE
    )
    
    PARAGRAPH_PATTERN = re.compile(
        r'(?:в\s+|из\s+|абзац\w*\s+)?абзац\w*\s+'
        r'(\d+|' + '|'.join(WORD_NUMBERS.keys()) + r')',
        re.IGNORECASE
    )
    # паттерн: "пункты 15 и 16"
    POINTS_AND_PATTERN = re.compile(
        r'(?:в\s+)?пункт\w*\s+(\d+)\s+и\s+(\d+)',
        re.IGNORECASE
    )
    
    # паттерн: "пункты 15, 16 и 17"
    POINTS_LIST_PATTERN = re.compile(
        r'(?:в\s+)?пункт\w*\s+((?:\d+\s*,\s*)*\d+(?:\s+и\s+\d+)*)',
        re.IGNORECASE
    )
    
    def parse(self, text: str) -> TargetAddress:
        text = text.strip()
        if not text:
            return TargetAddress.empty()
        
        text_outside_quotes = quote_analyzer.extract_text_outside_quotes(text)
        
        # 🔑 НОВОЕ: сначала проверяем "пункты X и Y" / "пункты X, Y и Z"
        result = self._try_parse_points_list(text_outside_quotes)
        if result:
            return result
        
        result = self._try_parse_range(text_outside_quotes)
        if result:
            return result
        
        result = self._try_parse_full_path(text_outside_quotes)
        if result:
            return result
        
        result = self._try_parse_compound_subpoint(text_outside_quotes)
        if result:
            return result
        
        result = self._try_parse_simple_point(text_outside_quotes)
        if result:
            return result
        
        return TargetAddress.empty()
    
    def _try_parse_points_list(self, text: str) -> Optional[TargetAddress]:
        """
        🔑 НОВОЕ: парсит список пунктов через "и" или запятые.
        
        Примеры:
            "пункты 15 и 16" → [POINT('15'), POINT('16')]
            "пункты 15, 16 и 17" → [POINT('15'), POINT('16'), POINT('17')]
        """
        match = self.POINTS_LIST_PATTERN.search(text)
        if not match:
            return None
        
        numbers_str = match.group(1)
        # Извлекаем все числа
        numbers = re.findall(r'\d+', numbers_str)
        
        if len(numbers) < 2:
            return None
        
        components = [
            TargetComponent(ComponentType.POINT, n, level=1)
            for n in numbers
        ]
        return TargetAddress(components=components)
    
    def _try_parse_full_path(self, text: str) -> Optional[TargetAddress]:
        components = []
        
        point_match = self.POINT_PATTERN.search(text)
        if point_match:
            components.extend(self._split_compound_number(point_match.group(1)))
        
        subpoint_match = self.SUBPOINT_PATTERN.search(text)
        if subpoint_match:
            value = (
                subpoint_match.group(1) or 
                subpoint_match.group(2) or 
                subpoint_match.group(3)
            )
            if value:
                existing_points = [c for c in components if c.type == ComponentType.POINT]
                base_level = len(existing_points) + 1 if existing_points else 1
                components.extend(self._split_compound_number(value, base_level))
        
        paragraph_match = self.PARAGRAPH_PATTERN.search(text)
        if paragraph_match:
            value = paragraph_match.group(1)
            # 🔑 Числительное → преобразуем в число
            number = self.WORD_NUMBERS.get(value.lower(), value)
            # 🔑 Проверяем, что это действительно число
            if number.isdigit():
                components.append(TargetComponent(ComponentType.PARAGRAPH, number))
            # Если не число — игнорируем (это не номер абзаца)
        
        if not components:
            return None
        
        components = self._deduplicate_components(components)
        return TargetAddress(components=components)
    
    def _try_parse_range(self, text: str) -> Optional[TargetAddress]:
        match = re.search(
            r'(?:в\s+)?пункт\w*\s+(\d+)\s*[—–-]\s*(\d+)',
            text,
            re.IGNORECASE
        )
        if not match:
            return None
        
        start = int(match.group(1))
        end = int(match.group(2))
        if start > end:
            return None
        
        components = [
            TargetComponent(ComponentType.POINT, str(i), level=1)
            for i in range(start, end + 1)
        ]
        return TargetAddress(components=components)
    
    def _try_parse_compound_subpoint(self, text: str) -> Optional[TargetAddress]:
        match = re.search(
            r'(?:в\s+)?подпункт\w*\s+(\d+(?:\.\d+)*\.[а-я])',
            text,
            re.IGNORECASE
        )
        if not match:
            return None
        
        components = self._split_compound_number(match.group(1))
        return TargetAddress(components=components)
    
    def _try_parse_simple_point(self, text: str) -> Optional[TargetAddress]:
        match = self.POINT_PATTERN.search(text)
        if not match:
            return None
        
        components = self._split_compound_number(match.group(1))
        return TargetAddress(components=components)
    
    def _split_compound_number(
        self, 
        value: str, 
        start_level: int = 1
    ) -> List[TargetComponent]:
        parts = value.split('.')
        result = []
        
        for i, part in enumerate(parts):
            level = start_level + i
            result.append(TargetComponent(ComponentType.POINT, part, level=level))
        
        return result
    
    def _deduplicate_components(self, components: List[TargetComponent]) -> List[TargetComponent]:
        seen = set()
        result = []
        for comp in components:
            key = (comp.type, comp.value, comp.level)
            if key not in seen:
                seen.add(key)
                result.append(comp)
        return result