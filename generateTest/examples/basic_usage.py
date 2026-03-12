#!/usr/bin/env python3
"""
Пример использования TestGen для генерации тест-кейсов.
"""

import sys
import os

# Добавляем src в путь для импорта
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.testgen import generate_cases_for_actions, print_test_suites, model

def main():
    """Основная функция примера."""
    print("=" * 80)
    print("ПРИМЕР ИСПОЛЬЗОВАНИЯ TESTGEN")
    print("=" * 80)
    print()
    
    # Показать все действия в модели
    all_actions = list(model.keys())
    print(f"Всего действий в модели: {len(all_actions)}")
    print(f"Действия: {', '.join(all_actions)}")
    print()
    
    # Пример 1: Генерация для всех действий
    print("Пример 1: Генерация тест-кейсов для всех действий")
    print("-" * 60)
    
    all_cases = generate_cases_for_actions(all_actions, verbose=False)
    
    # Вывести статистику
    total_scenarios = sum(len(cases) for cases in all_cases.values())
    print(f"Сгенерировано тест-сценариев: {total_scenarios}")
    print()
    
    # Пример 2: Генерация для конкретных действий
    print("Пример 2: Генерация для конкретных действий")
    print("-" * 60)
    
    specific_actions = ["Оформить рассрочку", "Купить товар"]
    specific_cases = generate_cases_for_actions(specific_actions, verbose=False)
    
    for action in specific_actions:
        if action in specific_cases:
            print(f"{action}: {len(specific_cases[action])} сценариев")
    print()
    
    # Пример 3: Полный вывод тест-сьютов
    print("Пример 3: Полные тест-сьюты для 'Оформить рассрочку'")
    print("-" * 60)
    print()
    
    if "Оформить рассрочку" in all_cases:
        cases = all_cases["Оформить рассрочку"]
        print(f"Функциональность: \"Оформить рассрочку\"")
        print()
        
        for i, case in enumerate(cases[:2], 1):  # Показываем только первые 2
            print(f"Сценарий {i} Оформить рассрочку")
            for step in case:
                print(f"Когда {step}")
            print(f"Когда Оформить рассрочку")
            print()
    
    print("=" * 80)
    print("Пример завершен!")
    print("Для полного вывода всех тест-сьютов запустите:")
    print("  python src/testgen.py")

if __name__ == "__main__":
    main()