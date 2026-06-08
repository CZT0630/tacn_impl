/**
 * TACN 主应用逻辑 v2
 * - Toast 通知替代 alert
 * - Loading spinner 动画
 * - Ctrl+Enter 快捷提交
 * - 平滑过渡动画
 */

document.addEventListener('DOMContentLoaded', function () {
    let currentTaskId = null;
    let currentPlan = null;

    // ========================================================================
    // Toast 通知系统
    // ========================================================================

    const toast = {
        _container: null,

        _getContainer() {
            if (!this._container) {
                this._container = document.getElementById('toast-container');
            }
            return this._container;
        },

        show(message, type = 'info', duration = 3000) {
            const container = this._getContainer();
            const el = document.createElement('div');
            el.className = `toast ${type}`;

            const icons = { success: '✅', error: '❌', info: 'ℹ️', warning: '⚠️' };
            el.innerHTML = `<span class="toast-icon">${icons[type] || ''}</span><span>${message}</span>`;

            container.appendChild(el);

            setTimeout(() => {
                el.classList.add('removing');
                el.addEventListener('animationend', () => el.remove());
            }, duration);
        },

        success(msg) { this.show(msg, 'success'); },
        error(msg)   { this.show(msg, 'error', 5000); },
        info(msg)    { this.show(msg, 'info'); },
        warning(msg) { this.show(msg, 'warning', 4000); },
    };

    // 暴露给全局（charts.js 等也能用）
    window.toast = toast;

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

    // Ctrl+Enter 快捷提交
    taskInput.addEventListener('keydown', function (e) {
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
            e.preventDefault();
            if (!processBtn.disabled) processBtn.click();
        }
    });

    // 快捷场景按钮
    document.querySelectorAll('.scenario-btn').forEach(btn => {
        btn.addEventListener('click', function () {
            taskInput.value = this.dataset.text;
            taskInput.focus();
            toast.info('已填入场景，按 Ctrl+Enter 或点击"处理请求"');
        });
    });

    processBtn.addEventListener('click', async function () {
        const input = taskInput.value.trim();
        if (!input) { toast.warning('请输入任务请求'); return; }

        setButtonLoading(processBtn);
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
            toast.success('意图解析完成，执行计划已生成');
        } catch (error) {
            toast.error('处理失败: ' + error.message);
        } finally {
            resetButton(processBtn, '处理请求');
        }
    });

    executeBtn.addEventListener('click', async function () {
        if (!currentTaskId) { toast.warning('请先处理请求'); return; }

        setButtonLoading(executeBtn);
        hideElement('execution-result');

        try {
            const result = await api.executeTask(currentTaskId);
            displayResult(result);
            showElement('execution-result');
            toast.success(`执行完成，耗时 ${result.actual_latency_ms.toFixed(0)}ms`);
        } catch (error) {
            toast.error('执行失败: ' + error.message);
        } finally {
            resetButton(executeBtn, '执行任务');
        }
    });

    // ========================================================================
    // 显示执行计划
    // ========================================================================

    function displayPlan(plan) {
        const intentTypeNames = {
            emergency_response: '🔥 应急响应',
            robot_inspection: '🔍 设备巡检',
            security_monitoring: '🛡️ 安防监控',
            predictive_maintenance: '🔧 预测维护',
            meeting_assistant: '📋 会议助手',
        };
        const typeName = intentTypeNames[plan.intent.type] || plan.intent.type;

        document.getElementById('plan-info').innerHTML = `
            <div class="stats-row">
                <div class="stat-card">
                    <div class="stat-value">${typeName}</div>
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
                <span class="meta-tag">🔒 ${plan.intent.privacy_level}</span>
                <span class="meta-tag">🤝 协作: ${plan.intent.requires_collaboration ? '是' : '否'}</span>
                <span class="meta-tag">⏱️ 截止: ${plan.intent.deadline_ms}ms</span>
                <span class="meta-tag">⚙️ ${plan.metadata.routing_mode || 'unknown'}</span>
            </div>
            <p class="request-text"><strong>用户请求:</strong> ${escapeHtml(plan.intent.text)}</p>
        `;

        renderDAG(plan);

        // 分配表
        const assignmentMap = {};
        plan.assignments.forEach(a => assignmentMap[a.subtask_id] = a);

        document.getElementById('assignments-list').innerHTML = plan.subtask_graph.subtasks.map((st, i) => {
            const a = assignmentMap[st.id];
            const loc = a ? a.location : '?';
            const agentShort = a ? a.agent_id.substring(0, 8) : '?';
            const dur = a ? a.estimated_duration_ms.toFixed(0) : '?';
            return `
                <div class="assignment-row">
                    <span class="asgn-index">${i + 1}</span>
                    <span class="asgn-name">${escapeHtml(st.name)}</span>
                    <span class="asgn-arrow">→</span>
                    <span class="asgn-agent">${agentShort}...</span>
                    <span class="location-badge ${loc}">${loc}</span>
                    <span style="font-size:11px;color:#b2bec3;margin-left:8px;">${dur}ms</span>
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
        const groups = plan.parallel_groups;
        const assignmentMap = {};
        plan.assignments.forEach(a => assignmentMap[a.subtask_id] = a);

        if (!groups || groups.length === 0) {
            container.innerHTML = '<div class="empty-state"><div class="empty-icon">📭</div><p>无并行组信息</p></div>';
            return;
        }

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
                    <div class="node-name">${escapeHtml(st.name)}</div>
                    <div class="node-loc">${loc}</div>
                </div>`;
            });

            html += '</div></div>';

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
        const statusText = result.success ? '✅ 成功' : '❌ 失败';

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

        const results = result.subtask_results;
        if (results && Object.keys(results).length > 0) {
            html += '<h4>子任务执行详情</h4>';
            html += '<div class="subtask-results">';
            for (const [stId, sr] of Object.entries(results)) {
                if (!sr || typeof sr !== 'object') continue;
                const icon = sr.success ? '✅' : '❌';
                const output = sr.output || '';
                const shortOutput = output.length > 500 ? output.substring(0, 500) + '...' : output;
                const formattedOutput = shortOutput
                    .replace(/### (.*)/g, '<strong>$1</strong>')
                    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                    .replace(/\n/g, '<br>');

                html += `
                    <div class="result-card ${sr.success ? 'success' : 'fail'}">
                        <div class="result-header">
                            <span class="result-icon">${icon}</span>
                            <span class="result-agent">${escapeHtml(sr.agent_name || sr.agent_id || stId)}</span>
                            <span class="location-badge ${sr.agent_location || ''}">${sr.agent_location || ''}</span>
                            <span class="result-latency">${sr.latency_ms ? sr.latency_ms.toFixed(0) + 'ms' : ''}</span>
                        </div>
                        <div class="result-output">${formattedOutput}</div>
                        ${sr.error ? `<div class="result-error">错误: ${escapeHtml(sr.error)}</div>` : ''}
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

            document.getElementById('agents-list').innerHTML = data.agents.map(agent => `
                <div class="agent-card">
                    <div class="agent-header">
                        <h4>${escapeHtml(agent.name)}</h4>
                        <span class="location-badge ${agent.location}">${agent.location}</span>
                    </div>
                    <p class="agent-desc">${escapeHtml(agent.description)}</p>
                    <div class="agent-metrics">
                        <span>📊 负载: ${(agent.current_load * 100).toFixed(0)}%</span>
                        <span>⏱️ 声明: ${agent.avg_latency_ms}ms</span>
                        <span>💰 $${agent.cost_per_invocation}</span>
                        <span>🔒 ${agent.privacy_level}</span>
                    </div>
                    <div class="agent-metrics">
                        <span>📈 可靠性: ${(agent.reliability_score * 100).toFixed(0)}%</span>
                        <span>🔧 工具成功率: ${((agent.tool_success_rate || 1) * 100).toFixed(0)}%</span>
                        <span>📦 上下文命中: ${((agent.context_hit_rate || 0) * 100).toFixed(0)}%</span>
                        <span>⏱️ 实测: ${(agent.observed_latency_ms || 0).toFixed(0)}ms</span>
                    </div>
                    <div class="agent-tools">
                        <strong>工具:</strong> ${agent.tools.map(t => `<code>${escapeHtml(t)}</code>`).join(', ')}
                    </div>
                    <div class="capability-list">
                        ${agent.capabilities.map(c => `<span class="capability-tag">${c.type} ${(c.quality * 100).toFixed(0)}%</span>`).join('')}
                    </div>
                </div>
            `).join('');

            // 反馈面板
            const fb = data.feedback;
            if (fb && fb.total_executions > 0) {
                let feedbackHtml = `
                    <div class="feedback-panel">
                        <h3>📊 反馈闭环统计</h3>
                        <div class="feedback-grid">
                            <div class="feedback-item">
                                <div class="fi-label">总执行次数</div>
                                <div class="fi-value">${fb.total_executions}</div>
                            </div>
                            <div class="feedback-item">
                                <div class="fi-label">总体成功率</div>
                                <div class="fi-value">${(fb.overall_success_rate * 100).toFixed(1)}%</div>
                            </div>
                        </div>`;

                const policies = fb.intent_policies || {};
                const policyKeys = Object.keys(policies);
                if (policyKeys.length > 0) {
                    feedbackHtml += '<h4 style="margin-top:16px">意图类型策略</h4><div class="feedback-grid">';
                    for (const [intentType, p] of Object.entries(policies)) {
                        const names = {
                            emergency_response: '🔥 应急响应',
                            robot_inspection: '🔍 设备巡检',
                            security_monitoring: '🛡️ 安防监控',
                            predictive_maintenance: '🔧 预测维护',
                            meeting_assistant: '📋 会议助手',
                        };
                        feedbackHtml += `
                            <div class="feedback-item">
                                <div class="fi-label">${names[intentType] || intentType}</div>
                                <div class="fi-value" style="font-size:14px">
                                    成功率 ${(p.success_rate * 100).toFixed(0)}% ·
                                    P95 ${p.p95_latency_ms.toFixed(0)}ms ·
                                    建议deadline ${p.suggested_deadline_ms.toFixed(0)}ms
                                </div>
                            </div>`;
                    }
                    feedbackHtml += '</div>';
                }

                feedbackHtml += '</div>';
                document.getElementById('agents-list').insertAdjacentHTML('beforebegin', feedbackHtml);
            }
        } catch (error) {
            toast.error('加载智能体失败: ' + error.message);
        }
    }

    document.getElementById('refresh-agents-btn').addEventListener('click', () => {
        loadAgents();
        toast.info('正在刷新智能体列表...');
    });

    // ========================================================================
    // 实验
    // ========================================================================

    document.getElementById('run-experiment-btn').addEventListener('click', async function () {
        const scenario = document.getElementById('scenario-select').value;
        const numTasks = parseInt(document.getElementById('num-tasks').value);

        setButtonLoading(this);
        showElement('experiment-status');

        try {
            const result = await api.runExperiment(scenario, numTasks, ['tacn', 'cloud_only', 'cpn', 'semantic']);
            toast.success('实验完成! ID: ' + result.experiment_id);

            const chartData = await api.getExperimentChart(result.experiment_id);
            if (chartData.charts && Object.keys(chartData.charts).length > 0) {
                charts.plotAll(chartData.charts);
            }

            document.querySelector('[data-section="results"]').click();
        } catch (error) {
            toast.error('实验失败: ' + error.message);
        } finally {
            resetButton(this, '运行实验');
            hideElement('experiment-status');
        }
    });

    // ========================================================================
    // 工具函数
    // ========================================================================

    function setButtonLoading(btn) {
        btn.classList.add('loading');
        btn.disabled = true;
    }

    function resetButton(btn, text) {
        btn.classList.remove('loading');
        btn.disabled = false;
        if (text) btn.textContent = text;
    }

    function showElement(id) {
        document.getElementById(id).classList.remove('hidden');
    }

    function hideElement(id) {
        document.getElementById(id).classList.add('hidden');
    }

    function escapeHtml(str) {
        if (!str) return '';
        return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }
});
