/**
 * TACN API 调用封装
 */

const API_BASE = '/api';

const api = {
    /**
     * 意图解析 + 子任务分解 + 路由
     */
    async processRequest(request, deadlineMs = 60000) {
        const response = await fetch(`${API_BASE}/tasks/process`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ request, deadline_ms: deadlineMs })
        });
        if (!response.ok) {
            const err = await response.json().catch(() => ({}));
            throw new Error(err.detail || response.statusText);
        }
        return response.json();
    },

    /**
     * 执行已规划的任务
     */
    async executeTask(taskId) {
        const response = await fetch(`${API_BASE}/tasks/execute`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ task_id: taskId })
        });
        if (!response.ok) {
            const err = await response.json().catch(() => ({}));
            throw new Error(err.detail || response.statusText);
        }
        return response.json();
    },

    /**
     * 获取所有智能体
     */
    async getAgents() {
        const response = await fetch(`${API_BASE}/agents`);
        if (!response.ok) throw new Error(response.statusText);
        return response.json();
    },

    /**
     * 运行对比实验
     */
    async runExperiment(scenario, numTasks, methods) {
        const response = await fetch(`${API_BASE}/experiments/run`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ scenario, num_tasks: numTasks, methods })
        });
        if (!response.ok) throw new Error(response.statusText);
        return response.json();
    },

    /**
     * 获取实验图表数据
     */
    async getExperimentChart(experimentId) {
        const response = await fetch(`${API_BASE}/experiments/${experimentId}/chart`);
        if (!response.ok) throw new Error(response.statusText);
        return response.json();
    }
};
