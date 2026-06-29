# nodes/target.py
from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum


class ComponentType(Enum):
    """Тип компонента адреса."""
    POINT = 'point'          # пункт или подпункт (различаются по level)
    PARAGRAPH = 'paragraph'  # абзац


@dataclass
class TargetComponent:
    """Один компонент адреса."""
    type: ComponentType
    value: str  # '3', '4', 'а', '1'
    level: int = 1  # 🔑 НОВОЕ: уровень вложенности (1 — пункт, 2 — подпункт, ...)
    
    def __str__(self) -> str:
        if self.type == ComponentType.PARAGRAPH:
            return f'para:{self.value}'
        return self.value


@dataclass
class TargetAddress:
    """
    Адрес целевого элемента в документе.
    
    Примеры:
        "пункт 3" → [POINT('3', level=1)]
        "пункт 4.1" → [POINT('4', level=1), POINT('1', level=2)]
        "подпункт а пункта 4" → [POINT('4', level=1), POINT('а', level=2)]
        "абзац 1 подпункта а пункта 4" → [POINT('4', level=1), POINT('а', level=2), PARAGRAPH('1')]
    """
    components: List[TargetComponent] = field(default_factory=list)
    
    @property
    def is_range(self) -> bool:
        """Проверяет, является ли адрес диапазоном (пункты 153 — 155)."""
        return len(self.components) > 1 and all(
            c.type == ComponentType.POINT and c.level == 1 for c in self.components
        )
    
    @property
    def paragraph_number(self) -> Optional[str]:
        """Номер абзаца."""
        if self.components and self.components[-1].type == ComponentType.PARAGRAPH:
            return self.components[-1].value
        return None
    
    @property
    def full_point_path(self) -> str:
        """Полный путь всех пунктов через точку: '4.1.а'."""
        point_parts = [
            c.value 
            for c in self.components 
            if c.type == ComponentType.POINT
        ]
        return '.'.join(point_parts)
    
    @property
    def max_level(self) -> int:
        """Максимальный уровень вложенности пунктов."""
        point_levels = [
            c.level 
            for c in self.components 
            if c.type == ComponentType.POINT
        ]
        return max(point_levels) if point_levels else 0
    
    def get_component_at_level(self, level: int) -> Optional[TargetComponent]:
        """Получить компонент на заданном уровне."""
        for c in self.components:
            if c.type == ComponentType.POINT and c.level == level:
                return c
        return None
    
    def to_path(self) -> str:
        """Строковое представление пути: '4.а.para:1'."""
        parts = []
        for c in self.components:
            if c.type == ComponentType.PARAGRAPH:
                parts.append(f'para:{c.value}')
            else:
                parts.append(c.value)
        return '.'.join(parts)
    
    def __str__(self) -> str:
        return self.to_path()
    
    @classmethod
    def empty(cls) -> 'TargetAddress':
        return cls(components=[])