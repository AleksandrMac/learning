# tests/test_rag/test_embeddings.py

from sentence_transformers import SentenceTransformer
import numpy as np

def test_sentence_transformers_import():
    """Проверяем, что sentence-transformers работает."""
    model = SentenceTransformer('sentence-transformers/LaBSE', device='cpu')
    
    # Тестируем кодирование
    texts = ["Пункт 10 о сметной стоимости", "Накладные расходы на реставрацию"]
    embeddings = model.encode(texts, convert_to_numpy=True)
    
    assert embeddings.shape == (2, 768)  # LaBSE возвращает 768-мерные векторы
    assert not np.isnan(embeddings).any()