"""运行小样本 LLM Agent 真实调用验证."""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.registry.agent_registry import create_default_registry
from backend.registry.model_registry import create_default_model_registry
from backend.registry.tool_registry import create_default_tool_registry
from backend.registry.context_registry import create_default_context_registry
from backend.infrastructure.network import NetworkModel
from backend.orchestration.tacn_system import TACNSystem
from backend.llm.config import LLMConfig
from backend.workload.generator import WorkloadGenerator


async def main(num_tasks: int = 8, use_real: bool = False):
    registry = create_default_registry()

    llm_config = None
    if use_real:
        llm_config = LLMConfig(
            api_key=os.getenv("TACN_API_KEY", ""),
            base_url=os.getenv("TACN_BASE_URL", ""),
            model=os.getenv("TACN_MODEL", "gpt-4o-mini"),
        )

    system = TACNSystem(
        registry=registry,
        llm_config=llm_config,
        model_registry=create_default_model_registry(),
        tool_registry=create_default_tool_registry(),
        context_registry=create_default_context_registry(),
        network_model=NetworkModel(),
    )

    generator = WorkloadGenerator(seed=42)
    requests = generator.generate_mixed(num_tasks)

    results = []
    for i, req in enumerate(requests):
        print(f"[{i+1}/{num_tasks}] {req[:60]}...")
        plan = await system.process_request(req)
        result = await system.execute_plan(plan)
        results.append({
            "request": req,
            "intent_type": plan.intent.intent_type.value,
            "num_subtasks": len(plan.subtask_graph.subtasks),
            "success": result.success,
            "latency_ms": result.actual_latency_ms,
            "routing_mode": plan.metadata.get("routing_mode", "unknown"),
            "subtask_results": {
                k: {"success": v.get("success"), "latency_ms": v.get("latency_ms")}
                for k, v in result.subtask_results.items()
                if isinstance(v, dict)
            },
        })

    output_path = Path("outputs/default/llm_agent_samples.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\nResults written to {output_path}")
    success_count = sum(1 for r in results if r["success"])
    print(f"Success: {success_count}/{len(results)}")
    print(f"Routing mode: {results[0]['routing_mode'] if results else 'N/A'}")


if __name__ == "__main__":
    num_tasks = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    use_real = "--use-real" in sys.argv
    asyncio.run(main(num_tasks, use_real))
