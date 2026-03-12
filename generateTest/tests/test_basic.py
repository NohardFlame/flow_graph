#!/usr/bin/env python3
"""
Базовые тесты для TestGen.
"""

import sys
import os

# Добавляем src в путь для импорта
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.testgen import can_add_action, model

def test_can_add_action():
    """Тест функции can_add_action."""
    # Пустой путь - можно добавить
    assert can_add_action([], "Действие1") == True
    
    # Действие встречается 1 раз - можно добавить
    assert can_add_action(["Действие1", "Действие2"], "Действие1") == True
    
    # Действие встречается 2 раза - нельзя добавить
    assert can_add_action(["Действие1", "Действие2", "Действие1"], "Действие1") == False
    
    # Действие встречается 3 раза - нельзя добавить
    assert can_add_action(["Действие1", "Действие1", "Действие1"], "Действие1") == False
    
    print("✓ test_can_add_action пройден")

def test_model_structure():
    """Тест структуры модели."""
    # Проверяем, что модель не пустая
    assert len(model) > 0
    
    # Проверяем структуру каждого действия
    for action_name, action_data in model.items():
        assert "init_states" in action_data
        assert "final_states" in action_data
        assert "b_value" in action_data
        assert isinstance(action_data["b_value"], int)
        assert 1 <= action_data["b_value"] <= 10
    
    print(f"✓ test_model_structure пройден (проверено {len(model)} действий)")

def test_initial_actions():
    """Тест начальных действий (без init_states)."""
    initial_actions = []
    for action_name, action_data in model.items():
        if not action_data["init_states"]:
            initial_actions.append(action_name)
    
    # Проверяем, что есть начальные действия
    assert len(initial_actions) > 0
    
    print(f"✓ test_initial_actions пройден (найдено {len(initial_actions)} начальных действий)")

def main():
    """Запуск всех тестов."""
    print("Запуск тестов TestGen...")
    print("=" * 60)
    
    try:
        test_can_add_action()
        test_model_structure()
        test_initial_actions()
        
        print("=" * 60)
        print("Все тесты пройдены успешно! ✅")
        
    except AssertionError as e:
        print(f"Ошибка теста: {e}")
        return 1
    except Exception as e:
        print(f"Неожиданная ошибка: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())