DESCRIPTION = "Создание таблицы вопросов"

def up(session):
    query = """
    CREATE TABLE IF NOT EXISTS questions (
        question_id Uint64,
        quest Json,
        PRIMARY KEY (question_id)
    );
    """
    session.execute_scheme(query)