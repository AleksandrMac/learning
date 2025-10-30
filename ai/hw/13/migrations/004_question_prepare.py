DESCRIPTION = "Заполнение таблицы с вопросами"

def up(driver):
    query = """
    UPSERT INTO question (question_id, quest) VALUES
    (0, CAST('{"question": "Что такое Python?", "options":["Язык программирования", "Тип данных", "Музыкальный инструмент", "Змея на английском"], "correct_option": 0}' AS Json)),
    (1, CAST('{"question": "Какой тип данных используется для хранения целых чисел?", "options": ["int", "float", "str", "natural"], "correct_option": 0}' AS Json)),
    (2, CAST('{"question": "Какой символ используется для комментариев в Python?", "options": ["//", "#", "/*", "--"], "correct_option": 1}' AS Json)),
    (3, CAST('{"question": "Какой тип данных в Python используется для хранения целых чисел?", "options": ["float", "str", "int", "bool"], "correct_option": 2}' AS Json)),
    (4, CAST('{"question": "Что выведет код: print(2 ** 3)?", "options": ["6", "8", "9", "23"], "correct_option": 1}' AS Json)),
    (5, CAST('{"question": "Какой метод списка добавляет элемент в конец?", "options": ["insert()", "append()", "push()", "add()"], "correct_option": 1}' AS Json)),
    (6, CAST('{"question": "Что такое PEP 8?", "options": ["Инструмент для запуска Python-скриптов", "Официальный сайт языка Python", "Стилевое руководство по написанию кода на Python", "Версия интерпретатора Python"], "correct_option": 2}' AS Json)),
    (7, CAST('{"question": "Какой модуль в Python используется для работы с регулярными выражениями?", "options": ["regex", "re", "regexp", "match"], "correct_option": 1}' AS Json)),
    (8, CAST('{"question": "Что означает \'IDE\' в программировании?", "options": ["Интерактивная динамическая среда", "Интегрированная среда разработки", "Интерпретатор данных и ошибок", "Инструмент для деплоя приложений"], "correct_option": 1}' AS Json)),
    (9, CAST('{"question": "Как создать виртуальное окружение в Python?", "options": ["python -m venv myenv", "pip install virtualenv", "python --create-env", "venv new"], "correct_option": 0}' AS Json));
    """
    driver.execute_scheme(query)