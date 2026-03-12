#!/usr/bin/env python3
"""
Основной скрипт для запуска TestGen.
Содержит логику вывода тест-кейсов с поддержкой:
- структур проверок: LEAF / BRANCH / TREE
- режимов генерации путей: ALL / QG / RANDOM
- режима прохождения шагов (passage): API / UI / UI_FULL / MANUAL / MANUAL_FULL / NONE
"""

import json
import os
import random
import sys
import urllib.request
from typing import Dict, List, Literal, Optional, Tuple

# Добавляем src в путь для импорта
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from testgen import generate_cases_for_actions, model
from run_parser import parse_run_graph_to_model

TestStructureType = Literal["LEAF", "BRANCH", "TREE"]
PassageType = Literal["API", "UI", "UI_FULL", "MANUAL", "MANUAL_FULL", "NONE"]

RANDOM_SEED = 42
SEPARATOR_LONG = "=" * 80
SEPARATOR_MID = "-" * 60
SEPARATOR_SHORT = "-" * 40


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_final_states(action_name: str, model_data: Optional[dict] = None) -> List[str]:
    """Возвращает final_states действия из модели."""
    m = model_data if model_data is not None else model
    if action_name in m:
        return m[action_name].get("final_states", [])
    return []


def get_step_channel(passage: str, step_index: int, total_steps: int) -> Optional[str]:
    """Возвращает канал шага (API/UI/MANUAL) в зависимости от passage."""
    if passage == "NONE":
        return None
    if passage == "API":
        return "API"
    if passage == "UI_FULL":
        return "UI"
    if passage == "MANUAL_FULL":
        return "MANUAL"

    is_last_step = step_index == total_steps - 1
    if passage == "UI":
        return "UI" if is_last_step else "API"
    if passage == "MANUAL":
        return "MANUAL" if is_last_step else "API"
    return None


def _with_channel(text: str, channel: Optional[str]) -> str:
    return f"{text} ({channel})" if channel else text


def _append_when(lines: List[str], step: str, idx: int, total: int, passage: str) -> None:
    ch = get_step_channel(passage, idx, total)
    lines.append(f"Когда {_with_channel(step, ch)}")


def _append_then(lines: List[str], verification: str, idx: int, total: int, passage: str) -> None:
    ch = get_step_channel(passage, idx, total)
    lines.append(f"Тогда {_with_channel(verification, ch)}")


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------

def format_test_case(
    case: List[str],
    action_name: str,
    test_structure: str = "LEAF",
    case_index: int = 1,
    passage: str = "NONE",
    model_data: Optional[dict] = None,
) -> List[str]:
    """Форматирует один тест-кейс в зависимости от test_structure и passage."""
    lines: List[str] = []
    total = len(case)
    finals = _get_final_states(action_name, model_data)

    if test_structure == "LEAF":
        for vi, v in enumerate(finals, 1):
            lines.append(f'Сценарий {case_index}.{vi} {action_name} "{v}"')
            for si, step in enumerate(case):
                _append_when(lines, step, si, total, passage)
            _append_then(lines, v, total - 1, total, passage)
            lines.append("")

    elif test_structure == "BRANCH":
        lines.append(f"Сценарий {case_index} {action_name}")
        for si, step in enumerate(case):
            _append_when(lines, step, si, total, passage)
        for v in finals:
            _append_then(lines, v, total - 1, total, passage)
        lines.append("")

    elif test_structure == "TREE":
        lines.append(f"Сценарий {case_index} {action_name}")
        for si, step in enumerate(case):
            _append_when(lines, step, si, total, passage)
            if si < total - 1:
                for v in _get_final_states(step, model_data):
                    _append_then(lines, v, si, total, passage)
        for v in finals:
            _append_then(lines, v, total - 1, total, passage)
        lines.append("")

    return lines


# ---------------------------------------------------------------------------
# Output (text)
# ---------------------------------------------------------------------------

def format_test_suites_text(
    cases_dict: Dict[str, List[List[str]]],
    test_structure: str = "LEAF",
    passage: str = "NONE",
    model_data: Optional[dict] = None,
) -> str:
    """
    Форматирует тест-кейсы в строку. Используется и для консольного вывода,
    и для отправки результата в UI.
    """
    lines: List[str] = []
    scenario_counter = 1

    for action, cases in cases_dict.items():
        if not cases:
            continue
        for case in cases:
            case_lines = format_test_case(
                case=case,
                action_name=action,
                test_structure=test_structure,
                case_index=scenario_counter,
                passage=passage,
                model_data=model_data,
            )
            lines.extend(case_lines)
            scenario_counter += 1

    return "\n".join(lines)


def print_test_suites(
    cases_dict: Dict[str, List[List[str]]],
    test_structure: str = "LEAF",
    mode_name: str = "",
    passage: str = "NONE",
    model_data: Optional[dict] = None,
) -> int:
    """Выводит тест-кейсы в консоль и возвращает количество сценариев."""
    if mode_name:
        print(f"\n{mode_name}")
        print(f"Структура проверок: {test_structure}")
        print(f"Passage: {passage}")
        print(SEPARATOR_MID)

    text = format_test_suites_text(cases_dict, test_structure, passage, model_data)
    if text:
        print(text)

    total = 0
    for action, cases in cases_dict.items():
        for _ in cases:
            if test_structure == "LEAF":
                total += len(_get_final_states(action, model_data))
            else:
                total += 1
    return total


# ---------------------------------------------------------------------------
# High-level API (used by UI server / CLI)
# ---------------------------------------------------------------------------

def generate_and_format(
    model_data: dict,
    actions: List[str],
    rounds: str = "ALL",
    test_structure: str = "LEAF",
    passage: str = "NONE",
    seed: int = RANDOM_SEED,
) -> str:
    """
    Единая точка входа: принимает модель + параметры, возвращает готовый текст.
    Вызывается из UI и из CLI.
    """
    if rounds == "RANDOM":
        random.seed(seed)

    cases = generate_cases_for_actions(actions, rounds=rounds, model_data=model_data)
    return format_test_suites_text(cases, test_structure, passage, model_data)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def generate_and_print_mode(
    mode_name: str,
    rounds_type: str,
    test_structure: str,
    passage: str,
    all_actions: List[str],
) -> Tuple[dict, int]:
    """Генерация и вывод тест-кейсов для заданной комбинации параметров."""
    print(f"\n{mode_name}")
    print(f"Режим генерации: {rounds_type}")
    print(f"Структура проверок: {test_structure}")
    print(f"Passage: {passage}")
    print(SEPARATOR_MID)

    if rounds_type == "RANDOM":
        random.seed(RANDOM_SEED)

    cases = generate_cases_for_actions(all_actions, verbose=False, rounds=rounds_type)
    total = print_test_suites(cases, test_structure=test_structure, passage=passage)
    print(f"Итого сценариев: {total}")
    return cases, total


def main() -> None:
    """Запуск TestGen со всеми режимами и структурами проверок."""
    print(SEPARATOR_LONG)
    print("TESTGEN - Генератор тест-кейсов в формате BDD")
    print(SEPARATOR_LONG)

    all_actions = list(model.keys())
    print(f"Всего действий в модели: {len(all_actions)}")
    print(f"Действия: {', '.join(all_actions)}")
    print()

    test_structures = ["LEAF", "BRANCH", "TREE"]
    rounds_types = ["ALL", "QG", "RANDOM"]
    passages = ["NONE", "API", "UI", "UI_FULL", "MANUAL", "MANUAL_FULL"]

    print("ДЕМОНСТРАЦИЯ ВСЕХ РЕЖИМОВ, СТРУКТУР И PASSAGE:")
    print(SEPARATOR_LONG)

    demo_actions = ["Купить товар"]

    for ts in test_structures:
        print(f"\n{'=' * 60}")
        print(f"СТРУКТУРА ПРОВЕРОК: {ts}")
        print(f"{'=' * 60}")

        for p in passages:
            print(f"\nPassage: {p}")
            print(SEPARATOR_SHORT)

            for rt in rounds_types:
                print(f"\nРежим генерации: {rt}")
                print(f"Структура проверок: {ts}")
                print(f"Passage: {p}")
                print(SEPARATOR_SHORT)

                if rt == "RANDOM":
                    random.seed(RANDOM_SEED)

                cases = generate_cases_for_actions(demo_actions, verbose=False, rounds=rt)
                total = print_test_suites(cases, test_structure=ts, passage=p)
                print(f"Итого сценариев: {total}")
                print()


# ---------------------------------------------------------------------------
# HTTP server for UI
# ---------------------------------------------------------------------------

def run_server(port: int = 8765) -> None:
    """Простой HTTP-сервер: отдаёт ui/ как статику, GET /import-run, POST /generate."""
    from http.server import HTTPServer, SimpleHTTPRequestHandler
    from urllib.parse import parse_qs, urlparse

    ui_dir = os.path.join(os.path.dirname(__file__), "ui")

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=ui_dir, **kwargs)

        def do_GET(self):
            parsed = urlparse(self.path)
            if parsed.path == "/import-run":
                q = parse_qs(parsed.query)
                base_url = (q.get("base_url") or [""])[0].strip().rstrip("/")
                run_id = (q.get("run_id") or [""])[0].strip()
                if not base_url or not run_id:
                    self.send_response(400)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(
                        json.dumps(
                            {"error": "Missing base_url or run_id"},
                            ensure_ascii=False,
                        ).encode()
                    )
                    return
                url = f"{base_url}/runs/{run_id}/graph"
                try:
                    with urllib.request.urlopen(url, timeout=30) as resp:
                        run_graph = json.loads(resp.read().decode())
                except Exception as e:
                    self.send_response(502)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(
                        json.dumps(
                            {"error": f"Failed to fetch run graph: {e}"},
                            ensure_ascii=False,
                        ).encode()
                    )
                    return
                v1_model = parse_run_graph_to_model(run_graph)
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(v1_model, ensure_ascii=False).encode())
                return
            super().do_GET()

        def do_POST(self):
            if self.path == "/generate":
                length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(length))

                model_data = body.get("model", {})
                actions = body.get("actions", list(model_data.keys()))
                rounds = body.get("rounds", "ALL")
                test_structure = body.get("test_structure", "LEAF")
                passage = body.get("passage", "NONE")

                result_text = generate_and_format(
                    model_data=model_data,
                    actions=actions,
                    rounds=rounds,
                    test_structure=test_structure,
                    passage=passage,
                )

                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"text": result_text}, ensure_ascii=False).encode())
            else:
                self.send_error(404)

        def do_OPTIONS(self):
            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()

    server = HTTPServer(("", port), Handler)
    print(f"TestGen server running on http://localhost:{port}")
    server.serve_forever()


if __name__ == "__main__":
    if "--serve" in sys.argv:
        run_server()
    else:
        main()
