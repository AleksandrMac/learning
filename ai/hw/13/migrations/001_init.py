DESCRIPTION = "Создание таблицы schema_version"

def up(session):
    query = """
    CREATE TABLE IF NOT EXISTS schema_version (
        version Uint64,
        applied_at Timestamp,
        description Utf8,
        PRIMARY KEY (version)
    );
    """
    session.execute_scheme(query)