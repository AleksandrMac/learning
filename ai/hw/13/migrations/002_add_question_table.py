DESCRIPTION = "Создание таблицы вопросов"

def up(driver):
    query = """
    CREATE TABLE IF NOT EXISTS questions (
        question_id Uint64,
        quest Json,
        PRIMARY KEY (question_id)
    );
    """
    driver.execute_scheme(query)