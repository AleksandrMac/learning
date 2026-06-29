from typing import Dict, Type, List, Optional


class NodeRegistry:
    """
    Реестр типов узлов.
    
    Все типы регистрируются через декоратор @NodeRegistry.register
    при импорте модулей в пакете nodes.
    """
    
    _registry: Dict[str, Type['BaseNode']] = {}
    
    @classmethod
    def register(cls, node_type: str):
        """Декоратор для регистрации типа узла."""
        def wrapper(node_class: Type['BaseNode']):
            if node_type in cls._registry:
                # Разрешаем повторную регистрацию того же класса
                if cls._registry[node_type] is not node_class:
                    raise ValueError(
                        f"Тип '{node_type}' уже зарегистрирован классом "
                        f"{cls._registry[node_type].__name__}"
                    )
                # Если класс тот же — просто возвращаем (для reload)
                return node_class
            
            cls._registry[node_type] = node_class
            node_class.node_type = node_type
            return node_class
        return wrapper
    
    @classmethod
    def create(cls, node_type: str, **kwargs) -> 'BaseNode':
        """Фабричный метод создания узла по типу."""
        if node_type not in cls._registry:
            available = ', '.join(sorted(cls._registry.keys()))
            raise ValueError(
                f"Неизвестный тип узла: '{node_type}'. "
                f"Доступные типы: {available}"
            )
        return cls._registry[node_type](**kwargs)
    
    @classmethod
    def get_types(cls) -> List[str]:
        """Получить список зарегистрированных типов."""
        return list(cls._registry.keys())
    
    @classmethod
    def get_class(cls, node_type: str) -> Optional[Type['BaseNode']]:
        """Получить класс узла по типу."""
        return cls._registry.get(node_type)
    
    @classmethod
    def is_registered(cls, node_type: str) -> bool:
        """Проверяет, зарегистрирован ли тип."""
        return node_type in cls._registry
    
    @classmethod
    def get_all_classes(cls) -> Dict[str, Type['BaseNode']]:
        """Получить словарь всех зарегистрированных типов и классов."""
        return dict(cls._registry)
    
    @classmethod
    def reset(cls):
        """Сбрасывает реестр. Только для тестов!"""
        cls._registry.clear()