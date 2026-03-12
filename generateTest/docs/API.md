<COMPRESSED>
# API документация TestGen

## Оглавление
- [Модель](#модель)
- [testgen.py — движок генерации](#testgenpy)
- [run.py — форматирование и вывод](#runpy)
- [Примеры](#примеры)

---

## Модель

Модель хранится в `src/model.json` — JSON-файл со следующей структурой:

```json
{
  "Название действия": {
    "init_states": ["Состояние1", "Состояние2"],
    "final_states": ["КонечноеСостояние1"],
    "b_value": 5
  }
}
```

### Поля:
- **init_states** — начальные состояния, необходимые для выполнения действия
- **final_states** — конечные состояния, создаваемые после выполнения
- **b_value** — натуральное число 1–10 (вес для QG и RANDOM)

---

## testgen.py

### `load_model(path: str = MODEL_PATH) -> dict`
Загружает модель из JSON-файла.

### `build_states(model_data: dict) -> dict`
Строит словарь состояний: какие действия приводят к каждому состоянию.

### `can_add_action(path: List[str], action: str) -> bool`
Проверяет, можно ли добавить действие в путь (< 2 повторов).

### `get_ways_to_action(action_name, visited_actions, rounds, model_data, states_data) -> List[List[str]]`
Находит все возможные пути к действию.

**Параметры:**
- `action_name` — название действия
- `visited_actions` — множество посещённых действий (для предотвращения циклов)
- `rounds` — режим генерации: `ALL` | `QG` | `RANDOM`
- `model_data` — модель (если None — глобальная)
- `states_data` — состояния (если None — глобальные)

### `get_ways_to_state(state_name, visited_actions, rounds, model_data, states_data) -> List[List[str]]`
Находит все пути к состоянию.

**Параметры:** аналогично `get_ways_to_action`.

**Логика по режимам:**
- `ALL` — возвращает пути через все действия, создающие состояние
- `QG` — выбирает действие с максимальным `b_value`
- `RANDOM` — взвешенный случайный выбор по `b_value`

### `generate_cases_for_actions(actions, rounds, model_data) -> dict`
Генерирует тест-кейсы для списка действий.

**Параметры:**
- `actions: List[str]` — список действий
- `rounds: str` — `ALL` | `QG` | `RANDOM` (по умолчанию `ALL`)
- `model_data: dict | None` — модель (если None — глобальная из model.json)

**Возвращает:** `{action_name: [[step1, step2, ...], ...], ...}`

---

## run.py

### `format_test_case(case, action_name, test_structure, case_index, passage, model_data) -> List[str]`
Форматирует один тест-кейс.

**Параметры:**
- `case` — путь (список действий)
- `action_name` — целевое действие
- `test_structure` — `LEAF` | `BRANCH` | `TREE`
- `case_index` — порядковый номер сценария
- `passage` — `NONE` | `API` | `UI` | `UI_FULL` | `MANUAL` | `MANUAL_FULL`
- `model_data` — модель (для получения final_states)

### `format_test_suites_text(cases_dict, test_structure, passage, model_data) -> str`
Форматирует все кейсы в текстовую строку.

### `print_test_suites(cases_dict, test_structure, passage, model_data) -> int`
Выводит кейсы в stdout. Возвращает количество сценариев.

### `generate_and_format(actions, rounds, test_structure, passage, model_data) -> str`
Генерирует кейсы + форматирует в текст (комбинация testgen + форматирования).

### `get_step_channel(passage, step_index, total_steps) -> str | None`
Возвращает канал шага (API/UI/MANUAL) в зависимости от passage и позиции шага.

### `main()`
CLI: демонстрация всех 9 комбинаций (3 rounds × 3 test_structure).

### `run_server(port=8765)`
Запуск HTTP-сервера. Принимает `POST /generate` с JSON:
```json
{
  "model": {...},
  "actions": ["Действие1", "Действие2"],
  "rounds": "ALL",
  "test_structure": "TREE",
  "passage": "UI"
}
```
Возвращает `{"text": "...сгенерированные кейсы..."}`.

---

## Примеры

### CLI
```bash
# Все режимы
python3 run.py

# HTTP-сервер
python3 run.py --serve
```

### Python API
```python
from src.testgen import generate_cases_for_actions, load_model

model = load_model('src/model.json')

# QG: один оптимальный путь на каждое действие
cases = generate_cases_for_actions(
    list(model.keys()),
    rounds='QG',
    model_data=model
)

# Форматирование
from run import format_test_suites_text
text = format_test_suites_text(
    cases,
    test_structure='TREE',
    passage='UI',
    model_data=model
)
print(text)
```

### Проверка ограничений
```python
from src.testgen import can_add_action

path = ["Действие1", "Действие2", "Действие1"]
can_add_action(path, "Действие1")  # False (уже 2 раза)
can_add_action(path, "Действие3")  # True
```
</COMPRESSED>