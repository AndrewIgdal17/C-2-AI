const API_BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? 'http://localhost:8000'
    : '';

let isProcessing = false;

document.addEventListener('DOMContentLoaded', async () => {
    try {
        const resp = await fetch(`${API_BASE}/api/config`);
        if (resp.ok) {
            const config = await resp.json();
            const link = document.getElementById('grafana-link');
            if (config.grafana_url) link.href = config.grafana_url;
        }
    } catch (e) {}
});

function askExample(btn) {
    document.getElementById('question-input').value = btn.textContent.trim();
    handleSubmit(new Event('submit'));
}

function processSSEBuffer(buffer, eventType, responseDiv, logContainer) {
    const lines = buffer.split('\n');
    const remaining = lines.pop();
    let currentEvent = eventType;
    for (const line of lines) {
        const trimmed = line.trim();
        if (trimmed.startsWith('event:')) {
            currentEvent = trimmed.slice(6).trim();
        } else if (trimmed.startsWith('data:') && currentEvent) {
            try {
                const data = JSON.parse(trimmed.slice(5).trim());
                handleEvent(currentEvent, data, responseDiv, logContainer);
            } catch (e) {}
            currentEvent = null;
        }
    }
    return { remaining, eventType: currentEvent };
}

async function handleSubmit(event) {
    event.preventDefault();
    if (isProcessing) return;
    const input = document.getElementById('question-input');
    const question = input.value.trim();
    if (!question) return;

    isProcessing = true;
    document.getElementById('send-btn').disabled = true;
    input.value = '';

    const requestStart = performance.now();

    addMessage(question, 'user');
    const responseDiv = addMessage('', 'assistant');
    const logContainer = addLogPanel(responseDiv);
    logContainer._startTime = requestStart;

    try {
        const resp = await fetch(`${API_BASE}/api/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question }),
        });
        if (!resp.ok) throw new Error(`Server error: ${resp.status}`);

        const reader = resp.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let eventType = null;

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });
            const result = processSSEBuffer(buffer, eventType, responseDiv, logContainer);
            buffer = result.remaining;
            eventType = result.eventType;
        }
        if (buffer.trim()) {
            buffer += '\n';
            processSSEBuffer(buffer, eventType, responseDiv, logContainer);
        }
    } catch (err) {
        const content = responseDiv.querySelector('.message-content');
        if (!content.querySelector('.report-text') && !content.querySelector('.stats-panel')) {
            content.innerHTML = `<div class="error-message">Failed to get a response: ${err.message}</div>`;
        }
    } finally {
        const collapseBtn = logContainer.querySelector('.log-collapse-btn');
        if (collapseBtn) collapseBtn.click();
        isProcessing = false;
        document.getElementById('send-btn').disabled = false;
        document.getElementById('question-input').focus();
    }
}

const AGENT_ICONS = {
    orchestrator: '\u2699',
    statistics: '\ud83d\udcca',
    visualization: '\ud83c\udfa8',
    query: '\ud83d\uddc4',
};

const AGENT_COLORS = {
    orchestrator: '#0072f5',
    statistics: '#17b169',
    visualization: '#f5a623',
    query: '#8e4ec6',
};

function handleEvent(type, data, container, logContainer) {
    const content = container.querySelector('.message-content');

    switch (type) {
        case 'log': {
            const agent = data.agent || 'system';
            const msg = data.message || '';
            addLogEntry(logContainer, agent, msg);
            break;
        }

        case 'status': {
            const msg = data.message || '';
            addLogEntry(logContainer, 'orchestrator', msg);
            break;
        }

        case 'statistics':
            renderStatistics(content, data);
            break;

        case 'charts':
            renderCharts(content, data);
            break;

        case 'report': {
            let text = (data.text || '').trim();
            text = text.replace(/<think>[\s\S]*?<\/think>/gi, '').trim();
            if (text) {
                const reportDiv = document.createElement('div');
                reportDiv.className = 'report-text';
                reportDiv.innerHTML = formatReport(text);
                content.prepend(reportDiv);
            }
            break;
        }

        case 'error': {
            addLogEntry(logContainer, 'system', `Error: ${data.message || 'Unknown error'}`);
            break;
        }

        case 'done': {
            const startTime = logContainer._startTime || performance.now();
            const total = ((performance.now() - startTime) / 1000).toFixed(1);
            addLogEntry(logContainer, 'orchestrator', `Complete (${total}s)`);
            break;
        }
    }

    document.getElementById('chat-container').scrollTop =
        document.getElementById('chat-container').scrollHeight;
}

function addLogPanel(container) {
    const panel = document.createElement('div');
    panel.className = 'log-panel';

    const header = document.createElement('div');
    header.className = 'log-header';
    header.innerHTML = `
        <span class="log-title"><span class="dot"></span> Agent Activity</span>
        <button class="log-collapse-btn">Collapse</button>
    `;
    panel.appendChild(header);

    const body = document.createElement('div');
    body.className = 'log-body';
    panel.appendChild(body);

    header.querySelector('.log-collapse-btn').addEventListener('click', function() {
        body.classList.toggle('collapsed');
        this.textContent = body.classList.contains('collapsed') ? 'Expand' : 'Collapse';
    });

    container.appendChild(panel);
    return panel;
}

function addLogEntry(logContainer, agent, message) {
    const body = logContainer.querySelector('.log-body');
    if (!body) return;

    const entry = document.createElement('div');
    entry.className = 'log-entry';

    const icon = AGENT_ICONS[agent] || '\u2022';
    const color = AGENT_COLORS[agent] || '#666666';

    const startTime = logContainer._startTime || performance.now();
    const elapsed = ((performance.now() - startTime) / 1000).toFixed(1);

    entry.innerHTML = `<span class="log-time">${elapsed}s</span>`
        + `<span class="log-agent" style="color:${color}">${icon} ${agent}</span>`
        + `<span class="log-msg">${escapeHtml(message)}</span>`;

    body.appendChild(entry);
    body.scrollTop = body.scrollHeight;

    const title = logContainer.querySelector('.log-title');
    if (title) {
        title.innerHTML = `<span class="dot"></span> ${escapeHtml(message).slice(0, 60)}`;
    }
}

function formatReport(text) {
    return text.split(/\n{2,}/).filter(p => p.trim())
        .map(p => `<p>${escapeHtml(p.trim())}</p>`).join('');
}

function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function renderStatistics(container, data) {
    const panel = document.createElement('div');
    panel.className = 'stats-panel';

    if (data.summary) {
        const p = document.createElement('p');
        p.textContent = data.summary;
        p.style.marginBottom = '12px';
        panel.appendChild(p);
    }

    if (data.statistics && Object.keys(data.statistics).length > 0) {
        const h = document.createElement('h3');
        h.textContent = 'Key Metrics';
        panel.appendChild(h);
        const grid = document.createElement('div');
        grid.className = 'stats-grid';
        for (const [key, value] of Object.entries(data.statistics)) {
            const card = document.createElement('div');
            card.className = 'stat-card';
            const fmtVal = typeof value === 'number'
                ? value.toLocaleString(undefined, { maximumFractionDigits: 2 })
                : typeof value === 'object' ? JSON.stringify(value) : value;
            card.innerHTML = `<div class="label">${formatLabel(key)}</div>`
                + `<div class="value">${escapeHtml(String(fmtVal))}</div>`;
            grid.appendChild(card);
        }
        panel.appendChild(grid);
    }

    if (data.tables && data.tables.length > 0) {
        for (const table of data.tables) {
            const wrap = document.createElement('div');
            wrap.style.marginTop = '12px';
            if (table.title) {
                const t = document.createElement('h3');
                t.textContent = table.title;
                wrap.appendChild(t);
            }
            const tbl = document.createElement('table');
            tbl.className = 'stats-table';
            if (table.headers) {
                const thead = document.createElement('thead');
                const tr = document.createElement('tr');
                for (const h of table.headers) {
                    const th = document.createElement('th');
                    th.textContent = h;
                    tr.appendChild(th);
                }
                thead.appendChild(tr);
                tbl.appendChild(thead);
            }
            if (table.rows) {
                const tbody = document.createElement('tbody');
                for (const row of table.rows) {
                    const tr = document.createElement('tr');
                    const cells = Array.isArray(row) ? row : Object.values(row);
                    for (const cell of cells) {
                        const td = document.createElement('td');
                        td.textContent = cell;
                        tr.appendChild(td);
                    }
                    tbody.appendChild(tr);
                }
                tbl.appendChild(tbody);
            }
            wrap.appendChild(tbl);
            panel.appendChild(wrap);
        }
    }
    container.appendChild(panel);
}

let chartCounter = 0;

const CHART_PALETTE = [
    '#171717',
    '#0072f5',
    '#17b169',
    '#f5a623',
    '#8e4ec6',
    '#e5484d',
    '#4d4d4d',
    '#0068d6',
    '#30a46c',
    '#e54666',
];

function renderCharts(container, data) {
    if (!data.charts || data.charts.length === 0) return;
    const wrap = document.createElement('div');
    wrap.className = 'chart-container';

    const pendingCharts = [];

    for (const chart of data.charts) {
        const item = document.createElement('div');
        item.className = 'chart-item';

        if (chart.description) {
            const desc = document.createElement('p');
            desc.className = 'chart-desc';
            desc.textContent = chart.description;
            item.appendChild(desc);
        }

        if (chart.chart_data) {
            const canvasWrap = document.createElement('div');
            canvasWrap.className = 'chart-canvas-wrap';
            const canvas = document.createElement('canvas');
            canvas.id = `chart-${++chartCounter}`;
            canvasWrap.appendChild(canvas);
            item.appendChild(canvasWrap);
            pendingCharts.push({ canvas, chart });
        } else if (chart.image_base64) {
            if (chart.title) {
                const h4 = document.createElement('h4');
                h4.textContent = chart.title;
                item.appendChild(h4);
            }
            const img = document.createElement('img');
            img.src = `data:image/png;base64,${chart.image_base64}`;
            img.alt = chart.title || 'Chart';
            item.appendChild(img);
        }

        wrap.appendChild(item);
    }

    container.appendChild(wrap);

    if (pendingCharts.length > 0) {
        requestAnimationFrame(() => {
            requestAnimationFrame(() => {
                for (const { canvas, chart } of pendingCharts) {
                    try {
                        renderChartJS(canvas, chart);
                    } catch (e) {
                        console.error('Chart.js render error:', e);
                    }
                }
            });
        });
    }
}

function renderChartJS(canvas, chart) {
    if (typeof Chart === 'undefined') {
        console.error('Chart.js not loaded');
        return;
    }

    const parent = canvas.parentElement;
    if (!parent || parent.clientWidth === 0) {
        console.warn('Chart parent has 0 width, retrying in 200ms');
        setTimeout(() => renderChartJS(canvas, chart), 200);
        return;
    }

    canvas.style.width = '100%';
    canvas.style.height = '100%';

    const chartType = mapChartType(chart.chart_type || 'bar');
    const isHorizontal = chart.chart_type === 'horizontalBar';

    const chartData = chart.chart_data;
    if (!chartData || !chartData.labels || !chartData.datasets) {
        console.error('Invalid chart data:', chartData);
        return;
    }

    const isBoxType = chartType === 'boxplot' || chartType === 'violin';

    const styledDatasets = (chartData.datasets || []).map((ds, i) => {
        const color = CHART_PALETTE[i % CHART_PALETTE.length];
        const patched = { ...ds };
        if (isBoxType) {
            if (!patched.backgroundColor) patched.backgroundColor = color + '40';
            if (!patched.borderColor) patched.borderColor = color;
        } else if (!patched.backgroundColor) {
            patched.backgroundColor = chartType === 'doughnut'
                ? chartData.labels.map((_, j) => CHART_PALETTE[j % CHART_PALETTE.length])
                : chartType === 'line' ? color + '18' : color;
        }
        if (!isBoxType && !patched.borderColor) {
            patched.borderColor = chartType === 'doughnut'
                ? '#ffffff'
                : color;
        }
        if (chartType === 'line' && patched.borderWidth === undefined) {
            patched.borderWidth = 2;
        }
        if (chartType === 'doughnut' && patched.borderWidth === undefined) {
            patched.borderWidth = 2;
        }
        return patched;
    });

    new Chart(canvas.getContext('2d'), {
        type: chartType,
        data: { ...chartData, datasets: styledDatasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: isHorizontal ? 'y' : 'x',
            plugins: {
                title: {
                    display: true,
                    text: chart.title || '',
                    color: '#171717',
                    font: { size: 14, weight: '600', family: "'Geist', sans-serif" },
                    padding: { bottom: 16 },
                },
                legend: {
                    display: (chartData.datasets || []).length > 1,
                    labels: {
                        color: '#4d4d4d',
                        font: { size: 12, family: "'Geist', sans-serif" },
                        usePointStyle: true,
                        pointStyle: 'circle',
                        padding: 16,
                    },
                },
                tooltip: {
                    backgroundColor: '#171717',
                    titleColor: '#ffffff',
                    bodyColor: '#ffffff',
                    borderColor: 'rgba(255, 255, 255, 0.1)',
                    borderWidth: 1,
                    padding: 10,
                    cornerRadius: 6,
                    titleFont: { family: "'Geist', sans-serif", weight: '500' },
                    bodyFont: { family: "'Geist Mono', monospace" },
                    ...(isBoxType ? {} : {
                        callbacks: {
                            label: function(ctx) {
                                const val = ctx.parsed.y ?? ctx.parsed.x ?? ctx.raw;
                                return `${ctx.dataset.label || ''}: ${Number(val).toLocaleString(undefined, {maximumFractionDigits: 2})}`;
                            }
                        },
                    }),
                },
            },
            scales: chartType === 'doughnut' ? {} : {
                x: {
                    title: {
                        display: !!chart.x_label,
                        text: chart.x_label || '',
                        color: '#666666',
                        font: { size: 12, family: "'Geist', sans-serif", weight: '500' },
                    },
                    ticks: {
                        color: '#666666',
                        font: { size: 11, family: "'Geist', sans-serif" },
                        maxRotation: 45,
                    },
                    grid: { color: 'rgba(0, 0, 0, 0.06)', drawBorder: false },
                    border: { display: false },
                },
                y: {
                    title: {
                        display: !!chart.y_label,
                        text: chart.y_label || '',
                        color: '#666666',
                        font: { size: 12, family: "'Geist', sans-serif", weight: '500' },
                    },
                    ticks: {
                        color: '#666666',
                        font: { size: 11, family: "'Geist Mono', monospace" },
                    },
                    grid: { color: 'rgba(0, 0, 0, 0.06)', drawBorder: false },
                    border: { display: false },
                    beginAtZero: false,
                },
            },
            animation: { duration: 800, easing: 'easeOutQuart' },
        },
    });
}

function mapChartType(type) {
    const map = { bar: 'bar', line: 'line', doughnut: 'doughnut', horizontalBar: 'bar', grouped_bar: 'bar', stacked_bar: 'bar', boxplot: 'boxplot', violin: 'violin' };
    return map[type] || 'bar';
}

function addMessage(text, role) {
    const messages = document.getElementById('messages');
    const div = document.createElement('div');
    div.className = `message ${role}-message`;
    const content = document.createElement('div');
    content.className = 'message-content';
    if (text) content.textContent = text;
    div.appendChild(content);
    messages.appendChild(div);
    document.getElementById('chat-container').scrollTop =
        document.getElementById('chat-container').scrollHeight;
    return div;
}

function formatLabel(key) {
    return key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}
