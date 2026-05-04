// 智能查询页面逻辑 - AI 自然语言查询

const API_BASE = '/api/chat';

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    // 绑定提交按钮
    const submitBtn = document.getElementById('submit-btn');
    const input = document.getElementById('query-input');

    submitBtn.addEventListener('click', submitQuery);

    input.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            submitQuery();
        }
    });

    // 绑定示例查询点击
    document.querySelectorAll('.example-query').forEach(el => {
        el.addEventListener('click', () => {
            input.value = el.textContent;
            submitQuery();
        });
    });
});

// 提交查询
async function submitQuery() {
    const input = document.getElementById('query-input');
    const query = input.value.trim();

    if (!query) {
        showError('请输入查询问题');
        return;
    }

    const resultArea = document.getElementById('result-area');
    const submitBtn = document.getElementById('submit-btn');

    // 显示加载状态
    resultArea.innerHTML = `
        <div class="ai-thinking">
            <svg class="ai-thinking-icon" viewBox="0 0 24 24" fill="currentColor">
                <circle cx="12" cy="12" r="3"/>
            </svg>
            <span>AI 正在理解您的问题...</span>
        </div>
    `;
    submitBtn.disabled = true;

    try {
        const resp = await fetch(`${API_BASE}/ai-query`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query }),
        });

        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || '查询失败');
        }

        const data = await resp.json();
        renderResult(data);
    } catch (e) {
        showError(e.message);
    } finally {
        submitBtn.disabled = false;
    }
}

// 渲染结果
function renderResult(data) {
    const resultArea = document.getElementById('result-area');

    if (!data.success) {
        showError(data.error || '查询失败');
        return;
    }

    const intent = data.intent || {};
    const stocks = data.data?.stocks || [];
    const count = data.data?.count || 0;
    const response = data.response || '';

    // AI 解释
    const explanation = intent.explanation || '';
    const conditions = intent.conditions || [];

    // 构建条件描述
    const condDesc = conditions.map(c => {
        const field = fieldNames[c.field] || c.field;
        const op = opNames[c.op] || c.op;
        const time = c.time_range ? `（${c.time_range}）` : '';
        return `${field} ${op} ${c.value}${time}`;
    }).join('、');

    resultArea.innerHTML = `
        <div class="result-card">
            <div class="ai-explanation">
                <strong>AI 理解：</strong> ${explanation}
                ${condDesc ? `<br><strong>筛选条件：</strong> ${condDesc}` : ''}
            </div>
            <div style="padding: 10px 0; color: #333;">
                ${response}
            </div>
        </div>

        <div class="result-card">
            <div class="result-header">
                <span class="result-title">查询结果</span>
                <span class="result-count">共 ${count} 只</span>
            </div>
            ${renderStockTable(stocks)}
        </div>
    `;
}

// 渲染股票表格
function renderStockTable(stocks) {
    if (!stocks.length) {
        return '<div style="text-align: center; color: #999; padding: 20px;">没有找到符合条件的股票</div>';
    }

    return `
        <table class="stock-table">
            <thead>
                <tr>
                    <th>代码</th>
                    <th>名称</th>
                    <th>行业</th>
                    <th>涨幅</th>
                    <th>5日涨幅</th>
                    <th>20日涨幅</th>
                    <th>换手率</th>
                </tr>
            </thead>
            <tbody>
                ${stocks.map(s => `
                    <tr>
                        <td>${s.code || ''}</td>
                        <td>${s.name || ''}</td>
                        <td>${s.industry || '未知'}</td>
                        <td class="${(s.change_pct || 0) >= 0 ? 'change-positive' : 'change-negative'}">
                            ${(s.change_pct || 0).toFixed(2)}%
                        </td>
                        <td class="${(s.change_5d || 0) >= 0 ? 'change-positive' : 'change-negative'}">
                            ${(s.change_5d || 0).toFixed(2)}%
                        </td>
                        <td class="${(s.change_20d || 0) >= 0 ? 'change-positive' : 'change-negative'}">
                            ${(s.change_20d || 0).toFixed(2)}%
                        </td>
                        <td>${(s.turnover || 0).toFixed(2)}%</td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
}

// 显示错误
function showError(msg) {
    const resultArea = document.getElementById('result-area');
    resultArea.innerHTML = `<div class="error-msg">${msg}</div>`;
}

// 字段名映射
const fieldNames = {
    'change_pct': '涨跌幅',
    'turnover': '换手率',
    'industry': '行业',
    'close': '收盘价',
};

// 操作符映射
const opNames = {
    '>=': '大于等于',
    '<=': '小于等于',
    '>': '大于',
    '<': '小于',
    '==': '等于',
    'contains': '包含',
};