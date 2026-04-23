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

    addMessage(question, 'user');
    const responseDiv = addMessage('', 'assistant');
    const logContainer = addLogPanel(responseDiv);

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
    orchestrator: '#5b8def',
    statistics: '#4CAF50',
    visualization: '#FF9800',
    query: '#9C27B0',
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

        case 'done':
            break;
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
    const color = AGENT_COLORS[agent] || '#8b8fa3';
    const time = new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });

    entry.innerHTML = `<span class="log-time">${time}</span>`
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
        setTimeout(() => {
            for (const { canvas, chart } of pendingCharts) {
                try {
                    renderChartJS(canvas, chart);
                } catch (e) {
                    console.error('Chart.js render error:', e);
                }
            }
        }, 50);
    }
}

function renderChartJS(canvas, chart) {
    const chartType = mapChartType(chart.chart_type || 'bar');
    const isHorizontal = chart.chart_type === 'horizontalBar';

    const config = {
        type: chartType,
        data: chart.chart_data,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: isHorizontal ? 'y' : 'x',
            plugins: {
                title: {
                    display: true,
                    text: chart.title || '',
                    color: '#e1e4ed',
                    font: { size: 14, weight: 'bold' },
                    padding: { bottom: 16 },
                },
                legend: {
                    display: (chart.chart_data.datasets || []).length > 1,
                    labels: { color: '#8b8fa3', font: { size: 11 } },
                },
                tooltip: {
                    backgroundColor: '#1a1b26',
                    titleColor: '#e1e4ed',
                    bodyColor: '#e1e4ed',
                    borderColor: '#2d2f42',
                    borderWidth: 1,
                    padding: 10,
                    cornerRadius: 6,
                },
            },
            scales: chartType === 'doughnut' ? {} : {
                x: {
                    title: {
                        display: !!chart.x_label,
                        text: chart.x_label || '',
                        color: '#8b8fa3',
                    },
                    ticks: { color: '#8b8fa3', maxRotation: 45 },
                    grid: { color: 'rgba(45,47,66,0.5)' },
                },
                y: {
                    title: {
                        display: !!chart.y_label,
                        text: chart.y_label || '',
                        color: '#8b8fa3',
                    },
                    ticks: { color: '#8b8fa3' },
                    grid: { color: 'rgba(45,47,66,0.5)' },
                },
            },
            animation: {
                duration: 800,
                easing: 'easeOutQuart',
            },
        },
    };

    new Chart(canvas, config);
}

function mapChartType(type) {
    const map = { bar: 'bar', line: 'line', doughnut: 'doughnut', horizontalBar: 'bar', grouped_bar: 'bar', stacked_bar: 'bar' };
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
