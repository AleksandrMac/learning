# handlers/paragraph_handler.py
import re
from typing import List, Optional
from .base import BaseHandler, ParseContext
from nodes.registry import NodeRegistry
from nodes.base import BaseNode


class ParagraphHandler(BaseHandler):
    """Обработчик пунктов с абзацами, списками и формулами."""
    
    PARAGRAPH_PATTERN = re.compile(r'^(\d+)\.\s+(.+)$', re.DOTALL)
    LIST_ITEM_PATTERN = re.compile(r'^\s*([а-я])\)\s+(.+)$')
    ANCHOR_PATTERN = re.compile(r'^\s*<a\s+[^>]*>\s*</a>\s*$')
    
    def can_handle(self, context: ParseContext) -> bool:
        return bool(self.PARAGRAPH_PATTERN.match(context.block.strip()))
    
    def handle(self, context: ParseContext) -> BaseNode:
        match = self.PARAGRAPH_PATTERN.match(context.block.strip())
        if not match:
            raise ValueError(f"Не удалось распарсить пункт: {context.block}")
        
        number = match.group(1)
        text = match.group(2).strip()
        
        elements = self._split_into_elements(text)
        if elements is None:
            elements = []
        
        point = NodeRegistry.create('point', number=number)
        para_counter = 1
        last_formula = None
        
        for element in elements:
            if element['type'] == 'text':
                para = NodeRegistry.create(
                    'paragraph', number=str(para_counter), text=element['text']
                )
                point.add_child(para)
                para_counter += 1
                last_formula = None
                
            elif element['type'] == 'list_item':
                subpoint = NodeRegistry.create('point', number=element['letter'])
                paragraphs = [p.strip() for p in element['text'].split('\n') if p.strip()]
                for idx, para_text in enumerate(paragraphs, start=1):
                    para_node = NodeRegistry.create(
                        'paragraph', number=str(idx), text=para_text
                    )
                    subpoint.add_child(para_node)
                point.add_child(subpoint)
                last_formula = None
                
            elif element['type'] == 'formula':
                formula_node = self._create_formula_node(element['text'])
                point.add_child(formula_node)
                last_formula = formula_node
                
            elif element['type'] == 'definitions':
                definitions = element.get('definitions') or []
                if last_formula and definitions:
                    for def_data in definitions:
                        def_node = NodeRegistry.create(
                            'definition', term=def_data['term'], description=def_data['description']
                        )
                        last_formula.add_child(def_node)
                        
        return point
    
    def _create_formula_node(self, formula_text: str):
        match = re.search(r'\$\$(.+?)\$\$', formula_text, re.DOTALL)
        if not match:
            return NodeRegistry.create('formula', number=None, expression=formula_text.strip())
        
        content = match.group(1).strip()
        tag_match = re.search(r'\\tag\{(\d+(?:\.\d+)?)\}', content)
        if tag_match:
            number = tag_match.group(1)
            expression = re.sub(r'\s*\\tag\{[^}]+\}', '', content).strip()
        else:
            number = None
            expression = content
            
        return NodeRegistry.create('formula', number=number, expression=expression)
    
    def _split_into_elements(self, text: str) -> List[dict]:
        result: List[dict] = []
        if not text:
            return result
            
        lines = text.split('\n')
        in_formula = False
        formula_lines: List[str] = []
        in_definitions = False
        definition_lines: List[str] = []
        
        current_list_item: Optional[dict] = None
        
        def flush_list_item():
            nonlocal current_list_item
            if current_list_item:
                current_list_item['text'] = '\n'.join(current_list_item['lines'])
                result.append(current_list_item)
                current_list_item = None
        
        for line in lines:
            stripped = line.strip()
            if self.ANCHOR_PATTERN.match(stripped):
                continue
                
            if '$$' in stripped:
                flush_list_item()
                if not in_formula:
                    if in_definitions and definition_lines:
                        result.append({'type': 'definitions', 'definitions': self._parse_definitions(definition_lines)})
                        definition_lines = []
                        in_definitions = False
                    in_formula = True
                    formula_lines = [line]
                    if stripped.count('$$') >= 2:
                        result.append({'type': 'formula', 'text': '\n'.join(formula_lines)})
                        formula_lines = []
                        in_formula = False
                else:
                    formula_lines.append(line)
                    result.append({'type': 'formula', 'text': '\n'.join(formula_lines)})
                    formula_lines = []
                    in_formula = False
                continue
                
            if in_formula:
                formula_lines.append(line)
                continue
                
            if not stripped:
                continue
                
            if stripped.lower().startswith('где:'):
                flush_list_item()
                if in_definitions and definition_lines:
                    result.append({'type': 'definitions', 'definitions': self._parse_definitions(definition_lines)})
                    definition_lines = []
                in_definitions = True
                continue
                
            if in_definitions:
                if stripped.startswith('- $'):
                    definition_lines.append(stripped)
                else:
                    if definition_lines:
                        result.append({'type': 'definitions', 'definitions': self._parse_definitions(definition_lines)})
                        definition_lines = []
                    in_definitions = False
                if in_definitions:
                    continue
                    
            list_match = self.LIST_ITEM_PATTERN.match(stripped)
            if list_match:
                flush_list_item()
                current_list_item = {
                    'type': 'list_item',
                    'letter': list_match.group(1),
                    'lines': [list_match.group(2).strip()]
                }
            elif current_list_item is not None:
                # 🔑 ИСПРАВЛЕНИЕ: проверяем отступ вместо эвристики с заглавной буквой
                
                # Если строка имеет отступ (пробелы или табуляция) → продолжение пункта
                has_indent = line.startswith('    ') or line.startswith('\t') or line.startswith('  ')
                
                if has_indent:
                    # Продолжение пункта списка
                    current_list_item['lines'].append(stripped)
                else:
                    # Нет отступа → новый абзац (не часть пункта списка)
                    flush_list_item()
                    result.append({'type': 'text', 'text': stripped})
            else:
                flush_list_item()
                result.append({'type': 'text', 'text': stripped})
                
        if definition_lines:
            result.append({'type': 'definitions', 'definitions': self._parse_definitions(definition_lines)})
            
        flush_list_item()
        return result if result is not None else []
    
    def _parse_definitions(self, lines: List[str]) -> List[dict]:
        definitions: List[dict] = []
        if not lines:
            return definitions
            
        for line in lines:
            line = line.lstrip('- ').strip()
            if not line: continue
            
            match = re.match(r'\$(.+?)\$\s*[-–—]?\s*(.+)', line)
            if match:
                term = re.sub(r'\\text\{([^}]+)\}', r'\1', match.group(1)).strip()
                term = re.sub(r'\\mathrm\{([^}]+)\}', r'\1', term).replace('\\', '').strip()
                definitions.append({'term': term, 'description': match.group(2).strip()})
                
        return definitions if definitions is not None else []