DESCRIPTION = "Создание таблицы состояния квиза"

def up(driver):
    query = """
    CREATE TABLE IF NOT EXISTS quiz_state (
        user_id Uint64, 
        question_index Uint64,
        amount Uint64,
        PRIMARY KEY (`user_id`)
    );
    """
    driver.execute_scheme(query)