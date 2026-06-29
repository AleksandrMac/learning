# handlers/amendment_parsers.py
import re
from typing import List, Tuple
from nodes.registry import NodeRegistry
from nodes.base import BaseNode
from nodes.target import TargetAddress, TargetComponent, ComponentType
from nodes.amendments import Replacement


class BaseAmendmentParser:
    def can_parse(self, text: str) -> bool:
        raise NotImplementedError
    
    def parse(self, text: str, target: TargetAddress) -> BaseNode:
        raise NotImplementedError

# кавычки в середине
class ExcludeAmendmentParser(BaseAmendmentParser):
    # 🔑 ИЗМЕНЕНИЕ: слово|слова|слов
    PATTERN = re.compile(r'слов\w*\s*«(.*)»\s*исключить', re.IGNORECASE)
    
    def can_parse(self, text: str) -> bool:
        return bool(self.PATTERN.search(text))
    
    def parse(self, text: str, target: TargetAddress) -> BaseNode:
        match = self.PATTERN.search(text)
        return NodeRegistry.create(
            'amendment_exclude',
            text=text,
            target=target,
            old_text=match.group(1)
        )

class ReplaceWordsAmendmentParser(BaseAmendmentParser):
    """
    Парсер замены слов.
    
    🔑 Теперь целевой подпункт добавляется в target.components,
    а не в отдельное поле.
    """
    PATTERNS = [
        # "в подпункте «г» слова «X» заменить словами «Y»"
        (
            re.compile(
                r'в\s+подпункте\s*«([а-я])»\s+слова\s*«(.*)»\s+заменить\s+словами\s*«(.*)»',
                re.IGNORECASE
            ),
            'with_subpoint'
        ),
        # "слова «X» заменить словами «Y»"
        (
            re.compile(r'слова\s*«(.*)»\s+заменить\s+словами\s*«(.*)»', re.IGNORECASE),
            'simple'
        ),
    ]
    
    def can_parse(self, text: str) -> bool:
        return any(p.search(text) for p, _ in self.PATTERNS)
    
    def parse(self, text: str, target: TargetAddress) -> BaseNode:
        for pattern, kind in self.PATTERNS:
            match = pattern.search(text)
            if match:
                if kind == 'with_subpoint':
                    # 🔑 Добавляем подпункт в target
                    subpoint_letter = match.group(1)
                    extended_target = self._extend_target_with_subpoint(target, subpoint_letter)
                    
                    return NodeRegistry.create(
                        'amendment_replace_words',
                        text=text,
                        target=extended_target,
                        old_text=match.group(2),
                        new_text=match.group(3)
                    )
                else:
                    return NodeRegistry.create(
                        'amendment_replace_words',
                        text=text, target=target,
                        old_text=match.group(1),
                        new_text=match.group(2)
                    )
        raise ValueError(f"Не удалось распарсить: {text}")
    
    def _extend_target_with_subpoint(self, target: TargetAddress, letter: str) -> TargetAddress:
        """Добавляет подпункт (POINT с level=2) в target."""
        # 🔑 Проверяем, есть ли уже компонент level=2
        has_subpoint = any(
            c.type == ComponentType.POINT and c.level == 2 
            for c in target.components
        )
        if has_subpoint:
            return target
        
        # 🔑 Определяем уровень: если есть level=1, то подпункт — level=2
        max_level = max(
            (c.level for c in target.components if c.type == ComponentType.POINT),
            default=0
        )
        new_level = max_level + 1 if max_level > 0 else 2
        
        new_components = list(target.components) + [
            TargetComponent(ComponentType.POINT, letter, level=new_level)
        ]
        return TargetAddress(components=new_components)

class AddAmendmentParser(BaseAmendmentParser):
    PATTERN = re.compile(
        r'после\s+слов\s*«(.*)»\s*дополнить\s+словами\s*«(.*)»',
        re.IGNORECASE
    )
    
    def can_parse(self, text: str) -> bool:
        return bool(self.PATTERN.search(text))
    
    def parse(self, text: str, target: TargetAddress) -> BaseNode:
        match = self.PATTERN.search(text)
        return NodeRegistry.create(
            'amendment_add',
            text=text, target=target,
            anchor=match.group(1),
            new_text=match.group(2)
        )

class MultipleReplaceWordsParser(BaseAmendmentParser):
    """
    Парсер множественных замен слов в одном подпункте.
    
    Распознаёт формулировки:
    - "слова «X» заменить словами «Y», слова «A» заменить словами «B»"
    - "слова «X» заменить словами «Y»; слова «A» заменить словами «B»"
    """
    # Паттерн одной замены
    SINGLE_REPLACE_PATTERN = re.compile(
        r'слова?\s*«([^»]+)»\s+заменить\s+словами\s*«([^»]+)»',
        re.IGNORECASE
    )
    
    def can_parse(self, text: str) -> bool:
        matches = self.SINGLE_REPLACE_PATTERN.findall(text)
        return len(matches) >= 2
    
    def parse(self, text: str, target: TargetAddress) -> BaseNode:
        matches = self.SINGLE_REPLACE_PATTERN.findall(text)
        
        if len(matches) < 2:
            raise ValueError(f"Не множественная замена: {text}")
        
        # 🔑 Проверяем, есть ли целевой подпункт в тексте
        target = self._maybe_extend_target_with_subpoint(text, target)
        
        replacements = [
            Replacement(old_text=old, new_text=new)
            for old, new in matches
        ]
        
        return NodeRegistry.create(
            'amendment_multiple_replace_words',
            text=text,
            target=target,
            replacements=replacements
        )
    
    def _maybe_extend_target_with_subpoint(
        self, 
        text: str, 
        target: TargetAddress
    ) -> TargetAddress:
        """Добавляет подпункт в target, если он указан в тексте."""
        subpoint_match = re.search(
            r'в\s+подпункте\s*«([а-я])»',
            text,
            re.IGNORECASE
        )
        if not subpoint_match:
            return target
        
        letter = subpoint_match.group(1)
        has_subpoint = any(
            c.type == ComponentType.POINT and getattr(c, 'level', 1) == 2
            for c in target.components
        )
        if has_subpoint:
            return target
        
        new_components = list(target.components) + [
            TargetComponent(ComponentType.POINT, letter, level=2)
        ]
        return TargetAddress(components=new_components)

class AddSubpointParser(BaseAmendmentParser):
    PATTERN = re.compile(
        r'дополнить\s+подпунктом\s*«([а-я])»\s+в\s+следующей\s+редакции:\s*«(.*)»',
        re.IGNORECASE | re.DOTALL
    )
    
    def can_parse(self, text: str) -> bool:
        return bool(self.PATTERN.search(text))
    
    def parse(self, text: str, target: TargetAddress) -> BaseNode:
        match = self.PATTERN.search(text)
        if not match:
            raise ValueError(f"Не удалось распарсить: {text}")
        
        letter = match.group(1)
        content_text = match.group(2).strip()
        new_content = self._parse_new_content(content_text, letter)
        
        return NodeRegistry.create(
            'amendment_add_subpoint',
            text=text, target=target,
            new_subpoint_number=letter,
            new_content=new_content
        )
    
    def _parse_new_content(self, content_text: str, expected_letter: str) -> list:
        new_content = []
        para_pattern = re.compile(
            r'^([а-я])\)\s+(.+?)(?=\n[а-я]\)|\Z)',
            re.DOTALL | re.MULTILINE
        )
        matches = list(para_pattern.finditer(content_text))
        
        if matches:
            for para_match in matches:
                para_letter = para_match.group(1)
                para_text = para_match.group(2).strip()
                point = NodeRegistry.create('point', number=para_letter)
                paragraphs = [p.strip() for p in para_text.split('\n') if p.strip()]
                for idx, para in enumerate(paragraphs, start=1):
                    point.add_child(NodeRegistry.create('paragraph', number=str(idx), text=para))
                new_content.append(point)
        else:
            point = NodeRegistry.create('point', number=expected_letter)
            paragraphs = [p.strip() for p in content_text.split('\n') if p.strip()]
            for idx, para in enumerate(paragraphs, start=1):
                point.add_child(NodeRegistry.create('paragraph', number=str(idx), text=para))
            new_content.append(point)
        
        return new_content  
# кавычки  в конце


class ReplaceAmendmentParser(BaseAmendmentParser):
    QUOTE_MARKERS = [
        r'в\s+следующей\s+редакции\s*[:\s]',
        r'следующем\s+содержании\s*[:\s]',
    ]
    
    def can_parse(self, text: str) -> bool:
        return 'изложить в следующей редакции' in text.lower()
    
    def parse(self, text: str, target: TargetAddress) -> BaseNode:
        quoted_text = self._extract_balanced_quotes(text)
        if not quoted_text:
            raise ValueError(f"Не найдены кавычки: {text}")
        
        new_content = self._parse_new_content(quoted_text)
        
        return NodeRegistry.create(
            'amendment_replace',
            text=text, target=target,
            new_content=new_content
        )
    
    def _extract_balanced_quotes(self, text: str):
        search_start = 0
        for marker in self.QUOTE_MARKERS:
            marker_match = re.search(marker, text, re.IGNORECASE)
            if marker_match:
                search_start = marker_match.end()
                break
        
        remaining_text = text[search_start:]
        start_match = re.search(r'«', remaining_text)
        if not start_match:
            return None
        
        start_pos = search_start + start_match.end()
        balance = 1
        pos = start_pos
        
        while pos < len(text) and balance > 0:
            if text[pos] == '«':
                balance += 1
            elif text[pos] == '»':
                balance -= 1
            pos += 1
        
        if balance != 0:
            return None
        
        return text[start_pos:pos - 1].strip()
    
    def _parse_new_content(self, quoted_text: str) -> List[BaseNode]:
        para_pattern = re.compile(
            r'^\s*(?:(\d+)\.\s+|([а-я])\)\s+)',
            re.MULTILINE
        )
        matches = list(para_pattern.finditer(quoted_text))
        
        if not matches:
            point = NodeRegistry.create('point', number=None)
            paragraphs = [p.strip() for p in quoted_text.split('\n') if p.strip()]
            for idx, para in enumerate(paragraphs, start=1):
                point.add_child(NodeRegistry.create('paragraph', number=str(idx), text=para))
            return [point]
        
        new_content = []
        for i, match in enumerate(matches):
            number = match.group(1) or match.group(2)
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(quoted_text)
            para_text = quoted_text[start:end].strip()
            
            point = NodeRegistry.create('point', number=number)
            paragraphs = [p.strip() for p in para_text.split('\n') if p.strip()]
            for idx, para in enumerate(paragraphs, start=1):
                point.add_child(NodeRegistry.create('paragraph', number=str(idx), text=para))
            new_content.append(point)
        
        return new_content

class AddParagraphParser(BaseAmendmentParser):
    """
    Парсер для 'дополнить абзацем следующего содержания: «...»'.
    """
    PATTERN = re.compile(
        r'дополнить\s+абзацем\s+(?:следующего\s+содержания|вторым|третьим|четвертым|пятым)\s*:?\s*«(.*)»',
        re.IGNORECASE | re.DOTALL
    )
    
    def can_parse(self, text: str) -> bool:
        return bool(self.PATTERN.search(text))
    
    def parse(self, text: str, target: TargetAddress) -> BaseNode:
        match = self.PATTERN.search(text)
        if not match:
            raise ValueError(f"Не удалось распарсить 'дополнить абзацем': {text}")
        
        quoted_text = match.group(1).strip()
        
        # Парсим содержимое нового абзаца
        new_content = []
        paragraph = NodeRegistry.create('paragraph', number='1', text=quoted_text)
        new_content.append(paragraph)
        
        return NodeRegistry.create(
            'amendment_add_paragraph',
            text=text,
            target=target,
            new_content=new_content
        )
    
class AddPointsParser(BaseAmendmentParser):
    """
    Парсер для 'Дополнить пунктами X — Y следующего содержания: «...»'.
    """
    PATTERN = re.compile(
        r'дополнить\s+пунктами\s+(\d+)\s*[—–-]\s*(\d+)\s+следующего\s+содержания\s*:?\s*«(.*)»',
        re.IGNORECASE | re.DOTALL
    )
    
    def can_parse(self, text: str) -> bool:
        return bool(self.PATTERN.search(text))
    
    def parse(self, text: str, target: TargetAddress) -> BaseNode:
        match = self.PATTERN.search(text)
        if not match:
            raise ValueError(f"Не удалось распарсить 'дополнить пунктами': {text}")
        
        start_point = match.group(1)
        end_point = match.group(2)
        quoted_text = match.group(3).strip()
        
        # 🔑 Парсим содержимое цитаты — извлекаем пункты
        new_content = self._parse_points_from_text(quoted_text, start_point, end_point)
        
        return NodeRegistry.create(
            'amendment_add_points',
            text=text,
            target=target,
            point_range=(start_point, end_point),
            new_content=new_content
        )
    
    def _parse_points_from_text(
        self, 
        text: str, 
        start_point: str, 
        end_point: str
    ) -> List[BaseNode]:
        """
        Парсит текст цитаты и извлекает пункты.
        
        Текст содержит пункты 190, 191, 192, каждый начинается с номера.
        """
        # 🔑 Ищем все номера пунктов в тексте
        point_pattern = re.compile(r'^(\d+)\.\s+', re.MULTILINE)
        matches = list(point_pattern.finditer(text))
        
        if not matches:
            # Если номеров нет — создаём один пункт
            paragraph = NodeRegistry.create('paragraph', number='1', text=text)
            point = NodeRegistry.create('point', number=start_point)
            point.add_child(paragraph)
            return [point]
        
        # 🔑 Извлекаем каждый пункт
        points = []
        for i, match in enumerate(matches):
            point_number = match.group(1)
            start = match.end()
            
            if i + 1 < len(matches):
                end = matches[i + 1].start()
            else:
                end = len(text)
            
            point_text = text[start:end].strip()
            
            # 🔑 Разбиваем текст пункта на абзацы
            paragraphs = self._split_into_paragraphs(point_text)
            
            point = NodeRegistry.create('point', number=point_number)
            for j, para_text in enumerate(paragraphs):
                paragraph = NodeRegistry.create('paragraph', number=str(j + 1), text=para_text)
                point.add_child(paragraph)
            
            points.append(point)
        
        return points
    
    def _split_into_paragraphs(self, text: str) -> List[str]:
        """Разбивает текст пункта на абзацы по переносам строк."""
        # 🔑 Простая логика: разбиваем по \n\n или одиночным \n
        paragraphs = re.split(r'\n\s*\n|\n(?=\S)', text)
        return [p.strip() for p in paragraphs if p.strip()]
    
class AddSectionParser(BaseAmendmentParser):
    """
    Парсер для 'Дополнить Методику разделом N следующего содержания: «...»'.
    """
    PATTERN = re.compile(
        r'дополнить\s+(?:Методику\s+)?разделом\s+([IVX]+)\s+следующего\s+содержания\s*:?\s*«(.*)»$',
        re.IGNORECASE | re.DOTALL
    )
    
    def __init__(self):
        from parsers.main_document_parser import MainDocumentParser
        self.main_parser = MainDocumentParser()
    
    def can_parse(self, text: str) -> bool:
        return bool(self.PATTERN.search(text))
    
    def parse(self, text: str, target: TargetAddress) -> BaseNode:
        match = self.PATTERN.search(text)
        if not match:
            raise ValueError(f"Не удалось распарсить 'дополнить разделом': {text}")
        
        section_number = match.group(1)
        quoted_text = match.group(2).strip()
        
        # Удаляем последнюю » если она есть
        if quoted_text.endswith('»'):
            quoted_text = quoted_text[:-1].strip()
        
        while quoted_text.endswith('»'):
            quoted_text = quoted_text[:-1].strip()
        
        section_title = self._extract_section_title(quoted_text, section_number)
        
        # 🔑 Используем MainDocumentParser для парсинга содержимого
        new_content = self.main_parser.parse(quoted_text)
        
        return NodeRegistry.create(
            'amendment_add_section',
            text=text,
            target=target,
            section_title=section_title,
            new_content=new_content
        )
    
    def _extract_section_title(self, text: str, section_number: str) -> str:
        """Извлекает заголовок раздела из цитаты."""
        match = re.search(
            r'##\s+' + re.escape(section_number) + r'\.\s*(.+?)(?=\n\d+\.|\Z)',
            text,
            re.IGNORECASE | re.DOTALL
        )
        if match:
            return f"## {section_number}. {match.group(1).strip()}"
        return f"## {section_number}."
        
# без кавычек
class RepealParagraphParser(BaseAmendmentParser):
    """
    Парсер 'абзац N признать утратившим силу'.
    
    🔑 Теперь целевой абзац добавляется в target.components,
    а не в отдельное поле.
    """
    PATTERN = re.compile(
        r'абзац\s+(\w+)\s+признать\s+утратившим\s+силу',
        re.IGNORECASE
    )
    
    WORD_NUMBERS = {
        'первый': '1', 'второй': '2', 'третий': '3', 'четвертый': '4',
        'пятый': '5', 'шестой': '6', 'седьмой': '7', 'восьмой': '8',
        'девятый': '9', 'десятый': '10',
        'первого': '1', 'второго': '2', 'третьего': '3', 'четвертого': '4',
        'пятого': '5', 'шестого': '6', 'седьмого': '7', 'восьмого': '8',
        'девятого': '9', 'десятого': '10',
    }
    
    def can_parse(self, text: str) -> bool:
        return bool(self.PATTERN.search(text))
    
    def parse(self, text: str, target: TargetAddress) -> BaseNode:
        match = self.PATTERN.search(text)
        if not match:
            raise ValueError(f"Не удалось распарсить: {text}")
        
        word = match.group(1).lower()
        para_number = self.WORD_NUMBERS.get(word, word)
        
        # 🔑 Добавляем абзац в target
        extended_target = self._extend_target_with_paragraph(target, para_number)
        
        return NodeRegistry.create(
            'amendment_repeal',
            text=text,
            target=extended_target,
        )
    
    def _extend_target_with_paragraph(self, target: TargetAddress, para_number: str) -> TargetAddress:
        """Добавляет абзац в target."""
        has_paragraph = any(c.type == ComponentType.PARAGRAPH for c in target.components)
        if has_paragraph:
            return target
        
        new_components = list(target.components) + [
            TargetComponent(ComponentType.PARAGRAPH, para_number)
        ]
        return TargetAddress(components=new_components)
        
class AmendmentParserFactory:
    PARSERS = [
        # 1. Сначала специфичные парсеры с уникальными фразами
        AddSectionParser(),           # "дополнить разделом N следующего содержания:"
        ReplaceAmendmentParser(),     # "изложить в следующей редакции:"
        
        # 2. Парсеры с подпунктами
        AddSubpointParser(),          # "дополнить подпунктом..."
        RepealParagraphParser(),      # "исключить абзац..."
        AddParagraphParser(),         # "дополнить абзацем..."
        AddPointsParser(),            # "дополнить пунктами..."
        
        # 3. Парсеры замены слов (от множественной к одиночной)
        MultipleReplaceWordsParser(), # "слова «...» заменить словами «...»; слова «...» заменить..."
        ReplaceWordsAmendmentParser(),# "слова «...» заменить словами «...»"
        
        # 4. Общие парсеры добавления/исключения
        AddAmendmentParser(),         # "дополнить словами «...»"
        ExcludeAmendmentParser(),     # "слова «...» исключить"
    ]

    @classmethod
    def parse(cls, text: str, target: TargetAddress) -> BaseNode:
        for parser in cls.PARSERS:
            if parser.can_parse(text):
                try:
                    return parser.parse(text, target)
                except ValueError:
                    continue
        
        return NodeRegistry.create(
            'amendment',
            text=text, target=target,
            action='unknown'
        )