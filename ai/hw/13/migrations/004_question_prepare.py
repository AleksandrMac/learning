DESCRIPTION = "Заполнение таблицы с вопросами"

def up(session):
    query = """
    UPSERT INTO questions (question_id, quest) VALUES
    (0, JSON(@@{"question": "Что такое Python?", "options":["Язык программирования", "Тип данных", "Музыкальный инструмент", "Змея на английском"], "correct_option": 0}@@)),
    (1, JSON(@@{"question": "Какой тип данных используется для хранения целых чисел?", "options": ["int", "float", "str", "natural"], "correct_option": 0}@@)),
    (2, JSON(@@{"question": "Какой символ используется для комментариев в Python?", "options": ["//", "#", "/*", "--"], "correct_option": 1}@@)),
    (3, JSON(@@{"question": "Какой тип данных в Python используется для хранения целых чисел?", "options": ["float", "str", "int", "bool"], "correct_option": 2}@@)),
    (4, JSON(@@{"question": "Что выведет код: print(2 ** 3)?", "options": ["6", "8", "9", "23"], "correct_option": 1}@@)),
    (5, JSON(@@{"question": "Какой метод списка добавляет элемент в конец?", "options": ["insert()", "append()", "push()", "add()"], "correct_option": 1}@@)),
    (6, JSON(@@{"question": "Что такое PEP 8?", "options": ["Инструмент для запуска Python-скриптов", "Официальный сайт языка Python", "Стилевое руководство по написанию кода на Python", "Версия интерпретатора Python"], "correct_option": 2}@@)),
    (7, JSON(@@{"question": "Какой модуль в Python используется для работы с регулярными выражениями?", "options": ["regex", "re", "regexp", "match"], "correct_option": 1}@@)),
    (8, JSON(@@{"question": "Что означает ''IDE'' в программировании?", "options": ["Интерактивная динамическая среда", "Интегрированная среда разработки", "Интерпретатор данных и ошибок", "Инструмент для деплоя приложений"], "correct_option": 1}@@)),
    (9, JSON(@@{"question": "Как создать виртуальное окружение в Python?", "options": ["python -m venv myenv", "pip install virtualenv", "python --create-env", "venv new"], "correct_option": 0}@@));
    """
    session.transaction().execute(query, commit_tx=True)