# parsers/base.py
import re
from abc import ABC, abstractmethod
from typing import List, Optional
from handlers.base import BaseHandler, ParseContext
from nodes.base import BaseNode
from nodes.concrete import SectionNode  # Импорт безопасен, циклов нет


class BaseDocumentParser(ABC):
    """Базовый парсер с поддержкой иерархии разделов."""

    def __init__(self):
        self.handlers: List[BaseHandler] = []

    def register_handler(self, handler: BaseHandler) -> 'BaseDocumentParser':
        self.handlers.append(handler)
        return self

    def parse(self, source: str) -> List[BaseNode]:
        """
        Парсинг с автоматической привязкой узлов к текущему разделу.
        
        Алгоритм:
        1. Идём по блокам последовательно
        2. Если блок -> SectionNode, запоминаем его как current_section
        3. Если блок -> другой узел, добавляем его в current_section.add_child()
        """
        raw_blocks = self._split_into_blocks(source)
        root_nodes = []
        current_section: Optional[SectionNode] = None

        for block in raw_blocks:
            if not block.strip():
                continue

            node = self._process_block(block)
            if not node:
                continue

            # 🔑 Ключевая логика привязки
            if isinstance(node, SectionNode):
                current_section = node
                root_nodes.append(node)
            else:
                if current_section:
                    current_section.add_child(node)
                else:
                    # Узлы до первого раздела остаются на верхнем уровне
                    root_nodes.append(node)

        return root_nodes

    def _process_block(self, block: str) -> Optional[BaseNode]:
        context = ParseContext(block=block)
        for handler in self.handlers:
            if handler.can_handle(context):
                try:
                    return handler.handle(context)
                except Exception:
                    continue
        from nodes.registry import NodeRegistry
        return NodeRegistry.create('paragraph', text=block.strip())

    @abstractmethod
    def _split_into_blocks(self, source: str) -> List[str]:
        pass