// 数据词典页面逻辑

const CATALOG_API = '/api/catalog';

// 初始化
document.addEventListener('DOMContentLoaded', async () => {
    await loadSources();
    await loadTypes();
});

// 加载数据源
async function loadSources() {
    const grid = document.getElementById('sources-grid');
    try {
        const resp = await fetch(`${CATALOG_API}/data-sources`);
        const data = await resp.json();

        grid.innerHTML = data.sources.map(s => `
            <div class="source-item">
                <div class="source-name">
                    ${s.name}
                    <span class="source-status status-${s.status}">${formatStatus(s.status)}</span>
                </div>
                <div class="source-desc">${s.description}</div>
                <div class="source-config">配置：${s.config}</div>
            </div>
        `).join('');
    } catch (e) {
        grid.innerHTML = `<div class="error-msg">加载失败: ${e.message}</div>`;
    }
}

// 加载数据类型
async function loadTypes() {
    const grid = document.getElementById('types-grid');
    try {
        const resp = await fetch(`${CATALOG_API}/data-types`);
        const data = await resp.json();

        grid.innerHTML = data.types.map(t => `
            <div class="type-item" onclick="showFields('${t.name}')">
                <div class="type-name">
                    ${t.name}
                    <span class="category-tag category-${t.category}">${formatCategory(t.category)}</span>
                    <span class="type-status status-${t.status}">${formatStatus(t.status)}</span>
                </div>
                <div class="type-desc">${t.description}</div>
                <div class="type-update">更新频率：${t.update_freq}</div>
            </div>
        `).join('');
    } catch (e) {
        grid.innerHTML = `<div class="error-msg">加载失败: ${e.message}</div>`;
    }
}

// 显示字段说明
async function showFields(dataType) {
    const section = document.getElementById('fields-section');
    const title = document.getElementById('fields-title');
    const body = document.getElementById('fields-body');
    const sampleSection = document.getElementById('sample-section');

    section.style.display = 'block';
    title.textContent = `${dataType} - 字段说明`;

    try {
        const resp = await fetch(`${CATALOG_API}/fields/${encodeURIComponent(dataType)}`);
        const data = await resp.json();

        if (data.error) {
            body.innerHTML = `<tr><td colspan="3">${data.error}</td></tr>`;
            return;
        }

        body.innerHTML = data.fields.map(f => `
            <tr>
                <td><code>${f.name}</code></td>
                <td>${f.type}</td>
                <td>${f.desc}</td>
            </tr>
        `).join('');

        // 同时加载样例
        await showSample(dataType);
    } catch (e) {
        body.innerHTML = `<tr><td colspan="3">加载失败: ${e.message}</td></tr>`;
    }
}

// 显示数据样例
async function showSample(dataType) {
    const section = document.getElementById('sample-section');
    const title = document.getElementById('sample-title');
    const jsonEl = document.getElementById('sample-json');

    section.style.display = 'block';
    title.textContent = `${dataType} - 数据样例`;

    try {
        const resp = await fetch(`${CATALOG_API}/sample/${encodeURIComponent(dataType)}`);
        const data = await resp.json();

        if (data.error) {
            jsonEl.textContent = data.error;
        } else {
            jsonEl.textContent = JSON.stringify(data.sample, null, 2);
        }
    } catch (e) {
        jsonEl.textContent = `加载失败: ${e.message}`;
    }
}

// 格式化状态
function formatStatus(status) {
    const map = {
        'active': '已启用',
        'available': '可用',
        'config_required': '需配置',
        'implemented': '已实现',
        'partial': '部分实现',
    };
    return map[status] || status;
}

// 格式化分类
function formatCategory(category) {
    const map = {
        'trade': '交易',
        'fundamental': '基本面',
        'market': '市场',
    };
    return map[category] || category;
}