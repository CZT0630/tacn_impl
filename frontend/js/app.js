/**
 * TACN 主应用逻辑
 */

document.addEventListener('DOMContentLoaded', function () {
    let currentTaskId = null;
    let currentPlan = null;

    // ========================================================================
    // 导航切换
    // ========================================================================

    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', function (e) {
            e.preventDefault();
            const section = this.dataset.section;

            document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
            this.classList.add('active');

            document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
            document.getElementById(`${section}-section`).classList.add('active');

            if (section === 'agents') loadAgents();
        });
    });

    // ========================================================================
    // 任务处理
    // ========================================================================

    const processBtn = document.getElementById('process-btn');
    const executeBtn = document.getElementById('execute-btn');
    const taskInput = document.getElementById('task-input');

    // 快捷场景按钮
    document.querySelectorAll('.scenario-btn').forEach(btn => {
        btn.addEventListener('click', function () {
            taskInput.value = this.dataset.text;
        });
    });

    processBtn.addEventListener('click', async function () {
        const input = taskInput.value.trim();
        if (!input) { alert('请输入任务请求'); return; }

        setButtonLoading(processBtn, '解析中...');
        hideElement('task-result');
        hideElement('execution-result');
        executeBtn.disabled = true;

        try {
            const plan = await api.processRequest(input);
            currentTaskId = plan.task_id;
            currentPlan = plan;
            displayPlan(plan);
            showElement('task-result');
            executeBtn.disabled = false;
        } catch (error) {
            showError('处理失败: ' + error.message);
        } finally {
            resetButton(processBtn, '处理请求');
        }
    });

    executeBtn.addEventListener('click', async function () {
        if (!currentTaskId) { alert('请先处理请求'); return; }

        setButtonLoading(executeBtn, '执行中...');
        hideElement('execution-result');

        try {
            const result = await api.executeTask(currentTaskId);
            displayResult(result);
            showElement('execution-result');
        } catch (error) {
            showError('执行失败: ' + error.message);
        } finally {
            resetButton(executeBtn, '执行任务');
        }
    });

    // ========================================================================
    // 显示执行计划
    // ========================================================================

    function displayPlan(plan) {
        // 统计卡片
        document.getElementById('plan-info').innerHTML = `
            <div class="stats-row">
                <div class="stat-card">
                    <div class="stat-value">${plan.intent.type}</div>
                    <div class="stat-label">意图类型</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${plan.subtask_graph.subtasks.length}</div>
                    <div class="stat-label">子任务数</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${plan.assignments.length}</div>
                    <div class="stat-label">Agent 分配</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${plan.parallel_groups.length}</div>
                    <div class="stat-label">并行组</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${plan.estimated_total_latency_ms.toFixed(0)}ms</div>
                    <div class="stat-label">预估延迟</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">$${plan.estimated_total_cost.toFixed(4)}</div>
                    <div class="stat-label">预估成本</div>
                </div>
            </div>
            <div class="plan-meta">
                <span class="meta-tag">隐私: ${plan.intent.privacy_level}</span>
                <span class="meta-tag">协作: ${plan.intent.requires_collaboration ? '是' : '否'}</span>
                <span class="meta-tag">截止: ${plan.intent.deadline_ms}ms</span>
                <span class="meta-tag">模式: ${plan.metadata.routing_mode || 'unknown'}</span>
            </div>
            <p class="request-text"><strong>用户请求:</strong> ${plan.intent.text}</p>
        `;

        // DAG 可视化
        renderDAG(plan);

        // 分配表
        const assignmentMap = {};
        plan.assignments.forEach(a => assignmentMap[a.subtask_id] = a);

        document.getElementById('assignments-list').innerHTML = plan.subtask_graph.subtasks.map((st, i) => {
            const a = assignmentMap[st.id];
            const loc = a ? a.location : '?';
            const agentShort = a ? a.agent_id.substring(0, 8) : '?';
            return `
                <div class="assignment-row">
                    <span class="asgn-index">${i + 1}</span>
                    <span class="asgn-name">${st.name}</span>
                    <span class="asgn-arrow">→</span>
                    <span class="asgn-agent">${agentShort}...</span>
                    <span class="location-badge ${loc}">${loc}</span>
                </div>
            `;
        }).join('');
    }

    // ========================================================================
    // DAG 渲染
    // ========================================================================

    function renderDAG(plan) {
        const container = document.getElementById('dag-container');
        const subtasks = plan.subtask_graph.subtasks;
        const edges = plan.subtask_graph.edges;
        const groups = plan.parallel_groups;
        const assignmentMap = {};
        plan.assignments.forEach(a => assignmentMap[a.subtask_id] = a);

        if (!groups || groups.length === 0) {
            container.innerHTML = '<p class="text-muted">无并行组信息</p>';
            return;
        }

        // 构建 stage 列
        let html = '<div class="dag-stages">';
        groups.forEach((group, stageIdx) => {
            html += `<div class="dag-stage">
                <div class="stage-label">Stage ${stageIdx + 1}</div>
                <div class="stage-nodes">`;

            group.forEach(stId => {
                const st = subtasks.find(s => s.id === stId);
                if (!st) return;
                const a = assignmentMap[stId];
                const loc = a ? a.location : '?';
                html += `<div class="dag-node ${loc}">
                    <div class="node-name">${st.name}</div>
                    <div class="node-loc">${loc}</div>
                </div>`;
            });

            html += '</div></div>';

            // 箭头
            if (stageIdx < groups.length - 1) {
                html += '<div class="dag-arrow">→</div>';
            }
        });
        html += '</div>';

        container.innerHTML = html;
    }

    // ========================================================================
    // 显示执行结果
    // ========================================================================

    function displayResult(result) {
        const statusClass = result.success ? 'status-success' : 'status-fail';
        const statusText = result.success ? '成功' : '失败';

        let html = `
            <div class="stats-row">
                <div class="stat-card">
                    <div class="stat-value ${statusClass}">${statusText}</div>
                    <div class="stat-label">执行状态</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${result.actual_latency_ms.toFixed(0)}ms</div>
                    <div class="stat-label">实际延迟</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">$${result.actual_cost.toFixed(4)}</div>
                    <div class="stat-label">实际成本</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${Object.keys(result.subtask_results).length}</div>
                    <div class="stat-label">完成子任务</div>
                </div>
            </div>
        `;

        // 子任务结果详情
        const results = result.subtask_results;
        if (results && Object.keys(results).length > 0) {
            html += '<h4>子任务执行详情</h4>';
            html += '<div class="subtask-results">';
            for (const [stId, sr] of Object.entries(results)) {
                if (!sr || typeof sr !== 'object') continue;
                const icon = sr.success ? '✅' : '❌';
                const output = sr.output || '';
                const shortOutput = output.length > 500 ? output.substring(0, 500) + '...' : output;
                // 将 markdown 标题转为 HTML
                const formattedOutput = shortOutput
                    .replace(/### (.*)/g, '<strong>$1</strong>')
                    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                    .replace(/\n/g, '<br>');

                html += `
                    <div class="result-card ${sr.success ? 'success' : 'fail'}">
                        <div class="result-header">
                            <span class="result-icon">${icon}</span>
                            <span class="result-agent">${sr.agent_name || sr.agent_id || stId}</span>
                            <span class="location-badge ${sr.agent_location || ''}">${sr.agent_location || ''}</span>
                            <span class="result-latency">${sr.latency_ms ? sr.latency_ms.toFixed(0) + 'ms' : ''}</span>
                        </div>
                        <div class="result-output">${formattedOutput}</div>
                        ${sr.error ? `<div class="result-error">错误: ${sr.error}</div>` : ''}
                    </div>
                `;
            }
            html += '</div>';
        }

        document.getElementById('result-info').innerHTML = html;
    }

    // ========================================================================
    // 智能体管理
    // ========================================================================

    async function loadAgents() {
        try {
            const data = await api.getAgents();

            // 统计
            const s = data.statistics;
            document.getElementById('agents-stats').innerHTML = `
                <div class="stat-card">
                    <div class="stat-value">${s.total_agents}</div>
                    <div class="stat-label">总智能体</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${s.available_agents}</div>
                    <div class="stat-label">可用</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${(s.avg_load * 100).toFixed(0)}%</div>
                    <div class="stat-label">平均负载</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${Object.keys(s.by_location).length}</div>
                    <div class="stat-label">位置类型</div>
                </div>
            `;

            // 智能体卡片
            document.getElementById('agents-list').innerHTML = data.agents.map(agent => `
                <div class="agent-card">
                    <div class="agent-header">
                        <h4>${agent.name}</h4>
                        <span class="location-badge ${agent.location}">${agent.location}</span>
                    </div>
                    <p class="agent-desc">${agent.description}</p>
                    <div class="agent-metrics">
                        <span>负载: ${(agent.current_load * 100).toFixed(0)}%</span>
                        <span>延迟: ${agent.avg_latency_ms}ms</span>
                        <span>成本: $${agent.cost_per_invocation}</span>
                        <span>可靠性: ${(agent.reliability_score * 100).toFixed(0)}%</span>
                    </div>
                    <div class="agent-tools">
                        <strong>工具:</strong> ${agent.tools.map(t => `<code>${t}</code>`).join(', ')}
                    </div>
                    <div class="capability-list">
                        ${agent.capabilities.map(c => `<span class="capability-tag">${c.type} ${(c.quality * 100).toFixed(0)}%</span>`).join('')}
                    </div>
                </div>
            `).join('');
        } catch (error) {
            console.error('加载智能体失败:', error);
        }
    }

    // ========================================================================
    // 刷新智能体
    // ========================================================================

    document.getElementById('refresh-agents-btn').addEventListener('click', loadAgents);

    // ========================================================================
    // 实验
    // ========================================================================

    document.getElementById('run-experiment-btn').addEventListener('click', async function () {
        const scenario = document.getElementById('scenario-select').value;
        const numTasks = parseInt(document.getElementById('num-tasks').value);

        setButtonLoading(this, '运行中...');
        showElement('experiment-status');

        try {
            const result = await api.runExperiment(scenario, numTasks, ['tacn', 'cloud_only', 'cpn', 'semantic']);
            alert('实验完成! ID: ' + result.experiment_id);

            const chartData = await api.getExperimentChart(result.experiment_id);
            if (chartData.charts && Object.keys(chartData.charts).length > 0) {
                charts.plotAll(chartData.charts);
            }

            document.querySelector('[data-section="results"]').click();
        } catch (error) {
            showError('实验失败: ' + error.message);
        } finally {
            resetButton(this, '运行实验');
            hideElement('experiment-status');
        }
    });

    // ========================================================================
    // 工具函数
    // ========================================================================

    function setButtonLoading(btn, text) {
        btn.disabled = true;
        btn.textContent = text;
    }

    function resetButton(btn, text) {
        btn.disabled = false;
        btn.textContent = text;
    }

    function showElement(id) {
        document.getElementById(id).classList.remove('hidden');
    }

    function hideElement(id) {
        document.getElementById(id).classList.add('hidden');
    }

    function showError(msg) {
        alert(msg);
    }
});
