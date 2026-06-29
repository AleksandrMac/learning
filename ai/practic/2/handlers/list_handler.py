import re
from typing import List
from .base import BaseHandler, ParseContext
from nodes.registry import NodeRegistry
from nodes.base import BaseNode


class ListHandler(BaseHandler):
    """Обработчик списков с буквенными обозначениями."""
    
    LIST_ITEM_PATTERN = re.compile(r'^\s*([а-я])\)\s+(.+)$', re.MULTILINE)
    
    def can_handle(self, context: ParseContext) -> bool:
        lines = context.block.strip().split('\n')
        has_colon = any(line.rstrip().endswith(':') for line in lines)
        has_items = bool(self.LIST_ITEM_PATTERN.search(context.block))
        return has_colon and has_items
    
    def handle(self, context: ParseContext) -> BaseNode:
        lines = context.block.strip().split('\n')
        
        # Находим вводную строку (заканчивается на ":")
        intro_text = ''
        list_start_idx = 0
        
        for i, line in enumerate(lines):
            if line.rstrip().endswith(':'):
                intro_text = line.rstrip()
                list_start_idx = i + 1
                break
        
        # 🔥 ИЗМЕНЕНИЕ: родитель — PointNode (если есть номер) или ParagraphNode
        number_match = re.match(r'^(\d+)\.\s+(.+)$', intro_text)
        if number_match:
            number = number_match.group(1)
            intro_text = number_match.group(2)
            parent = NodeRegistry.create('point', number=number)

            if intro_text:
                intro_para = NodeRegistry.create(
                    'paragraph',
                    number='1',
                    text=intro_text
                )
                parent.add_child(intro_para)
        else:
            parent = NodeRegistry.create('paragraph', text=intro_text)
        
        # Парсим пункты списка
        list_text = '\n'.join(lines[list_start_idx:])
        items = self.LIST_ITEM_PATTERN.findall(list_text)
        
        for letter, text in items:
            # 🔥 ИЗМЕНЕНИЕ: PointNode без text, текст — в дочернем ParagraphNode
            subpoint = NodeRegistry.create('point', number=letter)
            subpoint_text = NodeRegistry.create(
                'paragraph',
                number='1',
                text=text.strip()
            )
            subpoint.add_child(subpoint_text)
            parent.add_child(subpoint)
        
        return parent