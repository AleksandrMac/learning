# graph/storage.py
import json
from pathlib import Path
from .models import DocumentGraph


class GraphStorage:
    """Сохранение и загрузка графа."""
    
    @staticmethod
    def save_json(graph: DocumentGraph, filepath: str) -> None:
        """Сохранить граф в JSON."""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(graph.to_dict(), f, ensure_ascii=False, indent=2, default=str)
    
    @staticmethod
    def load_json(filepath: str) -> DocumentGraph:
        """Загрузить граф из JSON."""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return DocumentGraph.from_dict(data)