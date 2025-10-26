# Список open-source инструментов для MVP «Помощник сметчика»

| Назначение | Инструмент | Почему подходит |
|-----------|-----------|-----------------|
| **PDF-парсинг** | [`pdfplumber`](https://github.com/jsvine/pdfplumber) + [`unstructured`](https://github.com/unstructured-io/unstructured) | Точный извлечение текста, таблиц, метаданных; поддержка многостраничных структур |
| **Улучшенный парсинг (layout-aware)** | [`marker`](https://github.com/VikParuchuri/marker) | Конвертирует PDF в Markdown с сохранением структуры — идеально для нормативов |
| **Векторные эмбеддинги** | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` | Быстро, точно, поддержка русского языка |
| **Векторное хранилище** | [Chroma](https://github.com/chroma-core/chroma) | Лёгкий, встраиваемый, не требует отдельного сервера |
| **RAG-фреймворк** | [LlamaIndex](https://github.com/run-llama/llama_index) или [LangChain](https://github.com/langchain-ai/langchain) | Готовые пайплайны для цитирования, гибкая настройка |
| **LLM для генерации ответов** | `NousResearch/Hermes-3-Llama-3.1-8B` (через Ollama) или `Qwen2.5-7B-Instruct` | Высокое качество на русском, работает локально на GTX 1660 Ti (в 4-bit через `llama.cpp` или `vLLM`) |
| **Backend** | [FastAPI](https://fastapi.tiangolo.com/) | Асинхронный, автоматическая документация, легко интегрируется с ML |
| **Экспорт в Excel** | `pandas` + `openpyxl` | Стандарт де-факто, поддержка форматирования |
| **UI (минималистичный)** | [Streamlit](https://streamlit.io/) или Telegram Bot API | Быстро собрать интерфейс за 1–2 дня |
| **Деплой** | Docker + `nginx` + `gunicorn` | Портабельность, простота развёртывания на VPS |
| **Мониторинг** | [Sentry](https://sentry.io/) (open-source self-hosted) | Отслеживание ошибок в API и парсере |

> ✅ Все инструменты — бесплатные, open-source, работают локально или в облаке.