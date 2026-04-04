/**
 * SCP Foundation — RESHETO Containment System
 * Single Page Application
 */

// ══════════════════════════════════════════════════════════════════════════════
// API Client
// ══════════════════════════════════════════════════════════════════════════════

const API = {
    async request(method, path, body = null) {
        const opts = {
            method,
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
        };
        if (body) opts.body = JSON.stringify(body);
        const res = await fetch(path, opts);
        if (res.status === 204) return null;
        const data = await res.json().catch(() => null);
        if (!res.ok) throw { status: res.status, ...(data || { error: res.statusText }) };
        return data;
    },
    get:  (p)    => API.request('GET', p),
    post: (p, b) => API.request('POST', p, b),
};

// ══════════════════════════════════════════════════════════════════════════════
// State
// ══════════════════════════════════════════════════════════════════════════════

const State = {
    user: null,
    currentPage: 'login',
};

// ══════════════════════════════════════════════════════════════════════════════
// Toast Notifications
// ══════════════════════════════════════════════════════════════════════════════

function showToast(message, type = 'info') {
    let container = document.querySelector('.toast-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'toast-container';
        document.body.appendChild(container);
    }
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => { toast.remove(); }, 3500);
}

// ══════════════════════════════════════════════════════════════════════════════
// Router
// ══════════════════════════════════════════════════════════════════════════════

function navigate(page) {
    State.currentPage = page;
    window.location.hash = '#/' + page;
    render();
}

function getPage() {
    const hash = window.location.hash.replace('#/', '') || 'login';
    return hash;
}

window.addEventListener('hashchange', () => {
    State.currentPage = getPage();
    render();
});

// ══════════════════════════════════════════════════════════════════════════════
// Helpers
// ══════════════════════════════════════════════════════════════════════════════

function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function badgeClass(val) {
    return (val || '').toLowerCase().replace(/\s+/g, '-');
}

function clearanceName(level) {
    const names = { 1: 'Уровень 1', 2: 'Уровень 2', 3: 'Уровень 3', 4: 'Уровень 4', 5: 'O5 Council' };
    return names[level] || `Уровень ${level}`;
}

function formatDate(dt) {
    if (!dt) return '—';
    return new Date(dt).toLocaleString('ru-RU');
}

// ══════════════════════════════════════════════════════════════════════════════
// Page Renderers
// ══════════════════════════════════════════════════════════════════════════════

function renderAuth() {
    return `
    <div class="auth-container">
        <div class="auth-card">
            <div class="auth-logo">
                <div class="emblem">SCP</div>
                <div class="tagline">Secure · Contain · Protect</div>
                <div style="font-size:0.6rem;color:var(--text-secondary);margin-top:12px;letter-spacing:2px;">
                    RESHETO CONTAINMENT SYSTEM
                </div>
            </div>
            <div class="auth-tabs">
                <div class="auth-tab active" id="tab-login" onclick="switchAuthTab('login')">ВХОД</div>
                <div class="auth-tab" id="tab-register" onclick="switchAuthTab('register')">РЕГИСТРАЦИЯ</div>
            </div>
            <div class="auth-error" id="auth-error"></div>
            <form id="auth-form" onsubmit="handleAuth(event)">
                <div id="auth-fields"></div>
                <button type="submit" class="btn btn-primary" style="width:100%;margin-top:8px;" id="auth-submit">
                    АВТОРИЗОВАТЬСЯ
                </button>
            </form>
        </div>
    </div>`;
}

function switchAuthTab(tab) {
    document.querySelectorAll('.auth-tab').forEach(t => t.classList.remove('active'));
    document.getElementById('tab-' + tab).classList.add('active');
    const fields = document.getElementById('auth-fields');
    const btn = document.getElementById('auth-submit');
    document.getElementById('auth-error').classList.remove('visible');

    if (tab === 'login') {
        btn.textContent = 'АВТОРИЗОВАТЬСЯ';
        fields.innerHTML = `
            <div class="form-group">
                <label>Позывной</label>
                <input class="form-input" name="username" placeholder="agent_smith" required autocomplete="username">
            </div>
            <div class="form-group">
                <label>Пароль</label>
                <input class="form-input" name="password" type="password" placeholder="••••••••" required autocomplete="current-password">
            </div>`;
    } else {
        btn.textContent = 'ЗАРЕГИСТРИРОВАТЬСЯ';
        fields.innerHTML = `
            <div class="form-group">
                <label>Позывной</label>
                <input class="form-input" name="username" placeholder="agent_smith" required>
            </div>
            <div class="form-group">
                <label>Пароль</label>
                <input class="form-input" name="password" type="password" placeholder="••••••••" required>
            </div>
            <div class="form-group">
                <label>Полное имя</label>
                <input class="form-input" name="full_name" placeholder="Агент Смит">
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>Уровень допуска</label>
                    <select class="form-select" name="clearance_level">
                        <option value="1">1 — Общий</option>
                        <option value="2">2 — Ограниченный</option>
                        <option value="3">3 — Секретный</option>
                        <option value="4">4 — Совершенно секретный</option>
                        <option value="5">5 — O5 Council</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Отдел</label>
                    <input class="form-input" name="department" placeholder="Mobile Task Force" value="General">
                </div>
            </div>`;
    }
}

async function handleAuth(e) {
    e.preventDefault();
    const form = new FormData(e.target);
    const tab = document.getElementById('tab-register').classList.contains('active') ? 'register' : 'login';
    const errEl = document.getElementById('auth-error');

    const body = {};
    for (const [k, v] of form.entries()) {
        body[k] = k === 'clearance_level' ? parseInt(v) : v;
    }

    try {
        const user = await API.post(`/api/auth/${tab}`, body);
        State.user = user;
        showToast(`Добро пожаловать, ${user.username}`, 'success');
        navigate('dashboard');
    } catch (err) {
        errEl.textContent = err.error || 'Ошибка авторизации';
        errEl.classList.add('visible');
    }
}

// ── Dashboard ────────────────────────────────────────────────────────────────

async function renderDashboard() {
    const app = document.getElementById('app');
    app.innerHTML = layoutWrap('dashboard', `
        <div class="page-header">
            <h1>⬡ Панель управления</h1>
            <div class="breadcrumb">SCP Foundation / Resheto / Dashboard</div>
        </div>
        <div class="loading-container"><div class="spinner"></div> Загрузка данных...</div>
    `);

    try {
        const [anomalies, reports, research, incidents] = await Promise.all([
            API.get('/api/anomalies'),
            API.get('/api/reports'),
            API.get('/api/research'),
            API.get('/api/incidents'),
        ]);

        const content = `
        <div class="page-header">
            <h1>⬡ Панель управления</h1>
            <div class="breadcrumb">SCP Foundation / Resheto / Dashboard</div>
        </div>
        <div class="stats-grid">
            <div class="stat-card red">
                <div class="stat-value">${anomalies.length}</div>
                <div class="stat-label">Аномалий</div>
            </div>
            <div class="stat-card amber">
                <div class="stat-value">${reports.length}</div>
                <div class="stat-label">Отчётов</div>
            </div>
            <div class="stat-card cyan">
                <div class="stat-value">${research.length}</div>
                <div class="stat-label">Исследований</div>
            </div>
            <div class="stat-card green">
                <div class="stat-value">${incidents.length}</div>
                <div class="stat-label">Инцидентов</div>
            </div>
        </div>
        <div class="panel">
            <div class="panel-header">
                <span class="panel-title">Последние аномалии</span>
                <button class="btn btn-sm" onclick="navigate('anomalies/new')">+ Добавить</button>
            </div>
            <table class="data-table">
                <thead><tr><th>SCP ID</th><th>Класс</th><th>Название</th><th>Допуск</th></tr></thead>
                <tbody>
                    ${anomalies.slice(0, 5).map(a => `
                        <tr class="clickable" onclick="navigate('anomalies/${a.id}')">
                            <td style="color:var(--accent-red);font-weight:600">${escapeHtml(a.scp_id)}</td>
                            <td><span class="badge ${badgeClass(a.object_class)}">${escapeHtml(a.object_class)}</span></td>
                            <td>${escapeHtml(a.title)}</td>
                            <td>${a.min_clearance}</td>
                        </tr>
                    `).join('') || '<tr><td colspan="4" style="text-align:center;color:var(--text-secondary)">Нет записей</td></tr>'}
                </tbody>
            </table>
        </div>
        <div class="panel">
            <div class="panel-header">
                <span class="panel-title">Активные исследования</span>
            </div>
            <table class="data-table">
                <thead><tr><th>UUID</th><th>Объект</th><th>Статус</th><th>Дата</th></tr></thead>
                <tbody>
                    ${research.slice(0, 5).map(r => `
                        <tr>
                            <td style="font-size:0.75rem;color:var(--accent-cyan)">${escapeHtml(r.uuid)}</td>
                            <td>${escapeHtml(r.scp_id || '—')}</td>
                            <td><span class="badge ${badgeClass(r.status)}">${r.status}</span></td>
                            <td style="font-size:0.75rem">${formatDate(r.created_at)}</td>
                        </tr>
                    `).join('') || '<tr><td colspan="4" style="text-align:center;color:var(--text-secondary)">Нет исследований</td></tr>'}
                </tbody>
            </table>
        </div>`;
        document.querySelector('.main-content').innerHTML = content;
    } catch (err) {
        showToast(err.error || 'Ошибка загрузки', 'error');
    }
}

// ── Anomalies ────────────────────────────────────────────────────────────────

async function renderAnomalies() {
    const app = document.getElementById('app');
    app.innerHTML = layoutWrap('anomalies', `
        <div class="page-header">
            <h1>☣ База аномалий</h1>
            <div class="breadcrumb">SCP Foundation / Resheto / Anomalies</div>
        </div>
        <div class="loading-container"><div class="spinner"></div> Загрузка...</div>
    `);

    try {
        const anomalies = await API.get('/api/anomalies');
        let html = `
        <div class="page-header">
            <h1>☣ База аномалий</h1>
            <div class="breadcrumb">SCP Foundation / Resheto / Anomalies</div>
        </div>
        <div style="margin-bottom:16px;display:flex;gap:8px;flex-wrap:wrap">
            <button class="btn btn-primary" onclick="navigate('anomalies/new')">+ Зарегистрировать аномалию</button>
            <button class="btn" onclick="navigate('anomalies/search')">🔍 Поиск</button>
        </div>
        <div class="panel">
            <table class="data-table">
                <thead><tr><th>SCP ID</th><th>Класс</th><th>Название</th><th>Мин. допуск</th><th></th><th>Дата</th></tr></thead>
                <tbody>
                    ${anomalies.map(a => `
                        <tr class="clickable" onclick="navigate('anomalies/${a.id}')">
                            <td style="color:var(--accent-red);font-weight:600">${escapeHtml(a.scp_id)}</td>
                            <td><span class="badge ${badgeClass(a.object_class)}">${escapeHtml(a.object_class)}</span></td>
                            <td>${escapeHtml(a.title)}</td>
                            <td>${a.min_clearance}</td>
                            <td>${a.is_private ? '<span class="badge" style="background:rgba(233,69,96,0.2);color:var(--accent-red);border:1px solid rgba(233,69,96,0.4)">🔒 СКРЫТ</span>' : ''}</td>
                            <td style="font-size:0.75rem">${formatDate(a.created_at)}</td>
                        </tr>
                    `).join('') || '<tr><td colspan="6"><div class="empty-state"><div class="icon">☣</div><div class="message">Аномалии не обнаружены</div></div></td></tr>'}
                </tbody>
            </table>
        </div>`;
        document.querySelector('.main-content').innerHTML = html;
    } catch (err) {
        showToast(err.error || 'Ошибка', 'error');
    }
}

// ── Anomaly Search ───────────────────────────────────────────────────────────

function renderAnomalySearch() {
    return layoutWrap('anomalies', `
        <div class="page-header">
            <h1>🔍 Поиск аномалий</h1>
            <div class="breadcrumb">SCP Foundation / Resheto / Anomalies / Search</div>
        </div>
        <div class="panel">
            <div class="panel-header"><span class="panel-title">Параметры поиска</span></div>
            <form onsubmit="handleSearchAnomalies(event)">
                <div class="form-row">
                    <div class="form-group">
                        <label>SCP ID</label>
                        <input class="form-input" name="scp_id" placeholder="SCP-XXXX">
                    </div>
                    <div class="form-group">
                        <label>Класс объекта</label>
                        <select class="form-select" name="object_class">
                            <option value="">— Любой —</option>
                            <option value="Safe">Safe</option>
                            <option value="Euclid">Euclid</option>
                            <option value="Keter">Keter</option>
                            <option value="Thaumiel">Thaumiel</option>
                            <option value="Neutralized">Neutralized</option>
                            <option value="Apollyon">Apollyon</option>
                        </select>
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label>Название</label>
                        <input class="form-input" name="title" placeholder="Точное совпадение">
                    </div>
                    <div class="form-group">
                        <label>Мин. допуск</label>
                        <select class="form-select" name="min_clearance">
                            <option value="">— Любой —</option>
                            <option value="1">1</option><option value="2">2</option>
                            <option value="3">3</option><option value="4">4</option>
                            <option value="5">5</option>
                        </select>
                    </div>
                </div>
                <div class="form-group">
                    <label>Описание (текстовый поиск)</label>
                    <input class="form-input" name="description" placeholder="Фрагмент описания...">
                </div>
                <div class="form-group">
                    <label>Процедуры содержания (текстовый поиск)</label>
                    <input class="form-input" name="containment_procedures" placeholder="Фрагмент процедур...">
                </div>
                <button type="submit" class="btn btn-primary">🔍 Искать</button>
                <button type="button" class="btn" onclick="navigate('anomalies')" style="margin-left:8px">← Назад</button>
            </form>
        </div>
        <div id="search-results"></div>
    `);
}

async function handleSearchAnomalies(e) {
    e.preventDefault();
    const form = new FormData(e.target);
    const body = {};
    for (const [k, v] of form.entries()) {
        if (v !== '') {
            body[k] = (k === 'min_clearance') ? parseInt(v) : v;
        }
    }
    const resultsDiv = document.getElementById('search-results');
    resultsDiv.innerHTML = '<div class="loading-container"><div class="spinner"></div> Поиск...</div>';
    try {
        const results = await API.post('/api/anomalies/search', body);
        resultsDiv.innerHTML = `
        <div class="panel" style="margin-top:16px">
            <div class="panel-header">
                <span class="panel-title">Результаты: ${results.length}</span>
            </div>
            <table class="data-table">
                <thead><tr><th>SCP ID</th><th>Класс</th><th>Название</th><th>Допуск</th><th></th></tr></thead>
                <tbody>
                    ${results.map(a => `
                        <tr class="clickable" onclick="navigate('anomalies/${a.id}')">
                            <td style="color:var(--accent-red);font-weight:600">${escapeHtml(a.scp_id)}</td>
                            <td><span class="badge ${badgeClass(a.object_class)}">${escapeHtml(a.object_class)}</span></td>
                            <td>${escapeHtml(a.title)}</td>
                            <td>${a.min_clearance}</td>
                            <td>${a.is_private ? '<span class="badge" style="background:rgba(233,69,96,0.2);color:var(--accent-red);border:1px solid rgba(233,69,96,0.4)">🔒</span>' : ''}</td>
                        </tr>
                    `).join('') || '<tr><td colspan="5" style="text-align:center;color:var(--text-secondary)">Ничего не найдено</td></tr>'}
                </tbody>
            </table>
        </div>`;
    } catch (err) {
        resultsDiv.innerHTML = '';
        showToast(err.error || 'Ошибка поиска', 'error');
    }
}

function renderAnomalyForm() {
    return layoutWrap('anomalies', `
        <div class="page-header">
            <h1>☣ Новая аномалия</h1>
            <div class="breadcrumb">SCP Foundation / Resheto / Anomalies / New</div>
        </div>
        <div class="panel">
            <form onsubmit="handleCreateAnomaly(event)">
                <div class="form-row">
                    <div class="form-group">
                        <label>SCP ID</label>
                        <input class="form-input" name="scp_id" placeholder="SCP-XXXX" required>
                    </div>
                    <div class="form-group">
                        <label>Класс объекта</label>
                        <select class="form-select" name="object_class" required>
                            <option value="Safe">Safe</option>
                            <option value="Euclid" selected>Euclid</option>
                            <option value="Keter">Keter</option>
                            <option value="Thaumiel">Thaumiel</option>
                            <option value="Neutralized">Neutralized</option>
                            <option value="Apollyon">Apollyon</option>
                        </select>
                    </div>
                </div>
                <div class="form-group">
                    <label>Название</label>
                    <input class="form-input" name="title" placeholder="Краткое описание объекта" required>
                </div>
                <div class="form-group">
                    <label>Описание</label>
                    <textarea class="form-textarea" name="description" placeholder="Подробное описание аномальных свойств объекта..." required></textarea>
                </div>
                <div class="form-group">
                    <label>Процедуры содержания</label>
                    <textarea class="form-textarea" name="containment_procedures" placeholder="Специальные условия содержания..." required></textarea>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label>Минимальный уровень допуска</label>
                        <select class="form-select" name="min_clearance">
                            <option value="1">1</option><option value="2">2</option><option value="3">3</option>
                            <option value="4">4</option><option value="5">5</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label style="display:flex;align-items:center;gap:8px;margin-top:24px;cursor:pointer">
                            <input type="checkbox" name="is_private" value="1" style="width:18px;height:18px;accent-color:var(--accent-red)">
                            <span>🔒 Скрытая аномалия <span style="color:var(--text-secondary);font-size:0.6rem">(видна только вам)</span></span>
                        </label>
                    </div>
                </div>
                <button type="submit" class="btn btn-primary">Зарегистрировать</button>
                <button type="button" class="btn" onclick="navigate('anomalies')" style="margin-left:8px">Отмена</button>
            </form>
        </div>
    `);
}

async function handleCreateAnomaly(e) {
    e.preventDefault();
    const form = new FormData(e.target);
    const body = {};
    for (const [k, v] of form.entries()) {
        if (k === 'min_clearance') body[k] = parseInt(v);
        else if (k === 'is_private') body[k] = true;
        else body[k] = v;
    }
    if (!body.is_private) body.is_private = false;
    try {
        const a = await API.post('/api/anomalies', body);
        showToast(`Аномалия ${a.scp_id} зарегистрирована${a.is_private ? ' (скрытая)' : ''}`, 'success');
        navigate('anomalies/' + a.id);
    } catch (err) {
        showToast(err.error || 'Ошибка создания', 'error');
    }
}

async function renderAnomalyDetail(id) {
    const app = document.getElementById('app');
    app.innerHTML = layoutWrap('anomalies', `<div class="loading-container"><div class="spinner"></div></div>`);
    try {
        const a = await API.get(`/api/anomalies/${id}`);
        document.querySelector('.main-content').innerHTML = `
            <div class="page-header">
                <h1 style="color:var(--accent-red)">${escapeHtml(a.scp_id)}</h1>
                <div class="breadcrumb">SCP Foundation / Anomalies / ${escapeHtml(a.scp_id)}</div>
            </div>
            <div class="panel">
                <div class="panel-header">
                    <span class="panel-title">Карточка объекта</span>
                    <span style="display:flex;gap:6px;align-items:center">
                        ${a.is_private ? '<span class="badge" style="background:rgba(233,69,96,0.2);color:var(--accent-red);border:1px solid rgba(233,69,96,0.4)">🔒 СКРЫТЫЙ</span>' : ''}
                        <span class="badge ${badgeClass(a.object_class)}">${escapeHtml(a.object_class)}</span>
                    </span>
                </div>
                <div class="detail-grid">
                    <div class="detail-label">SCP ID</div>
                    <div class="detail-value" style="color:var(--accent-red);font-weight:600">${escapeHtml(a.scp_id)}</div>
                    <div class="detail-label">Название</div>
                    <div class="detail-value">${escapeHtml(a.title)}</div>
                    <div class="detail-label">Класс</div>
                    <div class="detail-value"><span class="badge ${badgeClass(a.object_class)}">${escapeHtml(a.object_class)}</span></div>
                    <div class="detail-label">Видимость</div>
                    <div class="detail-value">${a.is_private ? '<span style="color:var(--accent-red)">🔒 Скрытый (только для вас)</span>' : '<span style="color:var(--accent-green)">🌐 Публичный</span>'}</div>
                    <div class="detail-label">Мин. допуск</div>
                    <div class="detail-value">${clearanceName(a.min_clearance)}</div>
                    <div class="detail-label">Зарегистрирован</div>
                    <div class="detail-value">${formatDate(a.created_at)}</div>
                </div>
            </div>
            <div class="panel">
                <div class="panel-header"><span class="panel-title">Описание</span></div>
                <div style="white-space:pre-wrap;line-height:1.6">${escapeHtml(a.description)}</div>
            </div>
            <div class="panel">
                <div class="panel-header"><span class="panel-title">Процедуры содержания</span></div>
                <div style="white-space:pre-wrap;line-height:1.6">${escapeHtml(a.containment_procedures)}</div>
            </div>
            <div style="margin-top:16px;display:flex;gap:8px;">
                <button class="btn btn-primary" onclick="submitResearchFromAnomaly(${a.id})">🔬 Отправить на исследование</button>
                <button class="btn" onclick="navigate('anomalies')">← Назад</button>
            </div>
        `;
    } catch (err) {
        showToast(err.error || 'Ошибка загрузки', 'error');
        navigate('anomalies');
    }
}

async function submitResearchFromAnomaly(anomalyId) {
    const notes = prompt('Заметки исследователя (необязательно):');
    try {
        const r = await API.post('/api/research', { anomaly_id: anomalyId, notes: notes || '' });
        showToast(`Исследование создано: ${r.uuid}`, 'success');
        navigate('research');
    } catch (err) {
        showToast(err.error || 'Ошибка', 'error');
    }
}

// ── Reports ──────────────────────────────────────────────────────────────────

async function renderReports() {
    const app = document.getElementById('app');
    app.innerHTML = layoutWrap('reports', `<div class="loading-container"><div class="spinner"></div></div>`);
    try {
        const reports = await API.get('/api/reports');
        document.querySelector('.main-content').innerHTML = `
        <div class="page-header">
            <h1>📋 База знаний</h1>
            <div class="breadcrumb">SCP Foundation / Resheto / Reports</div>
        </div>
        <div style="margin-bottom:16px"><button class="btn btn-primary" onclick="navigate('reports/new')">+ Новый отчёт</button></div>
        <div class="panel">
            <table class="data-table">
                <thead><tr><th>UUID</th><th>Название</th><th>Классификация</th><th>PDF</th><th>Дата</th></tr></thead>
                <tbody>
                    ${reports.map(r => `
                        <tr class="clickable" onclick="navigate('reports/${r.uuid}')">
                            <td style="font-size:0.7rem;color:var(--accent-cyan)">${escapeHtml(r.uuid).substring(0,8)}…</td>
                            <td>${escapeHtml(r.title)}</td>
                            <td><span class="classified-stamp" style="font-size:0.55rem;padding:1px 6px;transform:none">${escapeHtml(r.classification)}</span></td>
                            <td>${r.pdf_path ? '✅' : '❌'}</td>
                            <td style="font-size:0.75rem">${formatDate(r.created_at)}</td>
                        </tr>
                    `).join('') || '<tr><td colspan="5"><div class="empty-state"><div class="icon">📋</div><div class="message">Отчёты ещё не созданы</div></div></td></tr>'}
                </tbody>
            </table>
        </div>`;
    } catch (err) { showToast(err.error || 'Ошибка', 'error'); }
}

function renderReportForm() {
    return layoutWrap('reports', `
        <div class="page-header">
            <h1>📋 Новый отчёт</h1>
            <div class="breadcrumb">SCP Foundation / Resheto / Reports / New</div>
        </div>
        <div class="panel">
            <form onsubmit="handleCreateReport(event)">
                <div class="form-group">
                    <label>Название</label>
                    <input class="form-input" name="title" placeholder="Отчёт об инциденте #42" required>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label>Классификация</label>
                        <select class="form-select" name="classification">
                            <option value="UNCLASSIFIED">Unclassified</option>
                            <option value="CONFIDENTIAL" selected>Confidential</option>
                            <option value="SECRET">Secret</option>
                            <option value="TOP SECRET">Top Secret</option>
                            <option value="LEVEL-5">Level-5</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>ID аномалии (необязательно)</label>
                        <input class="form-input" name="anomaly_id" type="number" placeholder="">
                    </div>
                </div>
                <div class="form-group">
                    <label>Содержание (Markdown)</label>
                    <textarea class="form-textarea" name="content_markdown" style="min-height:300px"
                        placeholder="# Заголовок отчёта&#10;&#10;## Описание инцидента&#10;&#10;Объект **SCP-XXXX** проявил аномальную активность...&#10;&#10;> Рекомендации по усилению процедур содержания&#10;&#10;- Пункт 1&#10;- Пункт 2" required></textarea>
                </div>
                <button type="submit" class="btn btn-primary">Создать отчёт и сгенерировать PDF</button>
                <button type="button" class="btn" onclick="navigate('reports')" style="margin-left:8px">Отмена</button>
            </form>
        </div>
    `);
}

async function handleCreateReport(e) {
    e.preventDefault();
    const form = new FormData(e.target);
    const body = {};
    for (const [k, v] of form.entries()) {
        if (k === 'anomaly_id') body[k] = v ? parseInt(v) : null;
        else body[k] = v;
    }
    try {
        const r = await API.post('/api/reports', body);
        showToast('Отчёт создан, PDF сгенерирован', 'success');
        navigate('reports/' + r.uuid);
    } catch (err) {
        showToast(err.error || 'Ошибка создания', 'error');
    }
}

async function renderReportDetail(uuid) {
    const app = document.getElementById('app');
    app.innerHTML = layoutWrap('reports', `<div class="loading-container"><div class="spinner"></div></div>`);
    try {
        const r = await API.get(`/api/reports/${uuid}`);
        document.querySelector('.main-content').innerHTML = `
            <div class="page-header">
                <h1>${escapeHtml(r.title)}</h1>
                <div class="breadcrumb">Reports / ${escapeHtml(r.uuid)}</div>
            </div>
            <div class="panel">
                <div class="panel-header">
                    <span class="panel-title">Метаданные</span>
                    <span class="classified-stamp">${escapeHtml(r.classification)}</span>
                </div>
                <div class="detail-grid">
                    <div class="detail-label">UUID</div>
                    <div class="detail-value" style="color:var(--accent-cyan)">${escapeHtml(r.uuid)}</div>
                    <div class="detail-label">Классификация</div>
                    <div class="detail-value">${escapeHtml(r.classification)}</div>
                    <div class="detail-label">Дата создания</div>
                    <div class="detail-value">${formatDate(r.created_at)}</div>
                </div>
            </div>
            <div class="panel">
                <div class="panel-header"><span class="panel-title">Содержание</span></div>
                <div class="markdown-content" style="white-space:pre-wrap">${escapeHtml(r.content_markdown)}</div>
            </div>
            <div style="margin-top:16px;display:flex;gap:8px;">
                ${r.pdf_path ? `<a href="/api/reports/${r.uuid}/pdf" target="_blank" class="btn btn-success">📥 Скачать PDF</a>` : ''}
                <button class="btn" onclick="navigate('reports')">← Назад</button>
            </div>
        `;
    } catch (err) {
        showToast(err.error || 'Ошибка', 'error');
        navigate('reports');
    }
}

// ── Research ─────────────────────────────────────────────────────────────────

async function renderResearch() {
    const app = document.getElementById('app');
    app.innerHTML = layoutWrap('research', `<div class="loading-container"><div class="spinner"></div></div>`);
    try {
        const tasks = await API.get('/api/research');
        document.querySelector('.main-content').innerHTML = `
        <div class="page-header">
            <h1>🔬 Лаборатория</h1>
            <div class="breadcrumb">SCP Foundation / Resheto / Research Lab</div>
        </div>
        <div class="panel">
            <div class="panel-header">
                <span class="panel-title">Мои исследования</span>
            </div>
            <table class="data-table">
                <thead><tr><th>UUID</th><th>Объект</th><th>Статус</th><th>Архив</th><th>Дата</th></tr></thead>
                <tbody>
                    ${tasks.map(t => `
                        <tr class="clickable" onclick="viewResearch('${escapeHtml(t.uuid)}')">
                            <td style="font-size:0.7rem;color:var(--accent-cyan)">${escapeHtml(t.uuid).substring(0,8)}…</td>
                            <td>${escapeHtml(t.scp_id || '')} ${escapeHtml(t.anomaly_title || '')}</td>
                            <td><span class="badge ${badgeClass(t.status)}">${t.status}</span></td>
                            <td style="font-size:0.7rem">${t.archive_uuid ? escapeHtml(t.archive_uuid).substring(0,8) + '…' : '—'}</td>
                            <td style="font-size:0.75rem">${formatDate(t.created_at)}</td>
                        </tr>
                    `).join('') || '<tr><td colspan="5"><div class="empty-state"><div class="icon">🔬</div><div class="message">Нет активных исследований</div></div></td></tr>'}
                </tbody>
            </table>
        </div>`;
    } catch (err) { showToast(err.error || 'Ошибка', 'error'); }
}

async function viewResearch(uuid) {
    try {
        const r = await API.get(`/api/research/${uuid}`);
        const overlay = document.createElement('div');
        overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.8);z-index:1000;display:flex;align-items:center;justify-content:center;padding:20px;';
        overlay.onclick = (e) => { if (e.target === overlay) overlay.remove(); };
        overlay.innerHTML = `
            <div class="panel" style="max-width:700px;width:100%;max-height:80vh;overflow-y:auto;">
                <div class="panel-header">
                    <span class="panel-title">Исследование ${escapeHtml(uuid).substring(0,8)}…</span>
                    <span class="badge ${badgeClass(r.status)}">${r.status}</span>
                </div>
                <div class="detail-grid">
                    <div class="detail-label">UUID</div><div class="detail-value" style="color:var(--accent-cyan)">${escapeHtml(r.uuid)}</div>
                    <div class="detail-label">Статус</div><div class="detail-value">${r.status}</div>
                    <div class="detail-label">Заметки</div><div class="detail-value">${escapeHtml(r.researcher_notes) || '—'}</div>
                </div>
                ${r.archive_content ? `
                    <div style="margin-top:16px;padding-top:16px;border-top:1px solid var(--border)">
                        <div class="detail-label" style="margin-bottom:8px">Результат исследования</div>
                        <pre style="background:var(--bg-input);padding:16px;border-radius:6px;white-space:pre-wrap;font-size:0.8rem;color:var(--terminal-green);border:1px solid var(--border)">${escapeHtml(r.archive_content)}</pre>
                    </div>
                ` : ''}
                <button class="btn" onclick="this.closest('div[style]').remove()" style="margin-top:16px">Закрыть</button>
            </div>
        `;
        document.body.appendChild(overlay);
    } catch (err) { showToast(err.error || 'Ошибка', 'error'); }
}

// ── Incidents ────────────────────────────────────────────────────────────────

async function renderIncidents() {
    const app = document.getElementById('app');
    app.innerHTML = layoutWrap('incidents', `<div class="loading-container"><div class="spinner"></div></div>`);
    try {
        const incidents = await API.get('/api/incidents');
        document.querySelector('.main-content').innerHTML = `
        <div class="page-header">
            <h1>⚠ Журнал инцидентов</h1>
            <div class="breadcrumb">SCP Foundation / Resheto / Incidents</div>
        </div>
        <div style="margin-bottom:16px"><button class="btn btn-primary" onclick="navigate('incidents/new')">+ Зафиксировать инцидент</button></div>
        <div class="panel">
            <table class="data-table">
                <thead><tr><th>UUID</th><th>Объект</th><th>Серьёзность</th><th>Описание</th><th>Дата</th></tr></thead>
                <tbody>
                    ${incidents.map(i => `
                        <tr>
                            <td style="font-size:0.7rem;color:var(--accent-cyan)">${escapeHtml(i.uuid).substring(0,8)}…</td>
                            <td>${escapeHtml(i.scp_id || '—')}</td>
                            <td><span class="badge ${badgeClass(i.severity)}">${i.severity}</span></td>
                            <td style="max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${escapeHtml(i.description)}</td>
                            <td style="font-size:0.75rem">${formatDate(i.created_at)}</td>
                        </tr>
                    `).join('') || '<tr><td colspan="5"><div class="empty-state"><div class="icon">⚠</div><div class="message">Инцидентов не зафиксировано</div></div></td></tr>'}
                </tbody>
            </table>
        </div>`;
    } catch (err) { showToast(err.error || 'Ошибка', 'error'); }
}

function renderIncidentForm() {
    return layoutWrap('incidents', `
        <div class="page-header">
            <h1>⚠ Новый инцидент</h1>
            <div class="breadcrumb">SCP Foundation / Resheto / Incidents / New</div>
        </div>
        <div class="panel">
            <form onsubmit="handleCreateIncident(event)">
                <div class="form-row">
                    <div class="form-group">
                        <label>ID аномалии (необязательно)</label>
                        <input class="form-input" name="anomaly_id" type="number" placeholder="">
                    </div>
                    <div class="form-group">
                        <label>Серьёзность</label>
                        <select class="form-select" name="severity" required>
                            <option value="LOW">LOW</option>
                            <option value="MEDIUM" selected>MEDIUM</option>
                            <option value="HIGH">HIGH</option>
                            <option value="CRITICAL">CRITICAL</option>
                        </select>
                    </div>
                </div>
                <div class="form-group">
                    <label>Описание инцидента</label>
                    <textarea class="form-textarea" name="description" placeholder="Подробное описание произошедшего..." required></textarea>
                </div>
                <div class="form-group">
                    <label>Заметки по реагированию</label>
                    <textarea class="form-textarea" name="response_notes" placeholder="Действия, предпринятые для ликвидации последствий..."></textarea>
                </div>
                <button type="submit" class="btn btn-primary">Зафиксировать</button>
                <button type="button" class="btn" onclick="navigate('incidents')" style="margin-left:8px">Отмена</button>
            </form>
        </div>
    `);
}

async function handleCreateIncident(e) {
    e.preventDefault();
    const form = new FormData(e.target);
    const body = {};
    for (const [k, v] of form.entries()) {
        if (k === 'anomaly_id') body[k] = v ? parseInt(v) : null;
        else body[k] = v;
    }
    try {
        await API.post('/api/incidents', body);
        showToast('Инцидент зафиксирован', 'success');
        navigate('incidents');
    } catch (err) { showToast(err.error || 'Ошибка', 'error'); }
}

// ══════════════════════════════════════════════════════════════════════════════
// Layout
// ══════════════════════════════════════════════════════════════════════════════

function layoutWrap(activePage, content) {
    const user = State.user;
    const navItems = [
        { id: 'dashboard',  icon: '⬡', label: 'Панель управления' },
        { id: 'anomalies',  icon: '☣', label: 'База аномалий' },
        { id: 'reports',    icon: '📋', label: 'База знаний' },
        { id: 'research',   icon: '🔬', label: 'Лаборатория' },
        { id: 'incidents',  icon: '⚠', label: 'Инциденты' },
    ];

    return `
    <div class="layout">
        <div class="sidebar">
            <div class="sidebar-logo">
                <div class="scp-emblem">SCP</div>
                <div class="subtitle">Resheto System</div>
            </div>
            <nav class="sidebar-nav">
                <div class="nav-section-title">Навигация</div>
                ${navItems.map(n => `
                    <div class="nav-item ${activePage.startsWith(n.id) ? 'active' : ''}" onclick="navigate('${n.id}')">
                        <span class="icon">${n.icon}</span> ${n.label}
                    </div>
                `).join('')}
            </nav>
            ${user ? `
            <div class="sidebar-user">
                <div class="user-name">▸ ${escapeHtml(user.username)}</div>
                <div class="user-clearance">Допуск: ${clearanceName(user.clearance_level)}</div>
                <div class="logout-btn" onclick="handleLogout()">[ ВЫХОД ]</div>
            </div>` : ''}
        </div>
        <div class="main-content">${content}</div>
    </div>`;
}

async function handleLogout() {
    try { await API.post('/api/auth/logout'); } catch {}
    State.user = null;
    navigate('login');
}

// ══════════════════════════════════════════════════════════════════════════════
// Main Render
// ══════════════════════════════════════════════════════════════════════════════

async function render() {
    const page = State.currentPage;
    const app = document.getElementById('app');

    // Auth pages
    if (page === 'login' || page === 'register') {
        app.innerHTML = renderAuth();
        setTimeout(() => switchAuthTab(page === 'register' ? 'register' : 'login'), 0);
        return;
    }

    // Check auth
    if (!State.user) {
        try {
            State.user = await API.get('/api/auth/me');
        } catch {
            navigate('login');
            return;
        }
    }

    // Route
    if (page === 'dashboard')          { await renderDashboard(); }
    else if (page === 'anomalies')        { await renderAnomalies(); }
    else if (page === 'anomalies/new')    { app.innerHTML = renderAnomalyForm(); }
    else if (page === 'anomalies/search') { app.innerHTML = renderAnomalySearch(); }
    else if (page.startsWith('anomalies/')) { await renderAnomalyDetail(page.split('/')[1]); }
    else if (page === 'reports')       { await renderReports(); }
    else if (page === 'reports/new')   { app.innerHTML = renderReportForm(); }
    else if (page.startsWith('reports/')) { await renderReportDetail(page.split('/')[1]); }
    else if (page === 'research')      { await renderResearch(); }
    else if (page === 'incidents')     { await renderIncidents(); }
    else if (page === 'incidents/new') { app.innerHTML = renderIncidentForm(); }
    else                               { navigate('dashboard'); }
}

// Boot
document.addEventListener('DOMContentLoaded', () => {
    State.currentPage = getPage();
    render();
});
