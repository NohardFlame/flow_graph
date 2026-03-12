let cy;
let selectionOrder = [];

const NODE_PADDING = 20;
const TEXT_MAX_WIDTH = 120;
const FONT_SIZE = 12;
const CHAR_WIDTH = 7;
const LINE_HEIGHT = 16;
const MIN_NODE_WIDTH = 60;
const MIN_NODE_HEIGHT = 40;
const DEFAULT_B_VALUE = 1;
const MAX_ACTION_REPEATS = 2;

// --- Text / size helpers ---

function wrapText(text, maxWidth) {
    var words = text.split(/\s+/);
    var lines = [];
    var cur = '';
    for (var i = 0; i < words.length; i++) {
        var w = words[i];
        var test = cur ? cur + ' ' + w : w;
        if (test.length * CHAR_WIDTH > maxWidth && cur) { lines.push(cur); cur = w; }
        else { cur = test; }
    }
    if (cur) lines.push(cur);
    return lines.length ? lines : [''];
}

function calcNodeSize(label) {
    var lines = wrapText(label, TEXT_MAX_WIDTH);
    var longest = lines.reduce(function(a, b) { return a.length > b.length ? a : b; }, '');
    return {
        w: Math.max(MIN_NODE_WIDTH, longest.length * CHAR_WIDTH + NODE_PADDING * 2),
        h: Math.max(MIN_NODE_HEIGHT, lines.length * LINE_HEIGHT + NODE_PADDING * 2),
    };
}

function actionLabel(name, bValue) {
    return name + '\n[b=' + bValue + ']';
}

// Build display name for an action from its parts (actor, action, place)
function buildActionName(actor, action, place) {
    return [actor, action, place].filter(function(p) { return p && p.trim(); }).join(' ');
}

// Build display label for a state node: "object state"
function buildStateName(objectName, stateName) {
    return [objectName, stateName].filter(function(p) { return p && p.trim(); }).join(' ');
}

// =====================================================================
// Test generation engine (ported from Python testgen.py + run.py)
// =====================================================================

function buildStates(modelData) {
    var states = {};
    for (var actionName in modelData) {
        var finals = modelData[actionName].final_states || [];
        for (var i = 0; i < finals.length; i++) {
            var fs = finals[i];
            if (!states[fs]) states[fs] = { actions: [] };
            states[fs].actions.push(actionName);
        }
    }
    return states;
}

function canAddAction(path, action) {
    var count = 0;
    for (var i = 0; i < path.length; i++) { if (path[i] === action) count++; }
    return count < MAX_ACTION_REPEATS;
}

function getWaysToAction(actionName, visitedActions, rounds, m, s) {
    if (visitedActions[actionName]) return [];
    var visited = {};
    for (var k in visitedActions) visited[k] = true;
    visited[actionName] = true;

    var action = m[actionName];
    if (!action) return [];
    if (!action.init_states || action.init_states.length === 0) return [[actionName]];

    var allWays = [];
    for (var i = 0; i < action.init_states.length; i++) {
        var ways = getWaysToState(action.init_states[i], visited, rounds, m, s);
        allWays.push(ways);
    }

    var current = allWays[0] || [];
    for (var i = 1; i < allWays.length; i++) {
        var next = allWays[i];
        var combined = [];
        for (var a = 0; a < current.length; a++) {
            for (var b = 0; b < next.length; b++) {
                var merged = current[a].concat(next[b]);
                var counts = {}, valid = true;
                for (var c = 0; c < merged.length; c++) {
                    counts[merged[c]] = (counts[merged[c]] || 0) + 1;
                    if (counts[merged[c]] > MAX_ACTION_REPEATS) { valid = false; break; }
                }
                if (valid) combined.push(merged);
            }
        }
        current = combined;
    }

    var result = [];
    for (var i = 0; i < current.length; i++) {
        if (canAddAction(current[i], actionName)) {
            result.push(current[i].concat([actionName]));
        }
    }
    return result;
}

function getWaysToState(stateName, visitedActions, rounds, m, s) {
    var state = s[stateName];
    if (!state) return [];

    if (rounds === 'ALL') {
        var ways = [];
        for (var i = 0; i < state.actions.length; i++) {
            var w = getWaysToAction(state.actions[i], visitedActions, rounds, m, s);
            ways = ways.concat(w);
        }
        return ways;
    }

    if (rounds === 'QG') {
        var best = null, bestVal = -1;
        for (var i = 0; i < state.actions.length; i++) {
            var bv = (m[state.actions[i]] || {}).b_value || 1;
            if (bv > bestVal) { bestVal = bv; best = state.actions[i]; }
        }
        return best ? getWaysToAction(best, visitedActions, rounds, m, s) : [];
    }

    if (rounds === 'RANDOM') {
        var actions = state.actions;
        if (!actions.length) return [];
        var weights = actions.map(function(a) { return (m[a] || {}).b_value || 1; });
        var totalW = weights.reduce(function(a, b) { return a + b; }, 0);
        var r = Math.random() * totalW, cum = 0, chosen = actions[0];
        for (var i = 0; i < actions.length; i++) {
            cum += weights[i];
            if (r <= cum) { chosen = actions[i]; break; }
        }
        return getWaysToAction(chosen, visitedActions, rounds, m, s);
    }

    return [];
}

function generateCases(modelData, actions, rounds) {
    var s = buildStates(modelData);
    var result = {};
    for (var i = 0; i < actions.length; i++) {
        var a = actions[i];
        if (!modelData[a]) { result[a] = []; continue; }
        try { result[a] = getWaysToAction(a, {}, rounds, modelData, s); }
        catch (e) { result[a] = []; }
    }
    return result;
}

// --- Formatting engine (ported from run.py) ---

function getStepChannel(passage, stepIndex, totalSteps) {
    if (passage === 'NONE') return null;
    if (passage === 'API') return 'API';
    if (passage === 'UI_FULL') return 'UI';
    if (passage === 'MANUAL_FULL') return 'MANUAL';
    var isLast = stepIndex === totalSteps - 1;
    if (passage === 'UI') return isLast ? 'UI' : 'API';
    if (passage === 'MANUAL') return isLast ? 'MANUAL' : 'API';
    return null;
}

function withChannel(text, ch) {
    return ch ? text + ' (' + ch + ')' : text;
}

function formatTestSuites(casesDict, modelData, testStructure, passage) {
    var lines = [];
    var scenarioCounter = 1;

    for (var action in casesDict) {
        var cases = casesDict[action];
        if (!cases || !cases.length) continue;

        lines.push('Функциональность: "' + action + '"');
        lines.push('');

        for (var ci = 0; ci < cases.length; ci++) {
            var cs = cases[ci];
            var total = cs.length;
            var finals = (modelData[action] || {}).final_states || [];

            if (testStructure === 'LEAF') {
                for (var vi = 0; vi < finals.length; vi++) {
                    lines.push('Сценарий ' + scenarioCounter + '.' + (vi + 1) + ' ' + action + ' "' + finals[vi] + '"');
                    for (var si = 0; si < total; si++) {
                        var ch = getStepChannel(passage, si, total);
                        lines.push('Когда ' + withChannel(cs[si], ch));
                    }
                    var chLast = getStepChannel(passage, total - 1, total);
                    lines.push('Тогда ' + withChannel(finals[vi], chLast));
                    lines.push('');
                }
            } else if (testStructure === 'BRANCH') {
                lines.push('Сценарий ' + scenarioCounter + ' ' + action);
                for (var si = 0; si < total; si++) {
                    var ch = getStepChannel(passage, si, total);
                    lines.push('Когда ' + withChannel(cs[si], ch));
                }
                for (var vi = 0; vi < finals.length; vi++) {
                    var chLast = getStepChannel(passage, total - 1, total);
                    lines.push('Тогда ' + withChannel(finals[vi], chLast));
                }
                lines.push('');
            } else if (testStructure === 'TREE') {
                lines.push('Сценарий ' + scenarioCounter + ' ' + action);
                for (var si = 0; si < total; si++) {
                    var ch = getStepChannel(passage, si, total);
                    lines.push('Когда ' + withChannel(cs[si], ch));
                    if (si < total - 1) {
                        var stepFinals = (modelData[cs[si]] || {}).final_states || [];
                        for (var sf = 0; sf < stepFinals.length; sf++) {
                            lines.push('Тогда ' + withChannel(stepFinals[sf], ch));
                        }
                    }
                }
                for (var vi = 0; vi < finals.length; vi++) {
                    var chLast = getStepChannel(passage, total - 1, total);
                    lines.push('Тогда ' + withChannel(finals[vi], chLast));
                }
                lines.push('');
            }
            scenarioCounter++;
        }
    }
    return lines.join('\n');
}

// =====================================================================
// Action modal
// =====================================================================

function showActionModal(actor, action, place, bValue, onOk) {
    var LABEL_STYLE = 'display:flex;flex-direction:column;gap:4px;font-size:13px;font-weight:500;color:#444;';
    var INPUT_STYLE = 'padding:8px 10px;border:1px solid #ccc;border-radius:5px;font-size:14px;outline:none;';

    var overlay = document.createElement('div');
    overlay.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.35);display:flex;align-items:center;justify-content:center;z-index:10000;';
    overlay.innerHTML =
        '<div style="background:#fff;border-radius:10px;min-width:360px;box-shadow:0 8px 30px rgba(0,0,0,0.2);">' +
            '<div style="padding:14px 20px;font-weight:600;font-size:16px;border-bottom:1px solid #eee;">Действие</div>' +
            '<div style="padding:16px 20px;display:flex;flex-direction:column;gap:12px;">' +
                '<label style="' + LABEL_STYLE + '">Актор (кто делает)' +
                    '<input type="text" id="_mActor" style="' + INPUT_STYLE + '" placeholder="пользователь" />' +
                '</label>' +
                '<label style="' + LABEL_STYLE + '">Действие (что делает)' +
                    '<input type="text" id="_mAction" style="' + INPUT_STYLE + '" placeholder="создает документ" />' +
                '</label>' +
                '<label style="' + LABEL_STYLE + '">Место (где)' +
                    '<input type="text" id="_mPlace" style="' + INPUT_STYLE + '" placeholder="(необязательно)" />' +
                '</label>' +
                '<label style="' + LABEL_STYLE + '">b_value (1–10)' +
                    '<input type="number" id="_mBVal" style="' + INPUT_STYLE + '" min="1" max="10" />' +
                '</label>' +
            '</div>' +
            '<div style="padding:12px 20px;display:flex;gap:8px;justify-content:flex-end;border-top:1px solid #eee;">' +
                '<button id="_mOk" style="padding:10px 15px;border:1px solid #ccc;border-radius:5px;cursor:pointer;background:#007bff;color:white;">OK</button>' +
                '<button id="_mCancel" style="padding:10px 15px;border:1px solid #ccc;border-radius:5px;cursor:pointer;">Отмена</button>' +
            '</div>' +
        '</div>';
    document.body.appendChild(overlay);

    var actorInput  = document.getElementById('_mActor');
    var actionInput = document.getElementById('_mAction');
    var placeInput  = document.getElementById('_mPlace');
    var bInput      = document.getElementById('_mBVal');
    actorInput.value  = actor || '';
    actionInput.value = action || '';
    placeInput.value  = place || '';
    bInput.value = (bValue >= 1 && bValue <= 10) ? bValue : DEFAULT_B_VALUE;
    actorInput.focus();

    function close() { document.body.removeChild(overlay); }

    function handleOk() {
        var ac = actorInput.value.trim();
        var aa = actionInput.value.trim();
        var ap = placeInput.value.trim();
        var b  = parseInt(bInput.value, 10);
        if (!aa) { actionInput.focus(); return; } // действие обязательно
        if (!(b >= 1 && b <= 10)) b = DEFAULT_B_VALUE;
        close();
        onOk(ac, aa, ap, b);
    }

    document.getElementById('_mOk').addEventListener('click', handleOk);
    document.getElementById('_mCancel').addEventListener('click', close);
    overlay.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') handleOk();
        if (e.key === 'Escape') close();
    });
}

// =====================================================================
// State modal (object + state)
// =====================================================================

function showStateModal(objectName, stateName, onOk) {
    var LABEL_STYLE = 'display:flex;flex-direction:column;gap:4px;font-size:13px;font-weight:500;color:#444;';
    var INPUT_STYLE = 'padding:8px 10px;border:1px solid #ccc;border-radius:5px;font-size:14px;outline:none;';

    var overlay = document.createElement('div');
    overlay.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.35);display:flex;align-items:center;justify-content:center;z-index:10000;';
    overlay.innerHTML =
        '<div style="background:#fff;border-radius:10px;min-width:360px;box-shadow:0 8px 30px rgba(0,0,0,0.2);">' +
            '<div style="padding:14px 20px;font-weight:600;font-size:16px;border-bottom:1px solid #eee;">Объект и состояние</div>' +
            '<div style="padding:16px 20px;display:flex;flex-direction:column;gap:12px;">' +
                '<label style="' + LABEL_STYLE + '">Объект' +
                    '<input type="text" id="_mObjName" style="' + INPUT_STYLE + '" placeholder="документ" />' +
                '</label>' +
                '<label style="' + LABEL_STYLE + '">Состояние' +
                    '<input type="text" id="_mStateName" style="' + INPUT_STYLE + '" placeholder="создан" />' +
                '</label>' +
            '</div>' +
            '<div style="padding:12px 20px;display:flex;gap:8px;justify-content:flex-end;border-top:1px solid #eee;">' +
                '<button id="_mOk" style="padding:10px 15px;border:1px solid #ccc;border-radius:5px;cursor:pointer;background:#28a745;color:white;">OK</button>' +
                '<button id="_mCancel" style="padding:10px 15px;border:1px solid #ccc;border-radius:5px;cursor:pointer;">Отмена</button>' +
            '</div>' +
        '</div>';
    document.body.appendChild(overlay);

    var objInput   = document.getElementById('_mObjName');
    var stateInput = document.getElementById('_mStateName');
    objInput.value   = objectName || '';
    stateInput.value = stateName || '';
    objInput.focus();

    function close() { document.body.removeChild(overlay); }

    function handleOk() {
        var o = objInput.value.trim();
        var s = stateInput.value.trim();
        if (!o) { objInput.focus(); return; }
        if (!s) { stateInput.focus(); return; }
        close();
        onOk(o, s);
    }

    document.getElementById('_mOk').addEventListener('click', handleOk);
    document.getElementById('_mCancel').addEventListener('click', close);
    overlay.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') handleOk();
        if (e.key === 'Escape') close();
    });
}

// =====================================================================
// Init
// =====================================================================

window.addEventListener('DOMContentLoaded', function() {
    initTestManager();
    renderGraph({ nodes: [], edges: [] });
});

// --- Test Manager panel ---

function initTestManager() {
    var panel = document.getElementById('testManagerPanel');
    var body  = document.getElementById('tmBody');
    var collapseBtn = document.getElementById('tmCollapseBtn');

    console.log('initTestManager called');
    console.log('panel:', panel);
    console.log('collapseBtn:', collapseBtn);
    console.log('closeBtn:', document.getElementById('tmCloseBtn'));

    document.getElementById('testManagerToggle').addEventListener('click', function() {
        console.log('Test Manager toggle clicked');
        panel.classList.toggle('hidden');
    });

    document.getElementById('tmCloseBtn').addEventListener('click', function() {
        console.log('Close button clicked');
        panel.classList.add('hidden');
    });

    collapseBtn.addEventListener('click', function() {
        console.log('Collapse button clicked - скрываем/показываем радиобатоны');
        panel.classList.toggle('collapsed');
        collapseBtn.textContent = panel.classList.contains('collapsed') ? '\u25B8' : '\u25BE';

        // Логирование состояния
        const fieldsets = panel.querySelectorAll('.tm-fieldset');
        if (panel.classList.contains('collapsed')) {
            console.log('Свернуто: скрыто ' + fieldsets.length + ' полей с радиобатонами');
        } else {
            console.log('Развернуто: показаны все поля');
        }
    });

    document.getElementById('tmGenAll').addEventListener('click', function() { runGenerate(false); });
    document.getElementById('tmGenSelected').addEventListener('click', function() { runGenerate(true); });
    document.getElementById('tmSaveToFile').addEventListener('click', saveTestsToFile);

    // Инициализация новой панели для создания тест-кейсов
    initTestCasePanel();
}

// =====================================================================
// Панель для создания тест-кейсов
// =====================================================================

function initTestCasePanel() {
    var casePanel = document.getElementById('testCasePanel');
    var caseCollapseBtn = document.getElementById('tmCaseCollapseBtn');

    if (!casePanel || !caseCollapseBtn) {
        console.log('Элементы панели тест-кейсов не найдены');
        return;
    }

    console.log('initTestCasePanel called');
    console.log('casePanel:', casePanel);
    console.log('caseCollapseBtn:', caseCollapseBtn);

    // Кнопка сворачивания панели тест-кейсов
    caseCollapseBtn.addEventListener('click', function() {
        console.log('Test Case panel collapse button clicked');
        casePanel.classList.toggle('collapsed');

        if (casePanel.classList.contains('collapsed')) {
            console.log('Панель тест-кейсов свернута');
        } else {
            console.log('Панель тест-кейсов развернута');
        }
    });

    // Обработчики для кнопок создания тест-кейсов
    var caseButtons = document.querySelectorAll('.tm-case-btn');
    caseButtons.forEach(function(button) {
        button.addEventListener('click', function() {
            var testType = this.getAttribute('data-type');

            // Проверяем, что data-type установлен
            if (!testType) {
                console.error('Кнопка не имеет data-type атрибута:', this.textContent);
                alert('Ошибка: кнопка не настроена правильно');
                return;
            }

            // Пропускаем кнопку сохранения
            if (testType === 'save-all') {
                return; // Эта кнопка обрабатывается отдельно
            }

            console.log('Нажата кнопка тест-кейса:', testType, this.textContent);

            // Получаем выделенные действия
            var selectedActions = getSelectedActions();
            console.log('Выделенные действия:', selectedActions);

            // Генерируем тест-кейсы
            generateTestCases(testType, selectedActions);
        });
    });

    // Кнопка сохранения всех тест-кейсов в файл
    document.getElementById('tmCaseSaveToFile').addEventListener('click', saveTestCasesToFile);
}

// Функция для получения выделенных действий из графа
function getSelectedActions() {
    if (!cy) {
        console.log('Граф не инициализирован');
        return [];
    }

    var selectedActions = [];

    // Получаем выделенные узлы-действия
    cy.nodes('[type="action"]:selected').forEach(function(node) {
        var actionName = node.data('name') || node.id();
        if (actionName && !selectedActions.includes(actionName)) {
            selectedActions.push(actionName);
        }
    });

    // Если нет выделенных действий, показываем сообщение
    if (selectedActions.length === 0) {
        console.log('Нет выделенных действий. Выделите действия на графе.');

        // Можно добавить уведомление для пользователя
        var notice = document.querySelector('.tm-case-notice');
        if (notice) {
            notice.innerHTML = '⚠️ <strong>Выделите действия на графе!</strong> Кликните на узлы-действия.';
            notice.style.background = '#f8d7da';
            notice.style.borderColor = '#f5c6cb';
            notice.style.color = '#721c24';

            // Возвращаем исходный текст через 3 секунды
            setTimeout(function() {
                notice.innerHTML = '⚠️ Выделите действия, которые были изменены';
                notice.style.background = '';
                notice.style.borderColor = '';
                notice.style.color = '';
            }, 3000);
        }
    }

    console.log('Выделенные действия:', selectedActions);
    return selectedActions;
}

// Функция для генерации тест-кейсов
function generateTestCases(testType, selectedActions) {
    console.log('Генерация тест-кейсов типа:', testType);
    console.log('Для действий:', selectedActions);

    // Конфигурации для каждого типа тест-кейсов
    var testCaseConfigs = {
        'after-code-back': {
            description: 'После написания кода back',
            structure: 'BRANCH',
            passage: 'API',
            rounds: 'ALL',
            fullDescription: 'Test Suite для выделенных действий BRANCH API ALL',
            useSelectedActions: true  // Только для выделенных действий
        },
        'after-code-ui': {
            description: 'После написания кода UI',
            structure: 'BRANCH',
            passage: 'UI',
            rounds: 'QG',
            fullDescription: 'для выделенных действий BRANCH UI QG',
            useSelectedActions: true  // Только для выделенных действий
        },
        'before-testing': {
            description: 'Перед передачей в тестирование',
            structure: 'BRANCH',
            passage: 'API',
            rounds: 'QG',
            fullDescription: 'BRANCH API QG',
            useSelectedActions: false  // Для всех действий
        },
        'manual-changes': {
            description: 'Для мануального тестирования изменений',
            structure: 'BRANCH',
            passage: 'MANUAL',
            rounds: 'ALL',
            fullDescription: 'Test Suite для выделенных действий BRANCH MANUAL ALL',
            useSelectedActions: true  // Только для выделенных действий
        },
        'impact-testing': {
            description: 'Импакт тестирование',
            structure: 'BRANCH',
            passage: 'API',
            rounds: 'ALL',
            fullDescription: 'все действия в которых есть выделенные действия BRANCH API ALL',
            useSelectedActions: true  // Только для выделенных действий
        },
        'manual-regress': {
            description: 'Мануальный регресс',
            structure: 'TREE',
            passage: 'MANUAL',
            rounds: 'RANDOM',
            fullDescription: 'TREE MANUAL RANDOM',
            useSelectedActions: false  // Для всех действий
        },
        'ui-regress': {
            description: 'UI регресс',
            structure: 'TREE',
            passage: 'UI',
            rounds: 'RANDOM',
            fullDescription: 'TREE UI RANDOM',
            useSelectedActions: false  // Для всех действий
        },
        'before-prod': {
            description: 'Перед продом',
            structure: 'BRANCH',
            passage: 'API',
            rounds: 'QG',
            fullDescription: 'BRANCH API QG',
            useSelectedActions: false  // Для всех действий
        },
        'api-regress': {
            description: 'API регресс',
            structure: 'TREE',
            passage: 'API',
            rounds: 'ALL',
            fullDescription: 'TREE API ALL',
            useSelectedActions: false  // Для всех действий
        },
        'full-test-plan': {
            description: 'Весь тест план',
            structure: 'MIXED',
            passage: 'MIXED',
            rounds: 'MIXED',
            fullDescription: 'все вышеперечисленные категории',
            useSelectedActions: false  // Комбинация
        }
    };

    var config = testCaseConfigs[testType];
    if (!config) {
        console.error('Неизвестный тип тест-кейса:', testType);
        return;
    }

    // Получаем модель из графа
    var modelData = buildModelFromGraph();
    var output = document.getElementById('tmOutput');

    if (Object.keys(modelData).length === 0) {
        output.value = 'Нет действий в графе. Загрузите модель или добавьте действия.';
        return;
    }

    // Определяем какие действия использовать
    var actions;
    var config = testCaseConfigs[testType];

    if (config.useSelectedActions) {
        // Используем выделенные действия
        if (selectedActions && selectedActions.length > 0) {
            actions = selectedActions.filter(function(action) {
                return modelData.hasOwnProperty(action);
            });
            if (actions.length === 0) {
                output.value = 'Выделенные действия не найдены в модели.';
                return;
            }
        } else {
            output.value = 'Для этого типа тест-кейсов нужно выделить действия на графе.';
            return;
        }
    } else {
        // Используем все действия
        actions = Object.keys(modelData);
        if (actions.length === 0) {
            output.value = 'Нет действий в модели.';
            return;
        }
    }

    // Для полного тест-плана генерируем все варианты
    if (testType === 'full-test-plan') {
        generateFullTestPlan(modelData, selectedActions, output);
        return;
    }

    // Генерируем тест-кейсы с указанной конфигурацией
    var cases = generateCases(modelData, actions, config.rounds);
    var text = formatTestSuites(cases, modelData, config.structure, config.passage);

    // Формируем полный вывод
    var message = '=== ' + config.description + ' ===\n';
    message += config.fullDescription + '\n\n';
    message += 'Выделенные действия: ' + actions.join(', ') + '\n';
    message += 'Структура: ' + config.structure + ' | Passage: ' + config.passage + ' | Режим: ' + config.rounds + '\n\n';
    message += text || '(пусто — нет кейсов для выбранных параметров)';

    output.value = message;
    output.scrollTop = output.scrollHeight;
}

// Функция для генерации полного тест-плана
function generateFullTestPlan(modelData, selectedActions, outputElement) {
    var allMessages = [];
    var testTypes = [
        'after-code-back',
        'after-code-ui',
        'before-testing',
        'manual-changes',
        'impact-testing',
        'manual-regress',
        'ui-regress',
        'before-prod',
        'api-regress'
    ];

    testTypes.forEach(function(testType) {
        var config = {
            'after-code-back': {structure: 'BRANCH', passage: 'API', rounds: 'ALL', useSelected: true},
            'after-code-ui': {structure: 'BRANCH', passage: 'UI', rounds: 'QG', useSelected: true},
            'before-testing': {structure: 'BRANCH', passage: 'API', rounds: 'QG', useSelected: false},
            'manual-changes': {structure: 'BRANCH', passage: 'MANUAL', rounds: 'ALL', useSelected: true},
            'impact-testing': {structure: 'BRANCH', passage: 'API', rounds: 'ALL', useSelected: true},
            'manual-regress': {structure: 'TREE', passage: 'MANUAL', rounds: 'RANDOM', useSelected: false},
            'ui-regress': {structure: 'TREE', passage: 'UI', rounds: 'RANDOM', useSelected: false},
            'before-prod': {structure: 'BRANCH', passage: 'API', rounds: 'QG', useSelected: false},
            'api-regress': {structure: 'TREE', passage: 'API', rounds: 'ALL', useSelected: false}
        }[testType];

        // Определяем какие действия использовать
        var actions;
        if (config.useSelected && selectedActions && selectedActions.length > 0) {
            actions = selectedActions.filter(function(action) {
                return modelData.hasOwnProperty(action);
            });
        } else {
            actions = Object.keys(modelData);
        }

        if (actions.length === 0) {
            if (config.useSelected) {
                allMessages.push('=== ' + getTestTypeDescription(testType) + ' ===');
                allMessages.push('Нет выделенных действий для генерации.');
                allMessages.push('');
            }
            return;
        }

        var cases = generateCases(modelData, actions, config.rounds);
        var text = formatTestSuites(cases, modelData, config.structure, config.passage);

        allMessages.push('=== ' + getTestTypeDescription(testType) + ' ===');
        if (text && text !== '(пусто — нет кейсов для выбранных параметров)') {
            allMessages.push(text);
        } else {
            allMessages.push('Не удалось сгенерировать тест-кейсы.');
        }
        allMessages.push(''); // пустая строка
    });

    if (allMessages.length === 0) {
        outputElement.value = 'Не удалось сгенерировать тест-кейсы.';
    } else {
        // Не добавляем заголовок "=== ВЕСЬ ТЕСТ ПЛАН ==="
        outputElement.value = allMessages.join('\n');
    }
    outputElement.scrollTop = outputElement.scrollHeight;
}

// Вспомогательная функция для получения описания типа теста
function getTestTypeDescription(testType) {
    var descriptions = {
        'after-code-back': 'После написания кода back',
        'after-code-ui': 'После написания кода UI',
        'before-testing': 'Перед передачей в тестирование',
        'manual-changes': 'Для мануального тестирования изменений',
        'impact-testing': 'Импакт тестирование',
        'manual-regress': 'Мануальный регресс',
        'ui-regress': 'UI регресс',
        'before-prod': 'Перед продом',
        'api-regress': 'API регресс'
    };
    return descriptions[testType] || testType;
}

// =====================================================================
// Graph
// =====================================================================

function renderGraph(elements) {
    if (elements.nodes) {
        for (var i = 0; i < elements.nodes.length; i++) {
            var n = elements.nodes[i];
            var size = calcNodeSize(n.data.label || '');
            n.data._w = size.w;
            n.data._h = size.h;
        }
    }

    if (cy) cy.destroy();
    cy = cytoscape({
        container: document.getElementById('cy'),
        elements: elements,
        style: [
            { selector: 'node', style: {
                'label': 'data(label)', 'text-valign': 'center', 'text-halign': 'center',
                'text-wrap': 'wrap', 'text-max-width': TEXT_MAX_WIDTH + 'px',
                'font-size': FONT_SIZE + 'px', 'padding': '0px',
                'border-width': 2, 'border-color': '#007bff', 'background-color': '#fff',
                'shape': 'rectangle', 'width': 'data(_w)', 'height': 'data(_h)',
            }},
            { selector: 'node[type="action"]', style: {
                'shape': 'round-rectangle', 'background-color': '#e6f7ff',
            }},
            { selector: 'node[type="state"]', style: {
                'shape': 'ellipse', 'background-color': '#f6ffed', 'border-color': '#52c41a',
            }},
            { selector: 'edge', style: {
                'width': 2, 'line-color': '#ccc',
                'target-arrow-shape': 'triangle', 'target-arrow-color': '#ccc', 'curve-style': 'bezier',
            }},
            { selector: ':selected', style: { 'border-width': 4, 'border-color': '#ffc107' }},
        ],
        layout: { name: 'dagre', rankDir: 'TB' }
    });

    cy.on('select', 'node', function(evt) {
        var id = evt.target.id();
        if (selectionOrder.indexOf(id) === -1) selectionOrder.push(id);
    });
    cy.on('unselect', 'node', function(evt) {
        selectionOrder = selectionOrder.filter(function(x) { return x !== evt.target.id(); });
    });

    // Dblclick: edit node
    cy.on('dblclick', 'node', function(event) {
        var node = event.target;
        var isAction = node.data('type') === 'action';
        var currentName = node.data('name') || node.id();
        var bVal = node.data('b_value') || DEFAULT_B_VALUE;

        if (isAction) {
            var curActor  = node.data('action_actor')  || '';
            var curAction = node.data('action_action') || '';
            var curPlace  = node.data('action_place')  || '';
            // Fallback: if parts are empty, put currentName into action_action
            if (!curAction) curAction = currentName;

            showActionModal(curActor, curAction, curPlace, bVal, function(actor, action, place, newB) {
                var newName = buildActionName(actor, action, place);
                if (newName !== currentName && cy.getElementById(newName).length > 0) {
                    alert('Узел с таким именем уже существует!');
                    return;
                }
                var oldId = node.id();
                node.data('name', newName);
                node.data('action_actor', actor);
                node.data('action_action', action);
                node.data('action_place', place);
                node.data('b_value', newB);
                node.data('label', actionLabel(newName, newB));
                node.data('id', newName);
                var size = calcNodeSize(node.data('label'));
                node.data('_w', size.w);
                node.data('_h', size.h);
                var idx = selectionOrder.indexOf(oldId);
                if (idx !== -1) selectionOrder[idx] = newName;
            });
        } else {
            var curObj   = node.data('object_name') || '';
            var curState = node.data('state_name')  || '';
            // Fallback: if parts are empty, put currentName into object_name
            if (!curObj) curObj = currentName;

            showStateModal(curObj, curState, function(objName, stateName) {
                var newName = buildStateName(objName, stateName);
                if (newName !== currentName && cy.getElementById(newName).length > 0) {
                    alert('Узел с таким именем уже существует!');
                    return;
                }
                var oldId = node.id();
                node.data('name', newName);
                node.data('object_name', objName);
                node.data('state_name', stateName);
                node.data('label', newName);
                node.data('id', newName);
                var size = calcNodeSize(newName);
                node.data('_w', size.w);
                node.data('_h', size.h);
                var idx = selectionOrder.indexOf(oldId);
                if (idx !== -1) selectionOrder[idx] = newName;
            });
        }
    });
}

// =====================================================================
// Add / Link
// =====================================================================

document.getElementById('addLinkButton').addEventListener('click', function() {
    if (selectionOrder.length < 2) { alert('Выберите узел-источник, затем узел-цель.'); return; }
    var srcId = selectionOrder[0], tgtId = selectionOrder[1];
    var src = cy.getElementById(srcId), tgt = cy.getElementById(tgtId);
    if (!src.length || !tgt.length) { alert('Узел удалён. Выберите заново.'); cy.elements().unselect(); selectionOrder = []; return; }
    if (src.data('type') === tgt.data('type')) { alert('Нельзя связывать узлы одного типа.'); }
    else {
        var eid = srcId + '->' + tgtId;
        if (!cy.getElementById(eid).length) cy.add({ group: 'edges', data: { id: eid, source: srcId, target: tgtId } });
    }
    cy.elements().unselect(); selectionOrder = [];
});

function addNode(type) {
    if (type === 'action') {
        showActionModal('', '', '', DEFAULT_B_VALUE, function(actor, action, place, bVal) {
            var name = buildActionName(actor, action, place);
            if (cy.getElementById(name).length > 0) { alert('Узел с таким именем уже существует!'); return; }
            var label = actionLabel(name, bVal);
            var size = calcNodeSize(label);
            cy.add({
                group: 'nodes',
                data: {
                    id: name, name: name, label: label, type: type,
                    action_actor: actor, action_action: action, action_place: place,
                    b_value: bVal, _w: size.w, _h: size.h
                },
                position: { x: 100, y: 100 },
            });
        });
    } else {
        showStateModal('', '', function(objName, stateName) {
            var name = buildStateName(objName, stateName);
            if (cy.getElementById(name).length > 0) { alert('Узел с таким именем уже существует!'); return; }
            var size = calcNodeSize(name);
            cy.add({
                group: 'nodes',
                data: {
                    id: name, name: name, label: name, type: type,
                    object_name: objName, state_name: stateName,
                    b_value: DEFAULT_B_VALUE, _w: size.w, _h: size.h
                },
                position: { x: 100, y: 100 },
            });
        });
    }
}

document.getElementById('addActionButton').addEventListener('click', function() { addNode('action'); });
document.getElementById('addStateButton').addEventListener('click', function() { addNode('state'); });

// =====================================================================
// Save / Load
// =====================================================================

document.getElementById('saveButton').addEventListener('click', function() {
    var name = prompt('Имя проекта:', 'model') || 'project';
    var output = buildV2ModelFromGraph();
    var blob = new Blob([JSON.stringify(output, null, 2)], { type: 'application/json' });
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = name + '.json';
    a.click();
});

// Build v2 JSON from the current Cytoscape graph
function buildV2ModelFromGraph() {
    var actionCounter = 1;
    var objectCounter = 1;
    var stateCounter  = 1;

    var model_actions = [];
    var model_objects = [];
    var model_connections = [];

    // Map: node display name -> generated action_id / composite state id
    var actionIdMap = {};  // actionName -> "a00001"
    var stateIdMap  = {};  // stateName  -> "o00001s00001"

    // --- Actions ---
    cy.nodes('[type="action"]').forEach(function(node) {
        var displayName = node.data('name') || node.id();
        var aid = 'a' + String(actionCounter++).padStart(5, '0');
        actionIdMap[displayName] = aid;

        model_actions.push({
            action_id:     aid,
            action_actor:  node.data('action_actor')  || null,
            action_action: node.data('action_action') || displayName,
            action_place:  node.data('action_place')  || null,
        });
    });

    // --- Objects / States ---
    // Group state nodes by object_name
    var objectGroups = {};  // objectName -> [{ node, stateName }]
    cy.nodes('[type="state"]').forEach(function(node) {
        var displayName = node.data('name') || node.id();
        var objName   = node.data('object_name') || displayName;
        var stateName = node.data('state_name')  || '';
        if (!objectGroups[objName]) objectGroups[objName] = [];
        objectGroups[objName].push({ node: node, displayName: displayName, stateName: stateName });
    });

    for (var objName in objectGroups) {
        var oid = 'o' + String(objectCounter++).padStart(5, '0');
        var states = [];
        objectGroups[objName].forEach(function(entry) {
            var sid = 's' + String(stateCounter++).padStart(5, '0');
            var compositeId = oid + sid;
            stateIdMap[entry.displayName] = compositeId;
            states.push({ state_id: sid, state_name: entry.stateName || entry.displayName });
        });
        model_objects.push({
            object_id: oid,
            object_name: objName,
            resource_state: states,
        });
    }

    // --- Connections ---
    cy.edges().forEach(function(edge) {
        var srcName = edge.source().data('name') || edge.source().id();
        var tgtName = edge.target().data('name') || edge.target().id();
        var srcIsAction = edge.source().data('type') === 'action';

        if (srcIsAction) {
            // action -> state (final_states)
            var aId = actionIdMap[srcName];
            var sId = stateIdMap[tgtName];
            if (aId && sId) {
                model_connections.push({ connection_out: aId, connection_in: sId });
            }
        } else {
            // state -> action (init_states)
            var sId = stateIdMap[srcName];
            var aId = actionIdMap[tgtName];
            if (sId && aId) {
                model_connections.push({ connection_out: sId, connection_in: aId });
            }
        }
    });

    return {
        model_actions: model_actions,
        model_objects: model_objects,
        model_connections: model_connections,
    };
}

document.getElementById('runLayoutButton').addEventListener('click', function() {
    cy.layout({ name: 'dagre', rankDir: 'TB' }).run();
});

// =====================================================================
// Import from run (flow_graph app GET /runs/{run_id}/graph)
// =====================================================================

function showImportRunModal() {
    var LABEL_STYLE = 'display:flex;flex-direction:column;gap:4px;font-size:13px;font-weight:500;color:#444;';
    var INPUT_STYLE = 'padding:8px 10px;border:1px solid #ccc;border-radius:5px;font-size:14px;outline:none;';

    var overlay = document.createElement('div');
    overlay.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.35);display:flex;align-items:center;justify-content:center;z-index:10000;';
    overlay.innerHTML =
        '<div style="background:#fff;border-radius:10px;min-width:360px;box-shadow:0 8px 30px rgba(0,0,0,0.2);">' +
            '<div style="padding:14px 20px;font-weight:600;font-size:16px;border-bottom:1px solid #eee;">Import from run</div>' +
            '<div style="padding:16px 20px;display:flex;flex-direction:column;gap:12px;">' +
                '<label style="' + LABEL_STYLE + '">App base URL' +
                    '<input type="text" id="_mBaseUrl" style="' + INPUT_STYLE + '" placeholder="http://localhost:8000" />' +
                '</label>' +
                '<label style="' + LABEL_STYLE + '">Run ID' +
                    '<input type="text" id="_mRunId" style="' + INPUT_STYLE + '" placeholder="run UUID" />' +
                '</label>' +
                '<p id="_mImportError" style="margin:0;font-size:13px;color:#c00;display:none;"></p>' +
            '</div>' +
            '<div style="padding:12px 20px;display:flex;gap:8px;justify-content:flex-end;border-top:1px solid #eee;">' +
                '<button id="_mImportOk" style="padding:10px 15px;border:1px solid #ccc;border-radius:5px;cursor:pointer;background:#007bff;color:white;">OK</button>' +
                '<button id="_mImportCancel" style="padding:10px 15px;border:1px solid #ccc;border-radius:5px;cursor:pointer;">Отмена</button>' +
            '</div>' +
        '</div>';
    document.body.appendChild(overlay);

    var baseInput = document.getElementById('_mBaseUrl');
    var runIdInput = document.getElementById('_mRunId');
    var errEl = document.getElementById('_mImportError');
    baseInput.value = '';
    runIdInput.value = '';
    baseInput.focus();

    function close() { document.body.removeChild(overlay); }

    function showError(msg) {
        errEl.textContent = msg || '';
        errEl.style.display = msg ? 'block' : 'none';
    }

    function handleOk() {
        var base = baseInput.value.trim();
        var runId = runIdInput.value.trim();
        if (!base) { showError('Enter App base URL'); baseInput.focus(); return; }
        if (!runId) { showError('Enter Run ID'); runIdInput.focus(); return; }
        showError('');
        var url = window.location.origin + '/import-run?base_url=' + encodeURIComponent(base) + '&run_id=' + encodeURIComponent(runId);
        fetch(url)
            .then(function(resp) {
                if (!resp.ok) return resp.json().then(function(o) { throw new Error(o.error || resp.statusText); });
                return resp.json();
            })
            .then(function(v1Model) {
                close();
                if (Object.keys(v1Model).length === 0) {
                    alert('Run has no actions.');
                    return;
                }
                document.getElementById('fileName').textContent = 'Run ' + runId;
                loadV1Model(v1Model);
                if (cy.elements().length > 0) {
                    cy.layout({ name: 'dagre', rankDir: 'TB' }).run();
                }
            })
            .catch(function(e) {
                showError(e.message || 'Failed to load run graph');
            });
    }

    document.getElementById('_mImportOk').addEventListener('click', handleOk);
    document.getElementById('_mImportCancel').addEventListener('click', close);
    overlay.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') handleOk();
        if (e.key === 'Escape') close();
    });
}

document.getElementById('importRunButton').addEventListener('click', showImportRunModal);

document.addEventListener('keydown', function(e) {
    if ((e.key === 'Delete' || e.key === 'Backspace') && document.activeElement.tagName !== 'INPUT' && document.activeElement.tagName !== 'TEXTAREA') {
        var selected = cy.elements(':selected');
        selected.nodes().forEach(function(n) { selectionOrder = selectionOrder.filter(function(x) { return x !== n.id(); }); });
        selected.remove();
    }
});

document.getElementById('fileInput').addEventListener('change', function(e) {
    var file = e.target.files[0];
    if (!file) return;
    document.getElementById('fileName').textContent = file.name;
    var reader = new FileReader();
    reader.onload = function(ev) {
        var json = JSON.parse(ev.target.result);

        // Detect format: v2 has model_actions array, v1 is a plain object of actions
        if (json.model_actions) {
            loadV2Model(json);
        } else {
            loadV1Model(json);
        }
    };
    reader.readAsText(file);
});

// Load old v1 format (flat object: actionName -> { init_states, final_states, b_value })
function loadV1Model(json) {
    var nodes = [], edges = [], ids = {};
    function add(id, type, bVal) {
        if (ids[id]) return;
        var label = type === 'action' ? actionLabel(id, bVal || DEFAULT_B_VALUE) : id;
        nodes.push({ data: { id: id, name: id, label: label, type: type, b_value: bVal || DEFAULT_B_VALUE } });
        ids[id] = true;
    }
    for (var act in json) {
        add(act, 'action', json[act].b_value);
        (json[act].init_states || []).forEach(function(s) { add(s, 'state'); edges.push({ data: { id: s + '->' + act, source: s, target: act } }); });
        (json[act].final_states || []).forEach(function(s) { add(s, 'state'); edges.push({ data: { id: act + '->' + s, source: act, target: s } }); });
    }
    renderGraph({ nodes: nodes, edges: edges });
}

// Load new v2 format ({ model_actions, model_objects, model_connections })
function loadV2Model(json) {
    var nodes = [], edges = [], ids = {};

    // Map: action_id -> display name & node data
    var actionMap = {};  // action_id -> { name, actor, action, place }
    (json.model_actions || []).forEach(function(a) {
        var displayName = buildActionName(a.action_actor, a.action_action, a.action_place);
        actionMap[a.action_id] = {
            name: displayName,
            actor:  a.action_actor  || '',
            action: a.action_action || '',
            place:  a.action_place  || '',
        };
        var label = actionLabel(displayName, DEFAULT_B_VALUE);
        var size = calcNodeSize(label);
        nodes.push({ data: {
            id: displayName, name: displayName, label: label, type: 'action',
            action_actor: a.action_actor || '', action_action: a.action_action || '', action_place: a.action_place || '',
            b_value: DEFAULT_B_VALUE, _w: size.w, _h: size.h,
        }});
        ids[displayName] = true;
    });

    // Map: composite id (object_id + state_id) -> display name & node data
    var stateMap = {};  // compositeId -> { name, objectName, stateName }
    (json.model_objects || []).forEach(function(obj) {
        (obj.resource_state || []).forEach(function(st) {
            var compositeId = obj.object_id + st.state_id;
            var displayName = buildStateName(obj.object_name, st.state_name);
            stateMap[compositeId] = {
                name: displayName,
                objectName: obj.object_name || '',
                stateName:  st.state_name  || '',
            };
            if (!ids[displayName]) {
                var size = calcNodeSize(displayName);
                nodes.push({ data: {
                    id: displayName, name: displayName, label: displayName, type: 'state',
                    object_name: obj.object_name || '', state_name: st.state_name || '',
                    b_value: DEFAULT_B_VALUE, _w: size.w, _h: size.h,
                }});
                ids[displayName] = true;
            }
        });
    });

    // Connections
    (json.model_connections || []).forEach(function(c) {
        var outAction = actionMap[c.connection_out];
        var outState  = stateMap[c.connection_out];
        var inAction  = actionMap[c.connection_in];
        var inState   = stateMap[c.connection_in];

        var srcName = outAction ? outAction.name : (outState ? outState.name : null);
        var tgtName = inAction  ? inAction.name  : (inState  ? inState.name  : null);

        if (srcName && tgtName) {
            var eid = srcName + '->' + tgtName;
            if (!ids[eid]) {
                edges.push({ data: { id: eid, source: srcName, target: tgtName } });
                ids[eid] = true;
            }
        }
    });

    renderGraph({ nodes: nodes, edges: edges });
}

// =====================================================================
// Test Manager: generate (runs locally, no server needed)
// =====================================================================

function getRadioValue(name) {
    return document.querySelector('input[name="' + name + '"]:checked').value;
}

function buildModelFromGraph() {
    var m = {};
    cy.nodes('[type="action"]').forEach(function(node) {
        var name = node.data('name') || node.id();
        m[name] = {
            init_states: node.incomers('edge').sources().map(function(n) { return n.data('name') || n.id(); }),
            final_states: node.outgoers('edge').targets().map(function(n) { return n.data('name') || n.id(); }),
            b_value: node.data('b_value') || DEFAULT_B_VALUE,
        };
    });
    return m;
}

function runGenerate(selectedOnly) {
    var output = document.getElementById('tmOutput');
    var modelData = buildModelFromGraph();

    if (Object.keys(modelData).length === 0) {
        output.value = 'Нет действий в графе. Загрузите модель или добавьте действия.';
        return;
    }

    var actions;
    if (selectedOnly) {
        actions = [];
        cy.nodes('[type="action"]:selected').forEach(function(n) { actions.push(n.data('name') || n.id()); });
        if (actions.length === 0) { output.value = 'Выберите действия на графе (клик по узлам-действиям).'; return; }
    } else {
        actions = Object.keys(modelData);
    }

    var rounds = getRadioValue('rounds');
    var testStructure = getRadioValue('test_structure');
    var passage = getRadioValue('passage');

    var cases = generateCases(modelData, actions, rounds);
    var text = formatTestSuites(cases, modelData, testStructure, passage);
    output.value = text || '(пусто — нет кейсов для выбранных параметров)';

    // Сохраняем сгенерированные данные для возможного экспорта
    window.lastGeneratedData = {
        cases: cases,
        modelData: modelData,
        testStructure: testStructure,
        passage: passage,
        rounds: rounds,
        actions: actions,
        outputText: text,
        generationTime: new Date(),
        source: 'main-panel'
    };
}

// =====================================================================
// Функции для сохранения в файл
// =====================================================================

// Функция для сохранения тестов из основной панели
function saveTestsToFile() {
    if (!window.lastGeneratedData || !window.lastGeneratedData.cases) {
        alert('Сначала сгенерируйте тесты!');
        return;
    }

    var data = window.lastGeneratedData;
    if (!data.outputText || data.outputText === '(пусто — нет кейсов для выбранных параметров)') {
        alert('Нет данных для сохранения!');
        return;
    }

    try {
        var zip = new JSZip();
        var modelName = getCurrentModelName();
        var timestamp = formatDateTime(new Date());
        var baseFilename = modelName + '_' + timestamp;

        // Сохраняем общий файл со всеми тестами (необязательно, но оставим)
        zip.file('all_tests.txt', data.outputText);

        // Сохраняем каждый тест-сьют в отдельный файл
        var actionIndex = 1;
        for (var actionName in data.cases) {
            var actionCases = data.cases[actionName];
            if (actionCases && actionCases.length > 0) {
                // Генерируем тесты только для этого действия
                var actionModel = {};
                actionModel[actionName] = data.modelData[actionName];
                var actionText = formatTestSuites(
                    {[actionName]: actionCases},
                    actionModel,
                    data.testStructure,
                    data.passage
                );

                if (actionText && actionText !== '(пусто — нет кейсов для выбранных параметров)') {
                    // Имя файла просто по названию действия
                    var actionFilename = actionName.replace(/[^a-zA-Zа-яА-Я0-9\s]/g, ' ').trim() + '_tests.txt';
                    zip.file(actionFilename, actionText);
                    actionIndex++;
                }
            }
        }

        // Генерируем и скачиваем ZIP архив
        zip.generateAsync({type: "blob"})
            .then(function(content) {
                // Имя архива просто по названию модели
                var archiveName = modelName.replace(/[^a-zA-Zа-яА-Я0-9\s]/g, ' ').trim() + '_tests.zip';
                saveAs(content, archiveName);
                console.log('Тесты успешно сохранены в архив:', archiveName);
            })
            .catch(function(err) {
                console.error('Ошибка при создании архива:', err);
                alert('Ошибка при сохранении файлов: ' + err.message);
            });

    } catch (error) {
        console.error('Ошибка при сохранении тестов:', error);
        alert('Ошибка: ' + error.message);
    }
}

// Функция для сохранения тест-кейсов из панели тест-кейсов
function saveTestCasesToFile() {
    if (!window.lastTestCaseData) {
        alert('Сначала сгенерируйте тест-кейсы!');
        return;
    }

    var data = window.lastTestCaseData;
    if (!data.testCases || data.testCases.length === 0) {
        alert('Нет данных для сохранения!');
        return;
    }

    try {
        var zip = new JSZip();
        var modelName = getCurrentModelName();
        var timestamp = formatDateTime(new Date());
        var baseFilename = modelName + '_' + timestamp;

        // Сохраняем каждый тип тест-кейсов в отдельный файл
        data.testCases.forEach(function(testCase, index) {
            if (testCase.text && testCase.text !== '(пусто — нет кейсов для выбранных параметров)') {
                // Убираем заголовок "=== ВЕСЬ ТЕСТ ПЛАН ===" если он есть
                var fileContent = testCase.text;
                if (testCase.type === 'Весь тест план') {
                    // Для "Весь тест план" разбиваем на отдельные файлы
                    var sections = splitFullTestPlan(fileContent);
                    if (sections && sections.length > 0) {
                    sections.forEach(function(section) {
                        if (section.content && section.content.trim()) {
                            // Имя файла просто по названию раздела
                            var sectionFilename = section.name.replace(/[^a-zA-Zа-яА-Я0-9\s]/g, ' ').trim() + '.txt';
                            zip.file(sectionFilename, section.content);
                        }
                    });
                    }
                } else {
                    // Для обычных тест-кейсов сохраняем как есть
                    // Имя файла просто по названию типа тест-кейса
                    var filename = testCase.type.replace(/[^a-zA-Zа-яА-Я0-9\s]/g, ' ').trim() + '.txt';
                    zip.file(filename, fileContent);
                }
            }
        });

        // Генерируем и скачиваем ZIP архив
        zip.generateAsync({type: "blob"})
            .then(function(content) {
                // Имя архива просто по названию модели
                var archiveName = modelName.replace(/[^a-zA-Zа-яА-Я0-9\s]/g, ' ').trim() + '_test_cases.zip';
                saveAs(content, archiveName);
                console.log('Тест-кейсы успешно сохранены в архив:', archiveName);
            })
            .catch(function(err) {
                console.error('Ошибка при создании архива:', err);
                alert('Ошибка при сохранении файлов: ' + err.message);
            });

    } catch (error) {
        console.error('Ошибка при сохранении тест-кейсов:', error);
        alert('Ошибка: ' + error.message);
    }
}

// Вспомогательная функция для получения имени текущей модели
function getCurrentModelName() {
    var fileName = document.getElementById('fileName').textContent;
    if (fileName && fileName.trim() !== '') {
        // Убираем расширение .json если есть
        return fileName.replace(/\.json$/i, '').trim() || 'model';
    }

    // Пробуем получить из графа
    if (cy && cy.nodes().length > 0) {
        return 'graph_model';
    }

    return 'model';
}

// Вспомогательная функция для форматирования даты и времени
function formatDateTime(date) {
    var d = date || new Date();
    var year = d.getFullYear();
    var month = String(d.getMonth() + 1).padStart(2, '0');
    var day = String(d.getDate()).padStart(2, '0');
    var hours = String(d.getHours()).padStart(2, '0');
    var minutes = String(d.getMinutes()).padStart(2, '0');
    var seconds = String(d.getSeconds()).padStart(2, '0');

    return year + month + day + '_' + hours + minutes + seconds;
}

// Обновляем функцию generateTestCases для сохранения данных
var originalGenerateTestCases = generateTestCases;
generateTestCases = function(testType, selectedActions) {
    // Проверяем, что testType не null или undefined
    if (!testType) {
        console.error('Ошибка: testType не определен');
        return;
    }

    var result = originalGenerateTestCases(testType, selectedActions);

    // Сохраняем данные для возможного экспорта
    if (window.lastGeneratedData && window.lastGeneratedData.outputText) {
        if (!window.lastTestCaseData) {
            window.lastTestCaseData = { testCases: [] };
        }

        // Добавляем текущий тест-кейс
        var testCaseConfigs = {
            'after-code-back': 'После написания кода back',
            'after-code-ui': 'После написания кода UI',
            'before-testing': 'Перед передачей в тестирование',
            'manual-changes': 'Для мануального тестирования изменений',
            'impact-testing': 'Импакт тестирование',
            'manual-regress': 'Мануальный регресс',
            'ui-regress': 'UI регресс',
            'before-prod': 'Перед продом',
            'api-regress': 'API регресс',
            'full-test-plan': 'Весь тест план',
            'save-all': 'Сохранить все' // для кнопки сохранения
        };

        window.lastTestCaseData.testCases.push({
            type: testCaseConfigs[testType] || testType,
            text: window.lastGeneratedData.outputText,
            timestamp: new Date()
        });
    }

    return result;
};

// Функция для разбивки "Весь тест план" на отдельные разделы
function splitFullTestPlan(fullTestPlanText) {
    var sections = [];

    if (!fullTestPlanText) {
        return sections;
    }

    // Убираем заголовок "=== ВЕСЬ ТЕСТ ПЛАН ===" если он есть
    var text = fullTestPlanText.replace(/^=== ВЕСЬ ТЕСТ ПЛАН ===\s*\n*/gi, '');

    // Разбиваем текст по разделителям "=== ... ==="
    var lines = text.split('\n');
    var currentSection = null;
    var currentContent = [];

    for (var i = 0; i < lines.length; i++) {
        var line = lines[i];

        // Проверяем, начинается ли строка с "==="
        if (line.trim().startsWith('===') && line.trim().endsWith('===')) {
            // Если есть текущая секция, сохраняем ее
            if (currentSection && currentContent.length > 0) {
                sections.push({
                    name: currentSection,
                    content: currentContent.join('\n').trim()
                });
                currentContent = [];
            }

            // Извлекаем название секции (убираем ===)
            currentSection = line.replace(/^===\s*/, '').replace(/\s*===$/, '').trim();
        } else if (currentSection) {
            // Добавляем строку в текущую секцию
            currentContent.push(line);
        }
    }

    // Добавляем последнюю секцию
    if (currentSection && currentContent.length > 0) {
        sections.push({
            name: currentSection,
            content: currentContent.join('\n').trim()
        });
    }

    // Если не удалось разбить, возвращаем весь текст как одну секцию
    if (sections.length === 0 && text.trim()) {
        sections.push({
            name: 'test_cases',
            content: text.trim()
        });
    }

    return sections;
}

// Обновляем функцию generateFullTestPlan для сохранения данных
var originalGenerateFullTestPlan = generateFullTestPlan;
generateFullTestPlan = function(modelData, selectedActions, outputElement) {
    var result = originalGenerateFullTestPlan(modelData, selectedActions, outputElement);

    // Сохраняем данные для возможного экспорта
    if (outputElement && outputElement.value) {
        window.lastTestCaseData = {
            testCases: [
                {
                    type: 'Весь тест план',
                    text: outputElement.value,
                    timestamp: new Date()
                }
            ]
        };
    }

    return result;
};
