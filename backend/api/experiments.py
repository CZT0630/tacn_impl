"""实验API."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.baselines.cloud_only import CloudOnlyBaseline
from backend.baselines.resource_aware_cpn import ResourceAwareCPN
from backend.baselines.semantic_router import SemanticOnlyRouter
from backend.core.models import IntentType, TaskResult
from backend.evaluation.metrics import MetricsCalculator
from backend.simulation.simulation import SimulationExecutor
from backend.orchestration.engine import OrchestrationEngine
from backend.registry.agent_registry import create_default_registry
from backend.workload.generator import WorkloadGenerator

router = APIRouter()

# 全局实例
registry = create_default_registry()
engine = OrchestrationEngine(registry)
executor = SimulationExecutor(registry, stochastic=True, seed=42)
workload_gen = WorkloadGenerator(seed=42)
metrics_calc = MetricsCalculator()

# 基线
cloud_only = CloudOnlyBaseline(registry)
cpn_baseline = ResourceAwareCPN(registry)
semantic_router = SemanticOnlyRouter(registry)

# 实验结果缓存
experiments_cache: dict[str, dict] = {}


class RunExperimentRequest(BaseModel):
    """运行实验请求."""
    scenario: str = "mixed"  # emergency_response, robot_inspection, security_monitoring, predictive_maintenance, mixed
    num_tasks: int = 50
    methods: list[str] = ["tacn", "cloud_only", "cpn", "semantic"]


@router.post("/run")
async def run_experiment(req: RunExperimentRequest) -> dict:
    """运行对比实验.

    Args:
        req: 实验请求

    Returns:
        实验ID
    """
    import uuid
    experiment_id = str(uuid.uuid4())

    # 生成工作负载
    if req.scenario == "mixed":
        requests = workload_gen.generate_mixed(req.num_tasks)
    else:
        try:
            intent_type = IntentType(req.scenario)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Unknown scenario: {req.scenario}")
        requests = workload_gen.generate(intent_type, req.num_tasks)

    # 运行各方法
    results: dict[str, list[TaskResult]] = {}

    for method in req.methods:
        method_results: list[TaskResult] = []

        for request in requests:
            try:
                if method == "tacn":
                    plan = await engine.process_request(request)
                elif method == "cloud_only":
                    plan = await cloud_only.process(request)
                elif method == "cpn":
                    plan = await cpn_baseline.process(request)
                elif method == "semantic":
                    plan = await semantic_router.process(request)
                else:
                    continue

                result = executor.execute(plan)
                method_results.append(result)
            except Exception:
                continue

        results[method] = method_results

    # 计算指标
    metrics: dict[str, dict] = {}
    for method, method_results in results.items():
        if method_results:
            metrics[method] = metrics_calc.calculate_all_metrics(method_results)

    # 缓存结果
    experiments_cache[experiment_id] = {
        "id": experiment_id,
        "status": "completed",
        "scenario": req.scenario,
        "num_tasks": req.num_tasks,
        "methods": req.methods,
        "metrics": metrics,
        "results": {m: len(r) for m, r in results.items()},
    }

    return {"experiment_id": experiment_id, "status": "completed"}


@router.get("/{experiment_id}")
async def get_experiment(experiment_id: str) -> dict:
    """获取实验结果.

    Args:
        experiment_id: 实验ID

    Returns:
        实验结果
    """
    exp = experiments_cache.get(experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")

    return exp


@router.get("/{experiment_id}/chart")
async def get_experiment_chart(experiment_id: str) -> dict:
    """获取实验图表数据.

    Args:
        experiment_id: 实验ID

    Returns:
        图表数据
    """
    exp = experiments_cache.get(experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")

    metrics = exp["metrics"]
    methods = list(metrics.keys())

    # 任务成功率
    task_success_rate = {
        "labels": methods,
        "values": [metrics[m].get("task_success_rate", 0) for m in methods],
    }

    # P95延迟
    latency_comparison = {
        "labels": methods,
        "values": [metrics[m].get("p95_latency_ms", 0) for m in methods],
    }

    # 成本对比
    cost_comparison = {
        "labels": methods,
        "values": [metrics[m].get("avg_cost", 0) for m in methods],
    }

    # 云端卸载比例
    cloud_ratio = {
        "labels": methods,
        "values": [metrics[m].get("cloud_offloading_ratio", 0) for m in methods],
    }

    # 隐私保护比例
    privacy_ratio = {
        "labels": methods,
        "values": [metrics[m].get("privacy_preservation_ratio", 0) for m in methods],
    }

    return {
        "task_success_rate": task_success_rate,
        "latency_comparison": latency_comparison,
        "cost_comparison": cost_comparison,
        "cloud_offloading_ratio": cloud_ratio,
        "privacy_preservation_ratio": privacy_ratio,
    }


@router.get("")
async def list_experiments() -> dict:
    """列出所有实验.

    Returns:
        实验列表
    """
    return {
        "experiments": list(experiments_cache.values())
    }
