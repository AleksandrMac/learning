from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
import uuid


@dataclass
class BaseNode:
    """Базовый класс для всех узлов."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parent_id: Optional[str] = None
    valid_from: Optional[str] = None
    children: List['BaseNode'] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)
    node_type: str = field(init=False, default='base')
    
    def add_child(self, child: 'BaseNode') -> 'BaseNode':
        """Добавить дочерний узел."""
        child.parent_id = self.id
        self.children.append(child)
        return self