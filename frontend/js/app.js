/**
 * TACN主应用逻辑
 */

document.addEventListener('DOMContentLoaded', function() {
    // 当前任务ID
    let currentTaskId = null;

    // 导航切换
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', function(e) {
            e.preventDefault();
            const section = this.dataset.section;

            // 更新导航状态
            document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
            this.classList.add('active');

            // 切换内容区
            document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
            document.getElementById(`${section}-section`).classList.add('active');

            // 加载数据
            if (section === 'agents') {
                loadAgents();
            }
        });
    });

    // 处理请求按钮
    document.getElementById('process-btn').addEventListener('click', async function() {
        const input = document.getElementById('task-input').value.trim();
        if (!input) {
            alert('请输入任务请求');
            return;
        }

        this.disabled = true;
        this.textContent = '处理中...';

        try {
            const result = await api.processRequest(input);
            currentTaskId = result.task_id;
            displayPlan(result);

            document.getElementById('execute-btn').disabled = false;
            document.getElementById('task-result').classList.remove('hidden');
        } catch (error) {
            alert('处理失败: ' + error.message);
        } finally {
            this.disabled = false;
            this.textContent = '处理请求';
        }
    });

    // 执行任务按钮
    document.getElementById('execute-btn').addEventListener('click', async function() {
        if (!currentTaskId) {
            alert('请先处理请求');
            return;
        }

        this.disabled = true;
        this.textContent = '执行中...';

        try {
            const result = await api.executeTask(currentTaskId);
            displayResult(result);

            document.getElementById('execution-result').classList.remove('hidden');
        } catch (error) {
            alert('执行失败: ' + error.message);
        } finally {
            this.disabled = false;
            this.textContent = '执行任务';
        }
    });

    // 刷新智能体按钮
    document.getElementById('refresh-agents-btn').addEventListener('click', loadAgents);

    // 运行实验按钮
    document.getElementById('run-experiment-btn').addEventListener('click', async function() {
        const scenario = document.getElementById('scenario-select').value;
        const numTasks = parseInt(document.getElementById('num-tasks').value);

        this.disabled = true;
        this.textContent = '运行中...';
        document.getElementById('experiment-status').classList.remove('hidden');

        try {
            const result = await api.runExperiment(scenario, numTasks, ['tacn', 'cloud_only', 'cpn', 'semantic']);
            alert('实验完成! ID: ' + result.experiment_id);

            // 加载图表
            const chartData = await api.getExperimentChart(result.experiment_id);
            charts.plotAll(chartData);

            // 切换到结果页面
            document.querySelector('[data-section="results"]').click();
        } catch (error) {
            alert('实验失败: ' + error.message);
        } finally {
            this.disabled = false;
            this.textContent = '运行实验';
            document.getElementById('experiment-status').classList.add('hidden');
        }
    });

    /**
     * 显示执行计划
     */
    function displayPlan(plan) {
        const planInfo = document.getElementById('plan-info');
        planInfo.innerHTML = `
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin-bottom: 20px;">
                <div class="stat-item">
                    <div class="stat-value">${plan.intent.type}</div>
                    <div class="stat-label">意图类型</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">${plan.estimated_total_latency_ms.toFixed(0)}ms</div>
                    <div class="stat-label">预估延迟</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">$${plan.estimated_total_cost.toFixed(4)}</div>
                    <div class="stat-label">预估成本</div>
                </div>
            </div>
            <p style="color: #666; font-size: 14px;"><strong>请求:</strong> ${plan.intent.text}</p>
        `;

        // 子任务列表
        const subtasksList = document.getElementById('subtasks-list');
        subtasksList.innerHTML = plan.subtask_graph.subtasks.map((st, i) => `
            <div class="subtask-item">
                <div class="subtask-index">${i + 1}</div>
                <div class="subtask-info">
                    <div class="subtask-name">${st.name}</div>
                    <div class="subtask-desc">${st.description}</div>
                </div>
            </div>
        `).join('');

        // 分配列表
        const assignmentsList = document.getElementById('assignments-list');
        assignmentsList.innerHTML = plan.assignments.map(a => {
            const subtask = plan.subtask_graph.subtasks.find(st => st.id === a.subtask_id);
            return `
                <div class="assignment-item">
                    <span class="assignment-subtask">${subtask ? subtask.name : a.subtask_id}</span>
                    <span class="assignment-arrow">→</span>
                    <span class="assignment-agent">${a.agent_id.substring(0, 8)}...</span>
                    <span class="assignment-location">(${a.location})</span>
                </div>
            `;
        }).join('');
    }

    /**
     * 显示执行结果
     */
    function displayResult(result) {
        const resultInfo = document.getElementById('result-info');
        const statusClass = result.success ? 'color: #4CAF50' : 'color: #F44336';
        const statusText = result.success ? '成功' : '失败';

        resultInfo.innerHTML = `
            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px;">
                <div class="stat-item">
                    <div class="stat-value" style="${statusClass}">${statusText}</div>
                    <div class="stat-label">执行状态</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">${result.actual_latency_ms.toFixed(0)}ms</div>
                    <div class="stat-label">实际延迟</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">$${result.actual_cost.toFixed(4)}</div>
                    <div class="stat-label">实际成本</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">${Object.keys(result.subtask_results).length}</div>
                    <div class="stat-label">子任务数</div>
                </div>
            </div>
        `;
    }

    /**
     * 加载智能体
     */
    async function loadAgents() {
        try {
            const data = await api.getAgents();

            // 显示统计
            const statsPanel = document.getElementById('agents-stats');
            statsPanel.innerHTML = `
                <div class="stat-item">
                    <div class="stat-value">${data.statistics.total_agents}</div>
                    <div class="stat-label">总智能体数</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">${data.statistics.available_agents}</div>
                    <div class="stat-label">可用智能体</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">${(data.statistics.avg_load * 100).toFixed(0)}%</div>
                    <div class="stat-label">平均负载</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">${data.statistics.by_location.edge || 0}</div>
                    <div class="stat-label">边缘节点</div>
                </div>
            `;

            // 显示智能体列表
            const agentsList = document.getElementById('agents-list');
            agentsList.innerHTML = data.agents.map(agent => `
                <div class="agent-card">
                    <h4>${agent.name}</h4>
                    <span class="agent-location ${agent.location}">${agent.location}</span>
                    <p style="font-size: 13px; color: #666; margin: 10px 0;">${agent.description}</p>
                    <div style="font-size: 12px; color: #888;">
                        <div>负载: ${(agent.current_load * 100).toFixed(0)}% / ${(agent.max_concurrent_tasks * 100).toFixed(0)}%</div>
                        <div>延迟: ${agent.avg_latency_ms}ms | 成本: $${agent.cost_per_invocation}</div>
                    </div>
                    <div class="capability-list">
                        ${agent.capabilities.map(c => `<span class="capability-tag">${c.type}</span>`).join('')}
                    </div>
                </div>
            `).join('');
        } catch (error) {
            console.error('加载智能体失败:', error);
        }
    }
});
