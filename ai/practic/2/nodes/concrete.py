from dataclasses import dataclass
from typing import Optional
from .registry import NodeRegistry
from .base import BaseNode


@NodeRegistry.register('paragraph')
@dataclass
class ParagraphNode(BaseNode):
    """Узел абзаца. Всегда содержит текст."""
    number: Optional[str] = None  # порядковый номер внутри родителя
    text: str = ''


@NodeRegistry.register('point')
@dataclass
class PointNode(BaseNode):
    """Узел пункта/подпункта. Чистый контейнер с номером."""
    number: Optional[str] = None  # '1', '153', 'а', 'б'


@NodeRegistry.register('formula')
@dataclass
class FormulaNode(BaseNode):
    number: Optional[str] = None
    expression: str = ''


@NodeRegistry.register('definition')
@dataclass
class DefinitionNode(BaseNode):
    term: str = ''
    description: str = ''


@NodeRegistry.register('section')
@dataclass
class SectionNode(BaseNode):
    number: Optional[str] = None
    title: str = ''