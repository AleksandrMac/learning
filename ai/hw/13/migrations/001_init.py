DESCRIPTION = "Создание таблицы schema_version"

def up(driver):
    query = """
    CREATE TABLE IF NOT EXISTS schema_version (
        version Uint64,
        applied_at Timestamp,
        description Utf8,
        PRIMARY KEY (version)
    );
    """
    driver.execute_scheme(query)