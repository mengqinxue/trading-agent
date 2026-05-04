// Trading Agent 前端逻辑

const API_BASE = '/api/tasks';

// 股票列表数据
let stockList = [];

// DOM 元素
const btnMarketAnalysis = document.getElementById('btn-market-analysis');
const btnStockAnalysis = document.getElementById('btn-stock-analysis');
const btnChatQuery = document.getElementById('btn-chat-query');
const btnDataCatalog = document.getElementById('btn-data-catalog');
const btnViewTasks = document.getElementById('btn-view-tasks');
const btnWorkflowDoc = document.getElementById('btn-workflow-doc');
const panelMarketAnalysis = document.getElementById('panel-market-analysis');
const panelStockAnalysis = document.getElementById('panel-stock-analysis');
const panelTasks = document.getElementById('panel-tasks');
const panelTaskDetail = document.getElementById('panel-task-detail');
const panelWorkflowDoc = document.getElementById('panel-workflow-doc');
const tasksList = document.getElementById('tasks-list');
const stockListContainer = document.getElementById('stock-list-container');
const stockPreview = document.getElementById('stock-preview');
const stockPreviewBody = document.getElementById('stock-preview-body');
const stockCount = document.getElementById('stock-count');

// 股票名称缓存
const stockNameCache = {};

// 显示面板
function showPanel(panelId) {
    const panels = [panelMarketAnalysis, panelStockAnalysis, panelTasks, panelTaskDetail, panelWorkflowDoc];
    panels.forEach(p => p.classList.add('hidden'));
    document.getElementById(panelId).classList.remove('hidden');

    const buttons = [btnMarketAnalysis, btnStockAnalysis, btnChatQuery, btnDataCatalog, btnViewTasks, btnWorkflowDoc];
    buttons.forEach(b => b.classList.remove('active'));
}

// Tab 切换
function setupTabs() {
    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    tabButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const tabId = btn.getAttribute('data-tab');

            tabButtons.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));

            btn.classList.add('active');
            document.getElementById(tabId + '-tab').classList.add('active');
        });
    });
}

// 导航按钮事件
btnMarketAnalysis.addEventListener('click', () => {
    showPanel('panel-market-analysis');
    btnMarketAnalysis.classList.add('active');
});

btnStockAnalysis.addEventListener('click', () => {
    showPanel('panel-stock-analysis');
    btnStockAnalysis.classList.add('active');
});

btnViewTasks.addEventListener('click', () => {
    showPanel('panel-tasks');
    btnViewTasks.classList.add('active');
    loadTasks();
});

btnWorkflowDoc.addEventListener('click', () => {
    showPanel('panel-workflow-doc');
    btnWorkflowDoc.classList.add('active');
});

// 智能查询跳转
btnChatQuery.addEventListener('click', () => {
    window.location.href = '/static/chat.html';
});

// 数据词典跳转
btnDataCatalog.addEventListener('click', () => {
    window.location.href = '/static/catalog.html';
});

// 添加股票行
function addStockRow(code = '', position = 0) {
    const defaultPosition = parseFloat(document.getElementById('default-position').value) || 0;
    const rowId = `stock-row-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

    const rowHtml = `
        <div class="stock-row" id="${rowId}">
            <input type="text" class="stock-code-input" placeholder="股票代码（如 600036）"
                   value="${code}" onchange="updateStockRow('${rowId}')">
            <span class="stock-name-display" id="${rowId}-name"></span>
            <input type="number" class="stock-position-input" placeholder="持仓金额"
                   value="${position || defaultPosition}">
            <button class="remove-stock-btn" onclick="removeStockRow('${rowId}')">×</button>
        </div>
    `;

    stockListContainer.insertAdjacentHTML('beforeend', rowHtml);

    if (code) {
        fetchStockName(code, rowId);
    }

    return rowId;
}

// 获取股票名称
async function fetchStockName(code, rowId) {
    if (stockNameCache[code]) {
        document.getElementById(`${rowId}-name`).textContent = stockNameCache[code];
        return;
    }

    try {
        const response = await fetch(`/api/stocks/${code}/name`);
        if (response.ok) {
            const data = await response.json();
            if (data.name) {
                stockNameCache[code] = data.name;
                document.getElementById(`${rowId}-name`).textContent = data.name;
            }
        }
    } catch (error) {
        // 静默失败
    }
}

// 更新股票行
function updateStockRow(rowId) {
    const row = document.getElementById(rowId);
    const codeInput = row.querySelector('.stock-code-input');
    const code = codeInput.value.trim();

    if (code && code.match(/^\d{6}$/)) {
        fetchStockName(code, rowId);
    } else {
        document.getElementById(`${rowId}-name`).textContent = '';
    }

    updateStockPreview();
}

// 删除股票行
function removeStockRow(rowId) {
    document.getElementById(rowId).remove();
    updateStockPreview();
}

// 更新股票预览
function updateStockPreview() {
    const rows = stockListContainer.querySelectorAll('.stock-row');
    const stocks = [];

    rows.forEach(row => {
        const code = row.querySelector('.stock-code-input').value.trim();
        const position = parseFloat(row.querySelector('.stock-position-input').value) || 0;
        const nameDisplay = row.querySelector('.stock-name-display') || {textContent: ''};

        if (code) {
            stocks.push({
                code,
                name: nameDisplay.textContent || stockNameCache[code] || '未知',
                position
            });
        }
    });

    if (stocks.length > 0) {
        stockPreview.classList.remove('hidden');
        stockPreviewBody.innerHTML = stocks.map((s, i) => `
            <tr>
                <td>${s.code}</td>
                <td>${s.name}</td>
                <td>${s.position.toLocaleString()} 元</td>
                <td><button onclick="removePreviewRow(${i})">删除</button></td>
            </tr>
        `).join('');
        stockCount.textContent = `共 ${stocks.length} 只股票待分析`;
    } else {
        stockPreview.classList.add('hidden');
    }

    stockList = stocks;
}

// 删除预览行
function removePreviewRow(index) {
    const rows = stockListContainer.querySelectorAll('.stock-row');
    const validRows = [];

    rows.forEach(row => {
        if (row.querySelector('.stock-code-input').value.trim()) {
            validRows.push(row);
        }
    });

    if (validRows[index]) {
        validRows[index].remove();
        updateStockPreview();
    }
}

// 添加股票按钮
document.getElementById('btn-add-stock').addEventListener('click', () => {
    addStockRow();
});

// 批量添加按钮
document.getElementById('btn-batch-add').addEventListener('click', () => {
    const batchCodes = document.getElementById('batch-stock-codes').value;
    const defaultPosition = parseFloat(document.getElementById('default-position').value) || 0;

    if (!batchCodes) {
        alert('请输入股票代码');
        return;
    }

    const codes = batchCodes.split(',').map(c => c.trim()).filter(c => c.match(/^\d{6}$/));

    codes.forEach(code => {
        addStockRow(code, defaultPosition);
    });

    document.getElementById('batch-stock-codes').value = '';
    updateStockPreview();
});

// 创建市场分析任务
document.getElementById('btn-create-market-task').addEventListener('click', async () => {
    try {
        const response = await fetch(API_BASE, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ task_type: 'market_analysis' })
        });
        const task = await response.json();
        alert(`任务创建成功！ID: ${task.task_id}`);
        btnViewTasks.click();
    } catch (error) {
        alert('创建任务失败: ' + error.message);
    }
});

// 创建股票分析任务
document.getElementById('btn-create-stock-task').addEventListener('click', async () => {
    updateStockPreview();

    if (stockList.length === 0) {
        alert('请添加至少一只股票');
        return;
    }

    const requestData = {
        task_type: 'stock_analysis',
        stocks: stockList.map(s => ({
            code: s.code,
            position: s.position
        }))
    };

    try {
        const response = await fetch(API_BASE, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestData)
        });
        const task = await response.json();
        alert(`任务创建成功！ID: ${task.task_id}\n将分析 ${stockList.length} 只股票`);
        btnViewTasks.click();

        stockListContainer.innerHTML = '';
        stockList = [];
        stockPreview.classList.add('hidden');
    } catch (error) {
        alert('创建任务失败: ' + error.message);
    }
});

// 加载任务列表
async function loadTasks() {
    try {
        const response = await fetch(API_BASE);
        const tasks = await response.json();
        renderTasks(tasks);
    } catch (error) {
        tasksList.innerHTML = '<p>加载任务列表失败</p>';
    }
}

// 渲染任务列表
function renderTasks(tasks) {
    if (tasks.length === 0) {
        tasksList.innerHTML = '<p>暂无任务</p>';
        return;
    }

    tasksList.innerHTML = tasks.map(task => `
        <div class="task-card" onclick="viewTask('${task.task_id}')">
            <h3>${task.folder_name || task.task_id.slice(0, 8)}</h3>
            <p class="task-type">${task.task_type === 'market_analysis' ? '市场分析' : '股票分析'}</p>
            <p class="task-time">${task.created_at ? new Date(task.created_at).toLocaleString() : '未知时间'}</p>
            <span class="status ${task.status}">${getStatusText(task.status)}</span>
        </div>
    `).join('');
}

// 状态文本
function getStatusText(status) {
    const statusMap = {
        'pending': '待执行',
        'running': '执行中',
        'completed': '已完成',
        'failed': '失败'
    };
    return statusMap[status] || status;
}

// 查看任务详情
async function viewTask(taskId) {
    try {
        const response = await fetch(`${API_BASE}/${taskId}`);
        const task = await response.json();
        showTaskDetail(task);
    } catch (error) {
        alert('加载任务详情失败');
    }
}

// 显示任务详情
function showTaskDetail(task) {
    showPanel('panel-task-detail');

    // 基本信息
    const basicInfo = document.getElementById('task-basic-info');
    let stockInfo = '';
    if (task.task_type === 'stock_analysis' && task.stocks) {
        stockInfo = `<div class="info-row"><span class="label">分析股票:</span><span class="value">${task.stocks.map(s => `${s.code} (${s.position.toLocaleString()}元)`).join(', ')}</span></div>`;
    }

    basicInfo.innerHTML = `
        <div class="info-row"><span class="label">任务类型:</span><span class="value">${task.task_type === 'market_analysis' ? '市场分析' : '股票分析'}</span></div>
        <div class="info-row"><span class="label">任务 ID:</span><span class="value">${task.task_id}</span></div>
        <div class="info-row"><span class="label">状态:</span><span class="value status-badge ${task.status}">${getStatusText(task.status)}</span></div>
        <div class="info-row"><span class="label">创建时间:</span><span class="value">${task.created_at ? new Date(task.created_at).toLocaleString() : '未知'}</span></div>
        <div class="info-row"><span class="label">开始时间:</span><span class="value">${task.started_at ? new Date(task.started_at).toLocaleString() : '未开始'}</span></div>
        <div class="info-row"><span class="label">完成时间:</span><span class="value">${task.completed_at ? new Date(task.completed_at).toLocaleString() : '未完成'}</span></div>
        ${stockInfo}
    `;

    // Workflow 流程图
    renderWorkflowFlowchart(task);

    // Summary
    renderSummary(task);

    // 日志
    const logsContent = document.getElementById('task-logs');
    if (task.logs && task.logs.length > 0) {
        logsContent.innerHTML = task.logs.map(log => `<div class="log-line">${log}</div>`).join('');
    } else {
        logsContent.innerHTML = '<p class="no-logs">暂无日志</p>';
    }
}

// 渲染 Workflow 流程图
function renderWorkflowFlowchart(task) {
    const flowchart = document.getElementById('workflow-flowchart');
    const steps = task.workflow_steps || [];

    // 定义 workflow 结构
    const workflowNodes = getWorkflowNodes(task.task_type);

    // 为每个节点添加状态
    const nodesWithStatus = workflowNodes.map(node => {
        const step = steps.find(s => s.name.includes(node.id) || s.name === node.id);
        return {
            ...node,
            stepData: step,
            status: getStepStatus(step, task.status)
        };
    });

    flowchart.innerHTML = `
        <h3>Workflow 执行流程</h3>
        <div class="flowchart-container">
            ${nodesWithStatus.map((node, i) => `
                <div class="flowchart-node ${node.status}" data-step="${node.id}">
                    <div class="node-icon">${getNodeIcon(node.status)}</div>
                    <div class="node-name">${node.name}</div>
                    <div class="node-time">${node.stepData?.completed_at ? formatDuration(node.stepData) : ''}</div>
                </div>
                ${i < nodesWithStatus.length - 1 ? '<div class="flowchart-arrow">→</div>' : ''}
            `).join('')}
        </div>
    `;
}

// 获取 Workflow 节点
function getWorkflowNodes(taskType) {
    if (taskType === 'market_analysis') {
        return [
            { id: 'macro', name: '宏观分析' },
            { id: 'sector', name: '板块分析' },
            { id: 'industry', name: '行业分析' },
            { id: 'screener', name: '个股筛选' }
        ];
    } else {
        return [
            { id: 'init', name: '初始化' },
            { id: 'fundamentals', name: '基本面' },
            { id: 'technical', name: '技术面' },
            { id: 'aggregator', name: '汇总' },
            { id: 'debate', name: '辩论' },
            { id: 'judge', name: '决策' },
            { id: 'position', name: '持仓建议' }
        ];
    }
}

// 获取步骤状态
function getStepStatus(step, taskStatus) {
    if (!step) {
        return taskStatus === 'running' ? 'pending' : 'skipped';
    }
    if (step.completed_at) {
        return 'completed';
    }
    if (step.started_at) {
        return 'running';
    }
    return 'pending';
}

// 获取节点图标
function getNodeIcon(status) {
    const icons = {
        'completed': '✓',
        'running': '◐',
        'pending': '○',
        'skipped': '-',
        'failed': '✗'
    };
    return icons[status] || '○';
}

// 格式化持续时间
function formatDuration(step) {
    if (!step.started_at || !step.completed_at) return '';
    const start = new Date(step.started_at);
    const end = new Date(step.completed_at);
    const seconds = Math.round((end - start) / 1000);
    if (seconds < 60) return `${seconds}秒`;
    const minutes = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${minutes}分${secs}秒`;
}

// 渲染 Summary
function renderSummary(task) {
    const summarySection = document.getElementById('task-summary');
    const summary = task.summary || task.result;

    if (!summary) {
        summarySection.innerHTML = '';
        return;
    }

    let summaryHtml = '<h3>分析摘要</h3>';

    if (Array.isArray(summary)) {
        // 批量分析摘要
        summaryHtml += '<div class="summary-grid">';
        summary.forEach(item => {
            const decisionClass = item.decision || item.error ? '' : 'neutral';
            summaryHtml += `
                <div class="summary-item ${item.error ? 'error' : decisionClass}">
                    <div class="summary-code">${item.code}</div>
                    <div class="summary-decision">${item.decision || item.error || 'N/A'}</div>
                    ${item.action ? `<div class="summary-action">${item.action}</div>` : ''}
                </div>
            `;
        });
        summaryHtml += '</div>';
    } else if (typeof summary === 'object') {
        // 单股分析摘要
        summaryHtml += '<div class="summary-box">';
        if (summary.decision) {
            summaryHtml += `<div class="summary-row"><span class="label">决策:</span><span class="value decision-${summary.decision}">${summary.decision}</span></div>`;
        }
        if (summary.confidence) {
            summaryHtml += `<div class="summary-row"><span class="label">置信度:</span><span class="value">${summary.confidence}</span></div>`;
        }
        Object.entries(summary).forEach(([key, value]) => {
            if (key !== 'decision' && key !== 'confidence' && value) {
                summaryHtml += `<div class="summary-row"><span class="label">${key}:</span><span class="value">${value}</span></div>`;
            }
        });
        summaryHtml += '</div>';
    }

    summarySection.innerHTML = summaryHtml;
}

// 日志折叠切换
document.getElementById('logs-toggle').addEventListener('click', () => {
    const logsContent = document.getElementById('task-logs');
    const toggleIcon = document.querySelector('.toggle-icon');

    if (logsContent.classList.contains('collapsed')) {
        logsContent.classList.remove('collapsed');
        toggleIcon.textContent = '▲';
    } else {
        logsContent.classList.add('collapsed');
        toggleIcon.textContent = '▼';
    }
});

// 返回任务列表
document.getElementById('btn-back-tasks').addEventListener('click', () => {
    btnViewTasks.click();
});

// 初始化
setupTabs();
addStockRow();
btnViewTasks.click();