"""TACN-Proto CLI 入口."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path


def run_experiment(config_path: str):
    """运行实验."""
    from backend.core.config import TACNConfig

    core_config = Path(__file__).parent / "configs" / "config.yaml"
    config = TACNConfig(core_config, config_path)
    exp = config.experiment_config
    print(f"实验名称: {exp.get('name', 'unnamed')}")
    print(f"描述: {exp.get('description', '')}")
    print(f"种子: {config.get_seed()}")
    print(f"任务数: {config.get_num_tasks()}")
    print(f"到达率: {config.get_arrival_rate()}")
    print(f"方法: {config.get_methods()}")
    print(f"消融标志: {config.get_ablation_flags()}")
    print(f"输出目录: {config.get_output_dir()}")

    # 加载核心 catalog
    templates = config.get_intent_templates()
    print(f"\n意图模板 ({len(templates)}):")
    for name, tmpl in templates.items():
        print(f"  - {name}: {tmpl.get('description', '')}")

    capabilities = config.get_capability_vocabulary()
    print(f"\n能力词表 ({len(capabilities)}):")
    for name, cap in capabilities.items():
        print(f"  - {name}: {cap.get('description', '')}")

    # 加载场景
    scenarios = config.scenario_catalog
    print(f"\n场景 ({len(scenarios)}):")
    for name, scenario in scenarios.items():
        agents = scenario.get("agents", [])
        print(f"  - {name}: {scenario.get('description', '')} ({len(agents)} agents)")


def generate_plots(results_path: str, outdir: str):
    """生成图表."""
    print(f"从 {results_path} 生成图表到 {outdir}")
    print("图表生成功能待阶段六实现。")


def start_server(port: int):
    """启动 FastAPI 服务."""
    import uvicorn

    uvicorn.run("backend.main:app", host="0.0.0.0", port=port)


def main():
    parser = argparse.ArgumentParser(description="TACN-Proto 终端智能体算力网络原型系统")
    subparsers = parser.add_subparsers(dest="command")

    run_p = subparsers.add_parser("run", help="运行实验")
    run_p.add_argument("--config", required=True, help="配置文件路径")

    plot_p = subparsers.add_parser("plot", help="生成图表")
    plot_p.add_argument("--results", required=True, help="结果 CSV 路径")
    plot_p.add_argument("--outdir", default="outputs/figures", help="输出目录")

    serve_p = subparsers.add_parser("serve", help="启动 FastAPI 服务")
    serve_p.add_argument("--port", type=int, default=8000)

    args = parser.parse_args()

    if args.command == "run":
        run_experiment(args.config)
    elif args.command == "plot":
        generate_plots(args.results, args.outdir)
    elif args.command == "serve":
        start_server(args.port)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
