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
            if (config.grafana_url) {
                link.href = config.grafana_url;
            }
        }
    } catch (e) {
        // Grafana link will stay as '#'
    }
});

function askExample(btn) {
    const input = document.getElementById('question-input');
    input.value = btn.textContent.trim();
    handleSubmit(new Event('submit'));
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
    const statusEl = addStatus(responseDiv);

    try {
        const resp = await fetch(`${API_BASE}/api/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question }),
        });

        if (!resp.ok) {
            throw new Error(`Server error: ${resp.status}`);
        }

        const reader = resp.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop();

            let eventType = null;
            for (const line of lines) {
                if (line.startsWith('event: ')) {
                    eventType = line.slice(7).trim();
                } else if (line.startsWith('data: ') && eventType) {
                    try {
                        const data = JSON.parse(line.slice(6));
                        handleEvent(eventType, data, responseDiv, statusEl);
                    } catch (e) {
                        // Skip unparseable events
                    }
                    eventType = null;
                }
            }
        }
    } catch (err) {
        const content = responseDiv.querySelector('.message-content');
        content.innerHTML = `<div class="error-message">Failed to get a response: ${err.message}</div>`;
    } finally {
        statusEl.remove();
        isProcessing = false;
        document.getElementById('send-btn').disabled = false;
    }
}

function handleEvent(type, data, container, statusEl) {
    const content = container.querySelector('.message-content');

    switch (type) {
        case 'status':
            statusEl.querySelector('.status-text').textContent = data.message || '';
            break;

        case 'statistics':
            renderStatistics(content, data);
            break;

        case 'charts':
            renderCharts(content, data);
            break;

        case 'report':
            const reportDiv = document.createElement('div');
            reportDiv.className = 'report-text';
            reportDiv.textContent = data.text || '';
            content.prepend(reportDiv);
            break;

        case 'error':
            const errDiv = document.createElement('div');
            errDiv.className = 'error-message';
            errDiv.textContent = data.message || 'An error occurred';
            content.appendChild(errDiv);
            break;

        case 'done':
            break;
    }

    const main = document.getElementById('chat-container');
    main.scrollTop = main.scrollHeight;
}

function renderStatistics(container, data) {
    const panel = document.createElement('div');
    panel.className = 'stats-panel';

    if (data.summary) {
        const summaryP = document.createElement('p');
        summaryP.textContent = data.summary;
        summaryP.style.marginBottom = '12px';
        panel.appendChild(summaryP);
    }

    if (data.statistics && Object.keys(data.statistics).length > 0) {
        const heading = document.createElement('h3');
        heading.textContent = 'Key Metrics';
        panel.appendChild(heading);

        const grid = document.createElement('div');
        grid.className = 'stats-grid';
        for (const [key, value] of Object.entries(data.statistics)) {
            const card = document.createElement('div');
            card.className = 'stat-card';
            card.innerHTML = `
                <div class="label">${formatLabel(key)}</div>
                <div class="value">${typeof value === 'object' ? JSON.stringify(value) : value}</div>
            `;
            grid.appendChild(card);
        }
        panel.appendChild(grid);
    }

    if (data.tables && data.tables.length > 0) {
        for (const table of data.tables) {
            const tableEl = document.createElement('div');
            tableEl.style.marginTop = '12px';
            if (table.title) {
                const title = document.createElement('h3');
                title.textContent = table.title;
                tableEl.appendChild(title);
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
                    for (const cell of row) {
                        const td = document.createElement('td');
                        td.textContent = cell;
                        tr.appendChild(td);
                    }
                    tbody.appendChild(tr);
                }
                tbl.appendChild(tbody);
            }
            tableEl.appendChild(tbl);
            panel.appendChild(tableEl);
        }
    }

    container.appendChild(panel);
}

function renderCharts(container, data) {
    if (!data.charts || data.charts.length === 0) return;

    const chartContainer = document.createElement('div');
    chartContainer.className = 'chart-container';

    for (const chart of data.charts) {
        const item = document.createElement('div');
        item.className = 'chart-item';

        if (chart.title) {
            const h4 = document.createElement('h4');
            h4.textContent = chart.title;
            item.appendChild(h4);
        }

        if (chart.image_base64) {
            const img = document.createElement('img');
            img.src = `data:image/png;base64,${chart.image_base64}`;
            img.alt = chart.title || 'Chart';
            item.appendChild(img);
        }

        if (chart.description) {
            const desc = document.createElement('p');
            desc.className = 'chart-desc';
            desc.textContent = chart.description;
            item.appendChild(desc);
        }

        chartContainer.appendChild(item);
    }

    container.appendChild(chartContainer);
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
    document.getElementById('chat-container').scrollTop = document.getElementById('chat-container').scrollHeight;
    return div;
}

function addStatus(container) {
    const status = document.createElement('div');
    status.className = 'status-indicator';
    status.innerHTML = '<span class="dot"></span><span class="status-text">Thinking...</span>';
    container.appendChild(status);
    return status;
}

function formatLabel(key) {
    return key
        .replace(/_/g, ' ')
        .replace(/\b\w/g, c => c.toUpperCase());
}
