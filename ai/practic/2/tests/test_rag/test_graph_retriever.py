import pytest
from rag.retriever import GraphRetriever
from graph.models import DocumentGraph
from graph.storage import GraphStorage

@pytest.fixture
def graph() -> DocumentGraph:
    """
    Собирает DocumentGraph из тестовых сэмплов.
    """
    doc_graph = GraphStorage.load_json("output/graph_v2.json")
    
    return doc_graph

def test_retriever_semantic_search(graph: DocumentGraph):
    """Тест семантического поиска."""
    retriever = GraphRetriever(graph)
    
    results = retriever.semantic_search("Как считать накладные расходы?", top_k=2)
    
    assert len(results) > 0
    assert results[0]['score'] > 0.5
    assert results[0]['node'].type.value in ['point', 'paragraph']


def test_retriever_context_with_history(graph: DocumentGraph):
    """Тест получения контекста с историей."""
    retriever = GraphRetriever(graph)
    
    # Предположим, пункт 10 менялся поправкой 7
    context = retriever.retrieve_context("пункт 10", top_k=1, include_history=True)
    
    assert "Пункт 10" in context
    # Если есть история, она должна быть в контексте
    if "История изменений" in context:
        assert "Поправка" in context


def test_retriever_point_history(graph: DocumentGraph):
    """Тест получения истории изменений пункта."""
    history = graph.get_point_history("point:10")
    
    # Если пункт 10 менялся, история не пустая
    if history:
        assert 'amendment_id' in history[0]
        assert 'action' in history[0]