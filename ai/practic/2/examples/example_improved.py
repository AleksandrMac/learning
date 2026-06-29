import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from graph.builder import GraphBuilder
from graph.queries import GraphQueries
from graph.storage import GraphStorage

from parsers.main_document_parser import MainDocumentParser
from parsers.amendment_document_parser import AmendmentDocumentParser


main_text = Path("/home/aleksandr/development/aleksandrMac/learning/ai/practic/dd/data/md/minstroy_20200804_pr_421_data.md").read_text(encoding='utf-8')
amendment_text = Path("/home/aleksandr/development/aleksandrMac/learning/ai/practic/dd/data/md/minstroy_20220707_pr_557-421_data.md").read_text(encoding='utf-8')
# Парсим документы
main_paser, amendment_parser = MainDocumentParser(), AmendmentDocumentParser()
main_nodes, amendment_nodes =  main_paser.parse(main_text), amendment_parser.parse(amendment_text)

# Строим граф с версиями
builder = GraphBuilder()
graph = builder.build(main_nodes + amendment_nodes, 
                     document_title="Методика № 421/пр")

# Сохраняем
GraphStorage.save_json(graph, "output/graph_v2.json")

# 🔍 Запросы
queries = GraphQueries(graph)

# Пример 1: Получить все версии пункта 14
print("\n📋 Версии пункта 14:")
versions = queries.get_point_versions('14')
for v in versions:
    version_num = v.metadata.get('version', 1)
    amended_by = v.metadata.get('amended_by', 'original')
    print(f"  v{version_num}: {v.text[:50]}... (изменён: {amended_by})")

# Пример 2: История изменений пункта 15
print("\n📜 История пункта 15:")
history = queries.get_amendment_history('15')
for h in history:
    print(f"  Amendment {h['amendment_number']}: {h['action']}")
    if h['old_text']:
        print(f"    Было: {h['old_text'][:40]}...")
    if h['new_text']:
        print(f"    Стало: {h['new_text'][:40]}...")

# Пример 3: Полный контекст пункта 14
print("\n🔍 Полный контекст пункта 14:")
context = queries.get_point_with_context('14')
print(f"  Текущая версия: v{context['current'].metadata.get('version', 1)}")
print(f"  Всего версий: {len(context.get('versions', []))}")
print(f"  Изменений: {len(context.get('amendments', []))}")
print(f"  Ссылается на: {[r['point'].number for r in context.get('references_to', [])]}")
print(f"  Ссылаются: {[r['point'].number for r in context.get('references_from', [])]}")

# Пример 4: Визуализация версий
print("\n🌳 Дерево версий:")
for version in context.get('versions', []):
    v_num = version.metadata.get('version', 1)
    superseded_by = [n.number for n in context.get('superseded_by', []) 
                     if n.metadata.get('version', 1) == v_num + 1]
    
    arrow = " → " + ", ".join(superseded_by) if superseded_by else ""
    print(f"  v{v_num}{arrow}")