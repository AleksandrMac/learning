# Пример полного использования
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from parsers.main_document_parser import MainDocumentParser
from parsers.amendment_document_parser import AmendmentDocumentParser
from graph.builder import GraphBuilder
from graph.storage import GraphStorage
from graph.queries import GraphQueries


# ═══════════════════════════════════════════════════════
# 1. Парсим основной документ
# ═══════════════════════════════════════════════════════

# /home/aleksandr/development/aleksandrMac/learning/ai/practic/2/tests/fixtures/main_document_sample.md
main_text = Path("tests/fixtures/main_document_sample.md").read_text(encoding='utf-8')
main_parser = MainDocumentParser()
main_nodes = main_parser.parse(main_text)

print(f"Основной документ: {len(main_nodes)} узлов верхнего уровня")


# ═══════════════════════════════════════════════════════
# 2. Парсим документы-изменения
# ═══════════════════════════════════════════════════════
# /home/aleksandr/development/aleksandrMac/learning/ai/practic/2/tests/fixtures/amendment_document_sample.md
amendment_text = Path("tests/fixtures/amendment_document_sample.md").read_text(encoding='utf-8')

amendment_parser = AmendmentDocumentParser()
amendment_nodes = amendment_parser.parse(amendment_text)

print(f"Документ изменений: {len(amendment_nodes)} amendments")


# ═══════════════════════════════════════════════════════
# 3. Строим граф из обоих типов узлов
# ═══════════════════════════════════════════════════════

builder = GraphBuilder()

# 🔑 Передаём ОБА списка узлов
all_nodes = main_nodes + amendment_nodes
graph = builder.build(all_nodes, document_title="Методика № 421/пр")

print(f"\nГраф построен:")
print(f"  Узлов: {len(graph.nodes)}")
print(f"  Рёбер: {len(graph.edges)}")


# ═══════════════════════════════════════════════════════
# 4. Сохраняем граф
# ═══════════════════════════════════════════════════════

GraphStorage.save_json(graph, "output/graph.json")
print(f"\nГраф сохранён в output/graph.json")


# ═══════════════════════════════════════════════════════
# 5. Запросы к графу
# ═══════════════════════════════════════════════════════

queries = GraphQueries(graph)

# 🔍 Пункт 14 с его изменениями
point_14_info = queries.get_point_with_amendments('14')

print(f"\n📍 Пункт 14:")
print(f"  Текст: {point_14_info['point'].text[:100]}...")
print(f"  Amendments: {len(point_14_info['amendments'])}")

for amend in point_14_info['amendments']:
    print(f"    - {amend.amendment_number}: {amend.action}")

# 🔍 Пункт 15 с изменениями
point_15_info = queries.get_point_with_amendments('15')

print(f"\n📍 Пункт 15:")
print(f"  Текст: {point_15_info['point'].text[:100]}...")
print(f"  Amendments: {len(point_15_info['amendments'])}")

for amend in point_15_info['amendments']:
    print(f"    - {amend.amendment_number}: {amend.action}")

# 🔍 Структура документа
structure = queries.get_document_structure()
print(f"\n📄 Структура документа:")
print(f"  {structure['title']}")
for child in structure.get('children', []):
    print(f"    └─ {child['type']}: {child.get('title') or child.get('number')}")

from graph.visualization import GraphVisualizer

GraphVisualizer.to_dot(graph, "output/graph.dot")