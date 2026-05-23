/**
 * TACN API调用封装
 */

const API_BASE = 'http://localhost:8000/api';

const api = {
    /**
     * 处理任务请求
     */
    async processRequest(request, deadlineMs = 30000) {
        const response = await fetch(`${API_BASE}/tasks/process`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ request, deadline_ms: deadlineMs })
        });
        if (!response.ok) {
            throw new Error(`API error: ${response.statusText}`);
        }
        return response.json();
    },

    /**
     * 执行任务
     */
    async executeTask(taskId) {
        const response = await fetch(`${API_BASE}/tasks/execute`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ task_id: taskId })
        });
        if (!response.ok) {
            throw new Error(`API error: ${response.statusText}`);
        }
        return response.json();
    },

    /**
     * 获取所有智能体
     */
    async getAgents() {
        const response = await fetch(`${API_BASE}/agents`);
        if (!response.ok) {
            throw new Error(`API error: ${response.statusText}`);
        }
        return response.json();
    },

    /**
     * 运行实验
     */
    async runExperiment(scenario, numTasks, methods) {
        const response = await fetch(`${API_BASE}/experiments/run`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                scenario,
                num_tasks: numTasks,
                methods
            })
        });
        if (!response.ok) {
            throw new Error(`API error: ${response.statusText}`);
        }
        return response.json();
    },

    /**
     * 获取实验结果
     */
    async getExperiment(experimentId) {
        const response = await fetch(`${API_BASE}/experiments/${experimentId}`);
        if (!response.ok) {
            throw new Error(`API error: ${response.statusText}`);
        }
        return response.json();
    },

    /**
     * 获取实验图表数据
     */
    async getExperimentChart(experimentId) {
        const response = await fetch(`${API_BASE}/experiments/${experimentId}/chart`);
        if (!response.ok) {
            throw new Error(`API error: ${response.statusText}`);
        }
        return response.json();
    }
};
