/**
 * TACN图表可视化
 */

const charts = {
    instances: {},

    /**
     * 颜色配置
     */
    colors: {
        tacn: '#4CAF50',
        cloud_only: '#F44336',
        cpn: '#2196F3',
        semantic: '#FF9800'
    },

    /**
     * 方法名称映射
     */
    methodNames: {
        tacn: 'TACN',
        cloud_only: 'Cloud-only',
        cpn: 'Resource-aware CPN',
        semantic: 'Semantic-only'
    },

    /**
     * 绘制任务成功率
     */
    plotTaskSuccessRate(data) {
        const ctx = document.getElementById('successRateChart').getContext('2d');

        if (this.instances.successRate) {
            this.instances.successRate.destroy();
        }

        const labels = data.labels.map(l => this.methodNames[l] || l);
        const values = data.values.map(v => (v * 100).toFixed(1));

        this.instances.successRate = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: '任务成功率 (%)',
                    data: values,
                    backgroundColor: data.labels.map(l => this.colors[l] || '#999')
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        ticks: {
                            callback: value => value + '%'
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    }
                }
            }
        });
    },

    /**
     * 绘制延迟对比
     */
    plotLatencyComparison(data) {
        const ctx = document.getElementById('latencyChart').getContext('2d');

        if (this.instances.latency) {
            this.instances.latency.destroy();
        }

        const labels = data.labels.map(l => this.methodNames[l] || l);
        const values = data.values.map(v => v.toFixed(0));

        this.instances.latency = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'P95延迟 (ms)',
                    data: values,
                    backgroundColor: data.labels.map(l => this.colors[l] || '#999')
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    }
                }
            }
        });
    },

    /**
     * 绘制成本对比
     */
    plotCostComparison(data) {
        const ctx = document.getElementById('costChart').getContext('2d');

        if (this.instances.cost) {
            this.instances.cost.destroy();
        }

        const labels = data.labels.map(l => this.methodNames[l] || l);
        const values = data.values.map(v => v.toFixed(4));

        this.instances.cost = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: '平均成本 ($)',
                    data: values,
                    backgroundColor: data.labels.map(l => this.colors[l] || '#999')
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    }
                }
            }
        });
    },

    /**
     * 绘制云端卸载比例
     */
    plotCloudRatio(data) {
        const ctx = document.getElementById('cloudRatioChart').getContext('2d');

        if (this.instances.cloudRatio) {
            this.instances.cloudRatio.destroy();
        }

        const labels = data.labels.map(l => this.methodNames[l] || l);
        const values = data.values.map(v => (v * 100).toFixed(1));

        this.instances.cloudRatio = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: '云端卸载比例 (%)',
                    data: values,
                    backgroundColor: data.labels.map(l => this.colors[l] || '#999')
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        ticks: {
                            callback: value => value + '%'
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    }
                }
            }
        });
    },

    /**
     * 绘制所有图表
     */
    plotAll(chartData) {
        this.plotTaskSuccessRate(chartData.task_success_rate);
        this.plotLatencyComparison(chartData.latency_comparison);
        this.plotCostComparison(chartData.cost_comparison);
        this.plotCloudRatio(chartData.cloud_offloading_ratio);
    }
};
