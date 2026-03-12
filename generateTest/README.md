<COMPRESSED>
# TestGen - Генератор тест-кейсов в формате BDD

## Описание
TestGen — инструмент для автоматической генерации тест-кейсов в формате BDD (Behavior Driven Development) на основе модели действий и состояний.

## Возможности
- Автоматическая генерация тест-сценариев из модели действий
- Три режима генерации путей: **ALL**, **QG**, **RANDOM**
- Три структуры проверок: **LEAF**, **BRANCH**, **TREE**
- Шесть режимов passage: **API**, **UI**, **UI_FULL**, **MANUAL**, **MANUAL_FULL**, **NONE**
- Проверка ограничений (действие не повторяется более 2 раз)
- Веб-интерфейс (UI) для визуального редактирования модели и генерации тестов
- HTTP-сервер для интеграции UI с генератором
- Модель хранится в JSON-файле

## Структура репозитория
```
testgen/
├── src/
│   ├── testgen.py          # Движок генерации путей
│   └── model.json          # Модель действий (JSON)
├── ui/
│   ├── index.html          # Веб-интерфейс
│   ├── script.js           # Логика UI + движок генерации (JS-порт)
│   └── styles.css          # Стили
├── tests/
│   ├── test_basic.py       # Базовые тесты
│   └── test_rounds.py      # Тесты режимов генерации
├── docs/
│   ├── API.md              # API документация
│   └── STRUCTURE_DOC.md    # Описание test_structure и passage
├── examples/
│   └── basic_usage.py      # Пример использования
├── run.py                  # CLI + форматирование + HTTP-сервер
├── Makefile                # Утилиты
├── requirements.txt        # Зависимости
├── STRUCTURE.md            # Описание структуры репозитория
└── README.md               # Этот файл
```

## Быстрый старт

### CLI
```bash
# Генерация тестов для всех действий (все режимы)
python3 run.py

# HTTP-сервер для UI
python3 run.py --serve
```

### Веб-интерфейс
1. Запустить сервер: `python3 run.py --serve`
2. Открыть в браузере: **http://localhost:8765** (или путь к `ui/index.html`)
3. Загрузить модель (`src/model.json`) или создать с нуля
4. Нажать **Test Manager** — выбрать параметры и сгенерировать тесты

### Просмотр результатов run (flow_graph app)
Чтобы отобразить в TestGen результаты завершённого run из основного приложения:

1. **Запустите flow_graph app** (API с данными runs), например на порту 8000:
   ```bash
   # из корня flow_graph
   .venv\Scripts\python -m uvicorn app.api.main:app --reload
   ```
2. **Запустите TestGen UI**:
   ```bash
   cd generateTest
   make serve          # если установлен make (Linux/macOS)
   # Windows PowerShell (venv уже активирован из корня проекта):
   python run.py --serve
   # или явно указать venv из корня flow_graph:
   ..\.venv\Scripts\python.exe run.py --serve
   ```
3. Откройте **http://localhost:8765** в браузере.
4. Нажмите **Import from run**.
5. Введите **App base URL** (например `http://localhost:8000`) и **Run ID** (UUID run из приложения).
6. Нажмите OK — граф действий run отобразится в формате TestGen; можно править модель и генерировать тесты.

### Python API
```python
from src.testgen import generate_cases_for_actions, load_model, build_states

# Загрузка модели
model = load_model('src/model.json')

# Генерация путей
cases = generate_cases_for_actions(
    list(model.keys()),
    rounds='QG',
    model_data=model
)
```

## Параметры генерации

### Режим генерации путей (`rounds`)
| Режим | Описание |
|---|---|
| `ALL` | Все возможные пути |
| `QG` | Выбор действия с максимальным `b_value` на каждой развилке |
| `RANDOM` | Взвешенно-случайный выбор по `b_value` |

### Структура проверок (`test_structure`)
| Структура | Описание |
|---|---|
| `LEAF` | Один кейс — одна проверка |
| `BRANCH` | Все проверки последнего шага в конце |
| `TREE` | Проверки после каждого шага |

### Passage (`passage`)
| Passage | Промежуточные шаги | Последний шаг |
|---|---|---|
| `NONE` | без суффикса | без суффикса |
| `API` | (API) | (API) |
| `UI` | (API) | (UI) |
| `UI_FULL` | (UI) | (UI) |
| `MANUAL` | (API) | (MANUAL) |
| `MANUAL_FULL` | (MANUAL) | (MANUAL) |

## Формат модели (JSON)
```json
{
  "Оформить рассрочку": {
    "init_states": ["Кошелек активен", "Возможна рассрочка"],
    "final_states": ["Оформлена рассрочка"],
    "b_value": 5
  }
}
```

## Формат вывода
```gherkin
Функциональность: "Купить товар"

Сценарий 1 Купить товар
Когда Активировать кошелек (API)
Тогда Кошелек активен (API)
Когда Оформить рассрочку (API)
Тогда Оформлена рассрочка (API)
Когда Купить товар (UI)
Тогда Создан транш (UI)
```

## Требования
- Python 3.7+
- Без внешних зависимостей

## Лицензия
MIT Li
</COMPRESSED>