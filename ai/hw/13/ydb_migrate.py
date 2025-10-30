import os
import time
import importlib
import ydb
from dotenv import load_dotenv

MIGRATIONS_DIR = "migrations"
SCHEMA_VERSION_TABLE = "schema_version"

def get_applied_versions(session):
    query = f"SELECT version FROM `{SCHEMA_VERSION_TABLE}` ORDER BY version"
    result = session.transaction().execute(query, commit_tx=True)
    return {row.version for row in result[0].rows}

def apply_migration(session, version: int, module, description: str):
    print(f"Применяется миграция {version:03d}: {description}")
    module.up(session.driver)
    
    # Записываем в таблицу версий
    query = f"""
    UPSERT INTO `{SCHEMA_VERSION_TABLE}` (version, applied_at, description)
    VALUES ({version}, CAST({int(time.time() * 1_000_000)} AS Timestamp), '{description}');
    """
    session.transaction().execute(query, commit_tx=True)
    print(f"Миграция {version:03d} успешно применена.")

def run_migrations(endpoint: str, database: str):



    driver_config = ydb.DriverConfig(
        endpoint, database,
        # credentials=ydb.credentials_from_env_variables(),
    )

    driver = ydb.Driver(driver_config)
    driver.wait(timeout=10)
    
    with ydb.SessionPool(driver) as pool:
        # Убедимся, что таблица версий существует (миграция 001)
        try:
            pool.retry_operation_sync(lambda s: s.execute_scheme(
                f"CREATE TABLE IF NOT EXISTS `{SCHEMA_VERSION_TABLE}` (version Uint64, applied_at Timestamp, description Utf8, PRIMARY KEY (version));"
            ))
        except Exception as e:
            print(f"Ошибка при создании schema_version: {e}")

        print(os.listdir("."))
        applied = pool.retry_operation_sync(lambda s: get_applied_versions(s))
        migration_files = sorted(f for f in os.listdir(MIGRATIONS_DIR) if f.endswith('.py') and f[:3].isdigit())

        for filename in migration_files:
            version = int(filename[:3])
            if version in applied:
                print(f"Миграция {version:03d} уже применена — пропускаем.")
                continue

            mod_name = filename[:-3]
            mod = importlib.import_module(f"{MIGRATIONS_DIR}.{mod_name}")
            description = getattr(mod, "DESCRIPTION", "Без описания")
            pool.retry_operation_sync(lambda s: apply_migration(s, version, mod, description))

    driver.stop()

if __name__ == "__main__":
    load_dotenv()
    # Настройки подключения (можно вынести в .env)
    ENDPOINT = os.getenv("YDB_ENDPOINT")
    DATABASE = os.getenv("YDB_DATABASE")

    run_migrations(ENDPOINT, DATABASE)