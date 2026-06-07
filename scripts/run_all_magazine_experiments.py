"""运行 magazine 全量实验 - 对比 4 种方法."""

from __future__ import annotations

import asyncio
import csv
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.core.models import ExecutionPlan, TaskResult
from backend.registry.agent_registry import create_default_registry
from backend.registry.model_registry import create_default_model_registry
from backend.registry.tool_registry import create_default_tool_registry
from backend.registry.context_registry import create_default_context_registry
from backend.infrastructure.network import NetworkModel
from backend.orchestration.tacn_system import TACNSystem
from backend.simulation.simulation import SimulationExecutor
from backend.evaluation.metrics import MetricsCalculator
from backend.workload.generator import WorkloadGenerator
from backend.baselines.cloud_only import CloudOnlyBaseline
from backend.baselines.resource_aware_cpn import ResourceAwareCPN
from backend.baselines.semantic_router import SemanticOnlyRouter


async def run_baseline(method, requests: list[str], executor: SimulationExecutor) -> list[TaskResult]:
    """运行 baseline 方法（process + simulation）."""
    results = []
    for req in requests:
        try:
            plan = await method.process(req)
            result = executor.execute(plan)
            results.append(result)
        except Exception as e:
            print(f"  Error: {e}")
    return results


def reset_agent_loads(registry):
    """重置所有 agent 的负载为 0."""
    for agent in registry.get_all_agents():
        agent.current_load = 0.0


async def run_tacn(system: TACNSystem, requests: list[str],
                   executor: SimulationExecutor) -> list[TaskResult]:
    """运行 TACN 方法（process_request + simulation）."""
    results = []
    for req in requests:
        try:
            plan = await system.process_request(req)
            result = executor.execute(plan)
            results.append(result)
        except Exception as e:
            print(f"  Error: {e}")
    return results


async def main(num_tasks: int = 100, seed: int = 42):
    output_dir = Path("outputs/magazine")
    output_dir.mkdir(parents=True, exist_ok=True)

    generator = WorkloadGenerator(seed=seed)
    metrics = MetricsCalculator()

    requests = generator.generate_mixed(num_tasks)
    print(f"Generated {len(requests)} requests (seed={seed})")

    registry = create_default_registry()
    model_registry = create_default_model_registry()
    tool_registry = create_default_tool_registry()
    context_registry = create_default_context_registry()
    network_model = NetworkModel()

    executor = SimulationExecutor(registry, stochastic=True, seed=seed)

    methods = {
        "cloud_only": CloudOnlyBaseline(registry),
        "resource_aware_cpn": ResourceAwareCPN(registry),
        "semantic_router": SemanticOnlyRouter(registry),
        "tacn": TACNSystem(
            registry=registry,
            model_registry=model_registry,
            tool_registry=tool_registry,
            context_registry=context_registry,
            network_model=network_model,
        ),
    }

    all_results = {}
    for method_name, method in methods.items():
        reset_agent_loads(registry)
        print(f"\nRunning {method_name}...")
        start = time.time()

        if method_name == "tacn":
            results = await run_tacn(method, requests, executor)
        else:
            results = await run_baseline(method, requests, executor)

        elapsed = time.time() - start
        m = metrics.calculate_all_metrics(results)
        m["elapsed_seconds"] = round(elapsed, 2)
        all_results[method_name] = m

        print(f"  tasks={len(results)}, "
              f"success_rate={m['task_success_rate']:.3f}, "
              f"p95_latency={m['p95_latency_ms']:.0f}ms, "
              f"cost={m['total_cost']:.3f}, "
              f"time={elapsed:.1f}s")

    # 输出 CSV
    csv_path = output_dir / "results" / "overall.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["method"] + list(next(iter(all_results.values())).keys())
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for method_name, m in all_results.items():
            writer.writerow({"method": method_name, **m})

    print(f"\nResults written to {csv_path}")

    # 输出 JSON
    import json
    json_path = output_dir / "results" / "overall.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f"Results written to {json_path}")


if __name__ == "__main__":
    num_tasks = 100
    seed = 42
    for arg in sys.argv[1:]:
        if arg.startswith("--num-tasks="):
            num_tasks = int(arg.split("=")[1])
        elif arg.startswith("--seed="):
            seed = int(arg.split("=")[1])
        elif arg.isdigit():
            num_tasks = int(arg)
    asyncio.run(main(num_tasks, seed))
