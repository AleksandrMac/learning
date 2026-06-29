"""
Пакет модели данных для нормативных документов.

Все типы узлов регистрируются при импорте модулей.
"""

from .registry import NodeRegistry
from .base import BaseNode

# Явные импорты — это гарантирует, что все декораторы выполнятся
from .concrete import (
    ParagraphNode,
    PointNode,
    FormulaNode,
    DefinitionNode,
    SectionNode,
)
from .amendments import (
    AmendmentNode,
    ExcludeAmendmentNode,
    AddAmendmentNode,
    ReplaceWordsAmendmentNode,
    ReplaceAmendmentNode,
)
from .target import TargetAddress, TargetComponent, ComponentType

__all__ = [
    # Реестр и базовый класс
    'NodeRegistry',
    'BaseNode',
    
    # Конкретные узлы
    'ParagraphNode',
    'PointNode',
    'FormulaNode',
    'DefinitionNode',
    'SectionNode',
    
    # Amendments
    'AmendmentNode',
    'ExcludeAmendmentNode',
    'AddAmendmentNode',
    'ReplaceWordsAmendmentNode',
    'ReplaceAmendmentNode',
    
    # Адресация
    'TargetAddress',
    'TargetComponent',
    'ComponentType',
]