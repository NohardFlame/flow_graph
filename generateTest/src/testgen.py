#!/usr/bin/env python3
"""
TestGen - Генератор тест-кейсов в формате BDD
Чистая версия без вывода - только логика генерации путей.
"""

import json
import os
import random
from typing import Literal, Dict, List, Optional

RoundType = Literal["ALL", "QG", "RANDOM"]

MODEL_PATH = os.path.join(os.path.dirname(__file__), "model.json")

MAX_ACTION_REPEATS = 2


def can_add_action(path: List[str], action: str) -> bool:
    """
    Проверяет, можно ли добавить действие в путь.
    Действие можно добавить, если оно встречается в пути менее MAX_ACTION_REPEATS раз.
    """
    return path.count(action) < MAX_ACTION_REPEATS


def _v2_to_v1(raw: dict) -> dict:
    """Convert v2 model (model_actions, model_objects, model_connections) to v1 (action_name -> init_states, final_states)."""
    if "model_actions" not in raw:
        return raw  # already v1 or unknown

    actions_list = raw.get("model_actions") or []
    objects_list = raw.get("model_objects") or []
    connections_list = raw.get("model_connections") or []

    def action_display_name(a: dict) -> str:
        parts = [
            a.get("action_actor"),
            a.get("action_action"),
            a.get("action_place"),
        ]
        return " ".join(p for p in parts if p).strip() or a.get("action_id", "")

    def state_display_name(obj: dict, st: dict) -> str:
        obj_name = obj.get("object_name") or ""
        st_name = st.get("state_name") or ""
        return " ".join(p for p in (obj_name, st_name) if p).strip() or (obj.get("object_id", "") + st.get("state_id", ""))

    action_id_to_name: Dict[str, str] = {}
    for a in actions_list:
        aid = a.get("action_id")
        if aid:
            action_id_to_name[aid] = action_display_name(a)

    composite_to_name: Dict[str, str] = {}
    for obj in objects_list:
        oid = obj.get("object_id", "")
        for st in obj.get("resource_state") or []:
            sid = st.get("state_id", "")
            composite = oid + sid
            composite_to_name[composite] = state_display_name(obj, st)

    v1: Dict[str, Dict[str, List[str]]] = {}
    for name in action_id_to_name.values():
        if name not in v1:
            v1[name] = {"init_states": [], "final_states": [], "b_value": 1}

    for c in connections_list:
        out_id = c.get("connection_out", "")
        in_id = c.get("connection_in", "")
        out_name = action_id_to_name.get(out_id) or composite_to_name.get(out_id)
        in_name = action_id_to_name.get(in_id) or composite_to_name.get(in_id)
        if out_name and in_name:
            if out_id in action_id_to_name and in_id in composite_to_name:
                v1[out_name]["final_states"].append(in_name)
            elif out_id in composite_to_name and in_id in action_id_to_name:
                if in_name not in v1:
                    v1[in_name] = {"init_states": [], "final_states": [], "b_value": 1}
                v1[in_name]["init_states"].append(out_name)

    for name in v1:
        v1[name]["init_states"] = list(dict.fromkeys(v1[name]["init_states"]))
        v1[name]["final_states"] = list(dict.fromkeys(v1[name]["final_states"]))
    return v1


def load_model(path: str = MODEL_PATH) -> dict:
    """Загружает модель действий из JSON-файла. Поддерживает v1 и v2 форматы."""
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    if raw.get("model_actions") is not None:
        return _v2_to_v1(raw)
    return raw


def build_states(model_data: dict) -> Dict[str, Dict[str, List[str]]]:
    """Строит словарь состояний из модели: какое действие приводит к какому состоянию."""
    states: Dict[str, Dict[str, List[str]]] = {}
    for action_name, action_data in model_data.items():
        for final_state in action_data["final_states"]:
            if final_state not in states:
                states[final_state] = {"actions": []}
            states[final_state]["actions"].append(action_name)
    return states


# Глобальная модель по умолчанию (для обратной совместимости)
model = load_model()
states = build_states(model)


def get_ways_to_action(
    action_name: str,
    visited_actions: Optional[set] = None,
    rounds: RoundType = "ALL",
    model_data: Optional[dict] = None,
    states_data: Optional[dict] = None,
) -> List[List[str]]:
    """
    Находит все возможные пути к указанному действию.

    Args:
        action_name: название действия
        visited_actions: множество уже посещенных действий (для предотвращения циклов)
        rounds: режим генерации (ALL, QG, RANDOM)
        model_data: модель (если None, используется глобальная)
        states_data: состояния (если None, используются глобальные)
    """
    m = model_data if model_data is not None else model
    s = states_data if states_data is not None else states

    if visited_actions is None:
        visited_actions = set()

    if action_name in visited_actions:
        return []

    visited_actions = visited_actions.copy()
    visited_actions.add(action_name)

    action = m[action_name]

    if not action["init_states"]:
        return [[action_name]]

    # Собираем пути для каждого начального состояния
    all_ways_for_states = []
    for init_state in action["init_states"]:
        ways = get_ways_to_state(init_state, visited_actions, rounds, m, s)
        all_ways_for_states.append(ways)

    # Объединяем пути от всех начальных состояний
    current_ways = all_ways_for_states[0] if all_ways_for_states else []

    for i in range(1, len(all_ways_for_states)):
        next_ways = all_ways_for_states[i]
        combined_ways = []

        for way1 in current_ways:
            for way2 in next_ways:
                combined = way1 + way2
                action_counts: Dict[str, int] = {}
                valid = True
                for act in combined:
                    action_counts[act] = action_counts.get(act, 0) + 1
                    if action_counts[act] > MAX_ACTION_REPEATS:
                        valid = False
                        break
                if valid:
                    combined_ways.append(combined)

        current_ways = combined_ways

    # Добавляем само действие в конец
    result = []
    for way in current_ways:
        if can_add_action(way, action_name):
            result.append(way + [action_name])

    return result


def get_ways_to_state(
    state_name: str,
    visited_actions: Optional[set] = None,
    rounds: RoundType = "ALL",
    model_data: Optional[dict] = None,
    states_data: Optional[dict] = None,
) -> List[List[str]]:
    """
    Находит все возможные пути к указанному состоянию.

    Args:
        state_name: название состояния
        visited_actions: множество уже посещенных действий
        rounds: режим генерации (ALL, QG, RANDOM)
        model_data: модель (если None, используется глобальная)
        states_data: состояния (если None, используются глобальные)
    """
    m = model_data if model_data is not None else model
    s = states_data if states_data is not None else states

    if visited_actions is None:
        visited_actions = set()

    state = s[state_name]

    if rounds == "ALL":
        ways_to_state: List[List[str]] = []
        for action_name in state["actions"]:
            ways = get_ways_to_action(action_name, visited_actions, rounds, m, s)
            ways_to_state.extend(ways)
        return ways_to_state

    elif rounds == "QG":
        best_action = max(
            state["actions"],
            key=lambda a: m[a].get("b_value", 1),
            default=None,
        )
        if best_action:
            return get_ways_to_action(best_action, visited_actions, rounds, m, s)
        return []

    elif rounds == "RANDOM":
        actions = state["actions"]
        if not actions:
            return []
        weights = [m[a].get("b_value", 1) for a in actions]
        chosen = random.choices(actions, weights=weights, k=1)[0]
        return get_ways_to_action(chosen, visited_actions, rounds, m, s)

    return []


def generate_cases_for_actions(
    actions: List[str],
    verbose: bool = False,
    rounds: RoundType = "ALL",
    model_data: Optional[dict] = None,
) -> Dict[str, List[List[str]]]:
    """
    Генерирует тест-кейсы для списка действий.

    Args:
        actions: список названий действий
        verbose: вывод подробной информации
        rounds: режим генерации (ALL, QG, RANDOM)
        model_data: произвольная модель (если None, используется глобальная)

    Returns:
        словарь, где ключ - название действия, значение - список тест-кейсов
    """
    m = model_data if model_data is not None else model
    s = build_states(m) if model_data is not None else states

    result = {}
    for action in actions:
        if action not in m:
            result[action] = []
            continue
        try:
            cases = get_ways_to_action(action, rounds=rounds, model_data=m, states_data=s)
            result[action] = cases
        except Exception:
            result[action] = []

    return result
