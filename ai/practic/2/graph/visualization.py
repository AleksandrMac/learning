import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from graph.models import DocumentGraph, NodeType, EdgeType
from graph.storage import GraphStorage

class GraphVisualizer:
    """Визуализация графа."""
    
    @staticmethod
    def to_dot(graph: DocumentGraph, filepath: str) -> None:
        """Экспорт графа в DOT формат (Graphviz)."""
        lines = ['digraph DocumentGraph {']
        lines.append('  rankdir=TB;')
        lines.append('  node [shape=box, style=filled];')
        
        # Цвета для разных типов узлов
        colors = {
            NodeType.DOCUMENT: '#lightblue',
            NodeType.SECTION: '#lightgreen',
            NodeType.POINT: '#lightyellow',
            NodeType.PARAGRAPH: '#white',
            NodeType.AMENDMENT: '#lightcoral',
            NodeType.REPLACEMENT: '#lightpink',
        }
        
        # Узлы
        for node_id, node in graph.nodes.items():
            color = colors.get(node.type, '#white')
            label = GraphVisualizer._get_label(node)
            lines.append(f'  "{node_id}" [label="{label}", fillcolor="{color}"];')
        
        # Рёбра
        for edge in graph.edges:
            style = GraphVisualizer._get_edge_style(edge.type)
            lines.append(f'  "{edge.source_id}" -> "{edge.target_id}" [{style}];')
        
        lines.append('}')
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
    
    @staticmethod
    def _get_label(node) -> str:
        """Создать метку для узла."""
        if node.type == NodeType.DOCUMENT:
            return f"📄 {node.title}"
        elif node.type == NodeType.SECTION:
            return f"§ {node.title}"
        elif node.type == NodeType.POINT:
            return f"¶ {node.number}"
        elif node.type == NodeType.PARAGRAPH:
            return f"¶{node.number}"
        elif node.type == NodeType.AMENDMENT:
            return f"🔧 {node.amendment_number}\\n{node.action}"
        elif node.type == NodeType.REPLACEMENT:
            old = node.old_text[:20] if node.old_text else ''
            new = node.new_text[:20] if node.new_text else ''
            return f"↻ {old}→{new}"
        return str(node.id)
    
    @staticmethod
    def _get_edge_style(edge_type: EdgeType) -> str:
        """Стиль ребра."""
        styles = {
            EdgeType.CONTAINS: 'color=black',
            EdgeType.AMENDS: 'color=red, style=dashed, label="amends"',
            EdgeType.REFERENCES: 'color=blue, style=dotted, label="ref"',
            EdgeType.SUPERSEDES: 'color=green, style=dashed',
            EdgeType.DEFINES: 'color=purple',
            EdgeType.USES_TERM: 'color=purple, style=dotted',
        }
        return styles.get(edge_type, '')
    
if __name__ == "__main__":    
    graph = GraphStorage.load_json("output/graph.json")
    GraphVisualizer.to_dot(graph, "output/graph.dot")