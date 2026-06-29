# visualize_all.py
"""Скрипт для визуализации графа во всех форматах."""
import sys
from pathlib import Path
from graph.storage import GraphStorage
from graph.visualization import GraphVisualizer


def main():
    input_file = sys.argv[1] if len(sys.argv) > 1 else "output/graph.json"
    
    if not Path(input_file).exists():
        print(f"❌ Файл не найден: {input_file}")
        sys.exit(1)
    
    print(f"📂 Загружаем граф из {input_file}...")
    graph = GraphStorage.load_json(input_file)
    print(f"   Узлов: {len(graph.nodes)}, Рёбер: {len(graph.edges)}")
    
    # 1. DOT файл
    dot_path = "output/graph.dot"
    GraphVisualizer.to_dot(graph, dot_path)
    print(f"✅ DOT: {dot_path}")
    
    # 2. PNG (если graphviz установлен)
    try:
        import subprocess
        subprocess.run(
            ['dot', '-Tpng', dot_path, '-o', 'output/graph.png'],
            check=True, capture_output=True
        )
        print(f"✅ PNG: output/graph.png")
    except FileNotFoundError:
        print("⚠️  Graphviz не установлен — пропуск PNG")
    
    # 3. Интерактивный HTML
    try:
        from visualize_interactive import render_interactive
        render_interactive(graph, "output/graph.html")
    except ImportError:
        print("⚠️  pyvis не установлен — пропуск HTML")
    
    print("\n🎉 Готово!")
    print("   Откройте output/graph.html в браузере для интерактивного просмотра")


if __name__ == "__main__":
    main()