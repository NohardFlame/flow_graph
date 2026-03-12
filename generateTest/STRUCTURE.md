<COMPRESSED>
# Структура репозитория TestGen

## Дерево файлов
```
testgen/
├── src/
│   ├── testgen.py          # Движок генерации путей (Python)
│   └── model.json          # Модель действий по умолчанию (JSON)
├── ui/
│   ├── index.html          # Веб-интерфейс: редактор графа + Test Manager
│   ├── script.js           # Логика UI + JS-порт движка генерации
│   └── styles.css          # Стили UI
├── tests/
│   ├── test_basic.py       # Тесты can_add_action(), структуры модели
│   └── test_rounds.py      # Тесты режимов ALL/QG/RANDOM
├── docs/
│   ├── API.md              # API документация (Python)
│   ├── MODEL_JSON_SPEC.md  # Спецификация model.json v2
│   └── STRUCTURE_DOC.md    # Описание test_structure и passage
├── examples/
│   └── basic_usage.py      # Пример использования Python API
├── run.py                  # CLI, форматирование вывода, HTTP-сервер
├── Makefile                # make run / make test / make serve / make clean
├── requirements.txt        # Зависимости Python (нет внешних)
├── STRUCTURE.md            # Этот файл
└── README.md               # Основная документация
```

## Описание компонентов

### src/testgen.py — движок генерации путей
Содержит:
- `load_model(path)` — загрузка модели из JSON
- `build_states(model_data)` — построение словаря состояний
- `can_add_action(path, action)` — проверка ограничений (≤ 2 повтора)
- `get_ways_to_action(action_name, ..., rounds, model_data, states_data)` — поиск путей к действию
- `get_ways_to_state(state_name, ..., rounds, model_data, states_data)` — поиск путей к состоянию
- `generate_cases_for_actions(actions, rounds, model_data)` — генерация кейсов

### src/model.json — модель по умолчанию
JSON-файл в формате v2: содержит `model_actions`, `model_objects`, `model_connections`.
Подробная спецификация — см. [docs/MODEL_JSON_SPEC.md](docs/MODEL_JSON_SPEC.md).

### run.py — CLI + форматирование + HTTP-сервер
- `format_test_case(...)` — форматирование одного кейса (LEAF/BRANCH/TREE + passage)
- `format_test_suites_text(...)` — форматирование всех кейсов в текст
- `print_test_suites(...)` — вывод в stdout
- `generate_and_format(...)` — генерация + форматирование
- `main()` — CLI: демонстрация всех режимов
- `run_server(port)` — HTTP-сервер (`--serve`)

### ui/ — веб-интерфейс
- Редактор графа на Cytoscape.js (действия, состояния, связи)
- Модальное окно для создания/редактирования действий с полем b_value
- Test Manager: панель с выбором rounds / test_structure / passage
- Генерация тестов выполняется локально в JS (порт из Python)

### tests/
- `test_basic.py` — тесты `can_add_action()`, структуры модели
- `test_rounds.py` — тесты режимов ALL, QG, RANDOM

## Использование
```bash
python3 run.py             # CLI: все режимы
python3 run.py --serve     # HTTP-сервер для UI
make run                   # то же через Makefile
make test                  # запуск тестов
make serve                 # HTTP-серв
</COMPRESSED>