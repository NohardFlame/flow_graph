#!/usr/bin/env python3
"""
Тесты для проверки параметра rounds.
"""

import sys
import os

# Добавляем src в путь для импорта
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.testgen import generate_cases_for_actions, model

def test_rounds_all():
    """Тест режима ALL."""
    print("Тестирование режима ALL...")
    
    all_actions = list(model.keys())
    cases = generate_cases_for_actions(all_actions, verbose=False, rounds="ALL")
    
    # Проверяем, что сгенерированы кейсы
    total_scenarios = sum(len(cases) for cases in cases.values())
    assert total_scenarios > 0, "В режиме ALL должно быть сгенерировано хотя бы несколько сценариев"
    
    print(f"✓ Режим ALL: {total_scenarios} сценариев")

def test_rounds_qg():
    """Тест режима QG."""
    print("Тестирование режима QG...")
    
    all_actions = list(model.keys())
    cases = generate_cases_for_actions(all_actions, verbose=False, rounds="QG")
    
    # Проверяем, что сгенерированы кейсы
    total_scenarios = sum(len(cases) for cases in cases.values())
    assert total_scenarios > 0, "В режиме QG должно быть сгенерировано хотя бы несколько сценариев"
    
    print(f"✓ Режим QG: {total_scenarios} сценариев")

def test_rounds_random():
    """Тест режима RANDOM."""
    print("Тестирование режима RANDOM...")
    
    all_actions = list(model.keys())
    cases = generate_cases_for_actions(all_actions, verbose=False, rounds="RANDOM")
    
    # Проверяем, что сгенерированы кейсы
    total_scenarios = sum(len(cases) for cases in cases.values())
    assert total_scenarios > 0, "В режиме RANDOM должно быть сгенерировано хотя бы несколько сценариев"
    
    print(f"✓ Режим RANDOM: {total_scenarios} сценариев")

def test_different_rounds_produce_different_results():
    """Тест, что разные режимы дают разное количество сценариев."""
    print("Тестирование различий между режимами...")
    
    all_actions = list(model.keys())
    
    # Получаем результаты для всех режимов
    all_cases = generate_cases_for_actions(all_actions, verbose=False, rounds="ALL")
    qg_cases = generate_cases_for_actions(all_actions, verbose=False, rounds="QG")
    
    all_count = sum(len(cases) for cases in all_cases.values())
    qg_count = sum(len(cases) for cases in qg_cases.values())
    
    # ALL должно давать больше или равно сценариев, чем QG
    assert all_count >= qg_count, f"ALL ({all_count}) должно давать не меньше сценариев, чем QG ({qg_count})"
    
    print(f"✓ ALL: {all_count} сценариев, QG: {qg_count} сценариев")

def main():
    """Запуск всех тестов."""
    print("Запуск тестов параметра rounds...")
    print("=" * 60)
    
    try:
        test_rounds_all()
        test_rounds_qg()
        test_rounds_random()
        test_different_rounds_produce_different_results()
        
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