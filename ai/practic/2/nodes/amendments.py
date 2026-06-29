# nodes/amendments.py
from dataclasses import dataclass, field
from typing import Optional, List, Tuple
from .registry import NodeRegistry
from .base import BaseNode
from .target import TargetAddress


@NodeRegistry.register('amendment')
@dataclass
class AmendmentNode(BaseNode):
    """Базовый узел изменения."""
    number: Optional[str] = None
    text: str = ''
    target: TargetAddress = field(default_factory=TargetAddress.empty)
    action: Optional[str] = None


@NodeRegistry.register('amendment_exclude')
@dataclass
class ExcludeAmendmentNode(AmendmentNode):
    """Исключение слов/текста."""
    action: str = field(default='exclude')
    old_text: str = ''


@NodeRegistry.register('amendment_add')
@dataclass
class AddAmendmentNode(AmendmentNode):
    """Дополнение словами после якоря."""
    action: str = field(default='add')
    anchor: str = ''
    new_text: str = ''


@NodeRegistry.register('amendment_replace_words')
@dataclass
class ReplaceWordsAmendmentNode(AmendmentNode):
    """Замена слов. Целевой подпункт — в target.components (SUBPOINT)."""
    action: str = field(default='replace_words')
    old_text: str = ''
    new_text: str = ''
    # 🔥 УБРАНО: target_subpoint — теперь в target.components


@NodeRegistry.register('amendment_add_subpoint')
@dataclass
class AddSubpointAmendmentNode(AmendmentNode):
    """Добавление нового подпункта."""
    action: str = field(default='add_subpoint')
    new_subpoint_number: Optional[str] = None
    new_content: List[BaseNode] = field(default_factory=list)

@NodeRegistry.register('amendment_add_points')
@dataclass
class AddPointsAmendmentNode(AmendmentNode):
    """
    Дополнение несколькими пунктами.
    
    Пример: "Дополнить пунктами 190 — 192 следующего содержания: «...»"
    """
    action: str = field(default='add_points')
    point_range: Tuple[str, str] = field(default_factory=lambda: ('', ''))  # ('190', '192')
    new_content: List[BaseNode] = field(default_factory=list)

@NodeRegistry.register('amendment_add_paragraph')
@dataclass
class AddParagraphAmendmentNode(AmendmentNode):
    """
    Дополнение абзацем следующего содержания.
    
    Пример: "дополнить абзацем следующего содержания: «...»"
    """
    action: str = field(default='add_paragraph')
    new_content: List[BaseNode] = field(default_factory=list)

@NodeRegistry.register('amendment_replace')
@dataclass
class ReplaceAmendmentNode(AmendmentNode):
    """Изложение в следующей редакции."""
    action: str = field(default='replace')
    new_content: List[BaseNode] = field(default_factory=list)


@NodeRegistry.register('amendment_repeal')
@dataclass
class RepealAmendmentNode(AmendmentNode):
    """Признание утратившим силу. Целевой абзац — в target.components (PARAGRAPH)."""
    action: str = field(default='repeal')

@dataclass
class Replacement:
    """Одна замена слов."""
    old_text: str
    new_text: str


@NodeRegistry.register('amendment_multiple_replace_words')
@dataclass
class MultipleReplaceWordsAmendmentNode(AmendmentNode):
    """
    Множественная замена слов в одном подпункте/абзаце.
    
    Пример: "слова «X» заменить словами «Y», слова «A» заменить словами «B»"
    """
    action: str = field(default='multiple_replace_words')
    replacements: List[Replacement] = field(default_factory=list)


@NodeRegistry.register('amendment_add_section')
@dataclass
class AddSectionAmendmentNode(AmendmentNode):
    """
    Дополнение документа новым разделом.
    
    Пример: "Дополнить Методику разделом XII следующего содержания: «...»"
    """
    action: str = field(default='add_section')
    section_title: str = field(default='')  # "## XII. Особенности определения..."
    new_content: List[BaseNode] = field(default_factory=list)  # [SectionNode, PointNode...]