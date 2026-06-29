import pytest
from nodes.registry import NodeRegistry
from nodes.concrete import (
    ParagraphNode, PointNode
)
from nodes.amendments import (
    AmendmentNode, ExcludeAmendmentNode, AddAmendmentNode,
    ReplaceWordsAmendmentNode, ReplaceAmendmentNode
)
from nodes.target import TargetAddress, TargetComponent, ComponentType

# 🔑 Важно: импортируем пакет целиком, чтобы сработали все @NodeRegistry.register
import nodes


class TestNodeRegistry:
    """Тесты реестра типов узлов."""
    
    def test_basic_types_registered(self):
        """Базовые типы узлов зарегистрированы после импорта пакета."""
        assert NodeRegistry.is_registered('paragraph')
        assert NodeRegistry.is_registered('point')
        assert NodeRegistry.is_registered('formula')
        assert NodeRegistry.is_registered('definition')
        assert NodeRegistry.is_registered('section')
    
    def test_amendment_types_registered(self):
        """Все типы amendments зарегистрированы."""
        assert NodeRegistry.is_registered('amendment')
        assert NodeRegistry.is_registered('amendment_exclude')
        assert NodeRegistry.is_registered('amendment_add')
        assert NodeRegistry.is_registered('amendment_replace_words')
        assert NodeRegistry.is_registered('amendment_replace')
    
    def test_create_paragraph_node(self):
        """Создание узла через реестр."""
        node = NodeRegistry.create(
            'paragraph',
            number='83',
            text='Сметная цена на эксплуатацию машин'
        )
        
        assert isinstance(node, ParagraphNode)
        assert node.number == '83'
        assert node.text == 'Сметная цена на эксплуатацию машин'
        assert node.node_type == 'paragraph'
    
    def test_create_amendment_exclude(self):
        """Создание специализированного amendment."""
        node = NodeRegistry.create(
            'amendment_exclude',
            text='исключить слова',
            old_text='старый текст',
            action='exclude'
        )
        
        assert isinstance(node, ExcludeAmendmentNode)
        assert node.old_text == 'старый текст'
        assert node.action == 'exclude'
    
    def test_create_unknown_type_raises_helpful_error(self):
        """Попытка создать неизвестный тип вызывает ошибку со списком доступных."""
        with pytest.raises(ValueError) as exc_info:
            NodeRegistry.create('unknown_type_xyz')
        
        error_msg = str(exc_info.value)
        assert 'unknown_type_xyz' in error_msg
        assert 'paragraph' in error_msg  # подсказка с доступными типами
        assert 'amendment_exclude' in error_msg
    
    def test_get_types(self):
        """Получение списка всех зарегистрированных типов."""
        types = NodeRegistry.get_types()
        assert 'paragraph' in types
        assert 'amendment_replace' in types
        assert len(types) >= 10  # все наши типы
    
    def test_get_class(self):
        """Получение класса узла по типу."""
        assert NodeRegistry.get_class('paragraph') is ParagraphNode
        assert NodeRegistry.get_class('point') is PointNode
        assert NodeRegistry.get_class('nonexistent') is None
    
    def test_duplicate_registration_same_class_allowed(self):
        """Повторная регистрация того же класса не вызывает ошибку (безопасно для reload)."""
        # Это не должно вызывать исключение
        NodeRegistry.register('paragraph')(ParagraphNode)
        assert NodeRegistry.is_registered('paragraph')
    
    def test_create_with_target_address(self):
        """Создание узла с вложенным объектом TargetAddress."""
        target = TargetAddress(components=[
            TargetComponent(ComponentType.POINT, '80'),
            TargetComponent(ComponentType.PARAGRAPH, '4')
        ])
        
        node = NodeRegistry.create(
            'amendment_replace_words',
            target=target,
            old_text='старое',
            new_text='новое'
        )
        
        assert node.target.to_path() == '80.para:4'
        assert node.old_text == 'старое'