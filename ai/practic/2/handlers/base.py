from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod
from nodes.base import BaseNode


@dataclass
class ParseContext:
    """Контекст, передаваемый между обработчиками."""
    block: str
    node_type: Optional[str] = None
    node_data: Dict[str, Any] = field(default_factory=dict)
    handled: bool = False


class BaseHandler(ABC):
    """Базовый обработчик."""
    
    @abstractmethod
    def can_handle(self, context: ParseContext) -> bool:
        """Проверить, может ли обработчик обработать блок."""
        pass
    
    @abstractmethod
    def handle(self, context: ParseContext) -> BaseNode:
        """Обработать блок и вернуть узел."""
        pass