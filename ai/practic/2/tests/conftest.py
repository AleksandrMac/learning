import pytest
from pathlib import Path


@pytest.fixture
def fixtures_dir():
    """Путь к директории с тестовыми данными."""
    return Path(__file__).parent / 'fixtures'


@pytest.fixture
def main_document_sample(fixtures_dir):
    """Пример основного документа."""
    return (fixtures_dir / 'main_document_sample.md').read_text(encoding='utf-8')


@pytest.fixture
def amendment_document_sample(fixtures_dir):
    """Пример документа изменений."""
    return (fixtures_dir / 'amendment_document_sample.md').read_text(encoding='utf-8')