"""Интерактивная визуализация графа через pyvis."""
from typing import Optional
from graph.models import DocumentGraph, NodeType, EdgeType


def render_interactive(graph: DocumentGraph, output_path: str = "output/graph.html") -> None:
    """
    Создать интерактивный HTML-файл с графом.
    
    Args:
        graph: граф документа
        output_path: путь для сохранения HTML
    """
    try:
        from pyvis.network import Network
    except ImportError:
        print("⚠️  pyvis не установлен. Установите: pip install pyvis")
        return
    
    net = Network(height="900px", width="100%", directed=True, notebook=False)
    net.barnes_hut(gravity=-80000, central_gravity=0.3, spring_length=250)
    
    # Цвета для типов узлов
    colors = {
        NodeType.DOCUMENT: '#4A90E2',
        NodeType.SECTION: '#7ED321',
        NodeType.POINT: '#F5A623',
        NodeType.PARAGRAPH: '#D8D8D8',
        NodeType.AMENDMENT: '#D0021B',
        NodeType.REPLACEMENT: '#FF6B9D',
        NodeType.FORMULA: '#BD10E0',
        NodeType.DEFINITION: '#9013FE',
    }
    
    # Размеры узлов
    sizes = {
        NodeType.DOCUMENT: 50,
        NodeType.SECTION: 35,
        NodeType.POINT: 25,
        NodeType.PARAGRAPH: 15,
        NodeType.AMENDMENT: 30,
        NodeType.REPLACEMENT: 20,
    }
    
    # Добавляем узлы
    for node_id, node in graph.nodes.items():
        color = colors.get(node.type, '#CCCCCC')
        size = sizes.get(node.type, 20)
        label = _get_short_label(node)
        title = _get_tooltip(node)
        
        shape = 'box' if node.type == NodeType.AMENDMENT else 'dot'
        
        net.add_node(
            node_id,
            label=label,
            title=title,
            color=color,
            size=size,
            shape=shape,
            font={'size': 12, 'color': '#333333'}
        )
    
    # Добавляем рёбра
    edge_colors = {
        EdgeType.CONTAINS: '#000000',
        EdgeType.AMENDS: '#FF0000',
        EdgeType.REFERENCES: '#0000FF',
        EdgeType.SUPERSEDES: '#00FF00',
        EdgeType.DEFINES: '#9C27B0',
        EdgeType.USES_TERM: '#9C27B0',
    }
    
    for edge in graph.edges:
        color = edge_colors.get(edge.type, '#999999')
        label = edge.type.value
        
        net.add_edge(
            edge.source_id,
            edge.target_id,
            color=color,
            title=label,
            label=label,
            arrows='to'
        )
    
    # Добавляем легенду
    _add_legend(net)
    
    # Сохраняем
    net.save_graph(output_path)
    print(f"✅ Интерактивный граф сохранён: {output_path}")
    print(f"   Откройте в браузере для просмотра")


def _get_short_label(node) -> str:
    """Короткая метка для узла."""
    if node.type == NodeType.DOCUMENT:
        return f"📄 {node.title[:25]}"
    elif node.type == NodeType.SECTION:
        title = getattr(node, 'title', '') or ''
        return f"§ {title[:25]}"
    elif node.type == NodeType.POINT:
        return f"¶{node.number}"
    elif node.type == NodeType.PARAGRAPH:
        return f"¶{node.number}"
    elif node.type == NodeType.AMENDMENT:
        return f"🔧#{node.amendment_number}"
    elif node.type == NodeType.REPLACEMENT:
        old = (node.old_text or '')[:10]
        new = (node.new_text or '')[:10]
        if old and new:
            return f"↻{old}→{new}"
        return "↻"
    return str(node.id)[:15]


def _get_tooltip(node) -> str:
    """Текст при наведении на узел."""
    parts = [f"<b>{node.type.value}</b>"]
    
    if hasattr(node, 'number') and node.number:
        parts.append(f"Номер: {node.number}")
    
    if hasattr(node, 'title') and node.title:
        parts.append(f"Заголовок: {node.title}")
    
    if hasattr(node, 'text') and node.text:
        text_preview = node.text[:300].replace('<', '&lt;').replace('>', '&gt;')
        parts.append(f"<hr><i>{text_preview}...</i>")
    
    if hasattr(node, 'action') and node.action:
        parts.append(f"Действие: {node.action}")
    
    if hasattr(node, 'old_text') and node.old_text:
        parts.append(f"<hr>Было: <i>{node.old_text[:100]}</i>")
    
    if hasattr(node, 'new_text') and node.new_text:
        parts.append(f"Стало: <i>{node.new_text[:100]}</i>")
    
    return "<br>".join(parts)


def _add_legend(net: 'Network') -> None:
    """Добавить легенду в виде узлов-подписей."""
    legend_items = [
        (NodeType.DOCUMENT, "Документ"),
        (NodeType.SECTION, "Раздел"),
        (NodeType.POINT, "Пункт"),
        (NodeType.PARAGRAPH, "Абзац"),
        (NodeType.AMENDMENT, "Изменение"),
        (NodeType.REPLACEMENT, "Замена"),
    ]
    
    colors = {
        NodeType.DOCUMENT: '#4A90E2',
        NodeType.SECTION: '#7ED321',
        NodeType.POINT: '#F5A623',
        NodeType.PARAGRAPH: '#D8D8D8',
        NodeType.AMENDMENT: '#D0021B',
        NodeType.REPLACEMENT: '#FF6B9D',
    }
    
    y_pos = -500
    for node_type, label in legend_items:
        legend_id = f"__legend_{node_type.value}"
        net.add_node(
            legend_id,
            label=label,
            color=colors.get(node_type, '#CCCCCC'),
            size=15,
            shape='dot',
            fixed=True,
            x=-800,
            y=y_pos,
            font={'size': 14, 'color': '#000000'}
        )
        y_pos += 50


# Запуск как скрипт
if __name__ == "__main__":
    import sys
    from graph.storage import GraphStorage
    
    input_file = sys.argv[1] if len(sys.argv) > 1 else "output/graph_v2.json"
    output_file = sys.argv[2] if len(sys.argv) > 2 else "output/graph_v2.html"
    
    try:
        graph = GraphStorage.load_json(input_file)
        render_interactive(graph, output_file)
    except FileNotFoundError:
        print(f"❌ Файл не найден: {input_file}")
        sys.exit(1)