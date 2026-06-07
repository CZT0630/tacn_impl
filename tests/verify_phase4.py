"""阶段四验证脚本."""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.core.models import (
    SubTask, SubTaskGraph, SubTaskEdge, CapabilityRequirement,
    CapabilityType, PrivacyLevel, Location, Intent, IntentType,
    AgentAssignment,
)
from backend.registry.agent_registry import create_default_registry
from backend.registry.model_registry import create_default_model_registry
from backend.registry.tool_registry import create_default_tool_registry
from backend.registry.context_registry import create_default_context_registry
from backend.infrastructure.network import NetworkModel
from backend.infrastructure.resource_monitor import ResourceMonitor
from backend.infrastructure.node import NodeStatus

print("=" * 60)
print("阶段四 验证")
print("=" * 60)

agent_reg = create_default_registry()
model_reg = create_default_model_registry()
tool_reg = create_default_tool_registry()
ctx_reg = create_default_context_registry()
net = NetworkModel()

# ============================================================
# 4.1 MTCCOrchestrator
# ============================================================
from backend.orchestration.mtcc_orchestrator import MTCCOrchestrator, MTCCDecision, MTCCConfig

mtcc = MTCCOrchestrator(agent_reg, model_reg, tool_reg, ctx_reg, net)

print("\n--- 4.1 MTCCOrchestrator ---")

# 4.1.1 单子任务决策 - 感知任务
st1 = SubTask(
    name="sensor_analysis", description="传感器分析",
    required_capabilities=[CapabilityRequirement(capability_type=CapabilityType.SENSING, min_quality=0.5)],
    required_tools=["temperature_sensor"], required_context=["sensor_history"],
    privacy_level=PrivacyLevel.INTERNAL,
)
d1 = mtcc.orchestrate_subtask(st1)
assert isinstance(d1, MTCCDecision), "MTCCDecision type"
assert d1.selected_agent_id, "agent selected"
assert d1.selected_model, "model selected"
assert "temperature_sensor" in d1.selected_tools, "tool selected"
assert "sensor_history" in d1.selected_context, "context selected"
assert d1.privacy_action == "allow_remote", f"privacy={d1.privacy_action}"
assert d1.execution_mode == "direct", f"exec_mode={d1.execution_mode}"
assert d1.score > 0, f"score={d1.score}"
print(f"  感知任务: agent={d1.selected_agent_id[:8]}... model={d1.selected_model} score={d1.score:.3f} [OK]")

# 4.1.2 RESTRICTED 隐私 -> local_only
st2 = SubTask(
    name="security_scan", description="安全扫描",
    required_capabilities=[CapabilityRequirement(capability_type=CapabilityType.REASONING, min_quality=0.5)],
    privacy_level=PrivacyLevel.RESTRICTED,
)
d2 = mtcc.orchestrate_subtask(st2)
assert d2.privacy_action == "local_only", f"RESTRICTED should be local_only, got {d2.privacy_action}"
print(f"  RESTRICTED->local_only: {d2.privacy_action} [OK]")

# 4.1.3 CONFIDENTIAL + CLOUD -> anonymize
st3 = SubTask(
    name="cloud_analysis", description="云端分析",
    required_capabilities=[CapabilityRequirement(capability_type=CapabilityType.REASONING, min_quality=0.9)],
    privacy_level=PrivacyLevel.CONFIDENTIAL,
)
d3 = mtcc.orchestrate_subtask(st3)
if d3.selected_compute_tier == Location.CLOUD:
    assert d3.privacy_action == "anonymize", f"CONFIDENTIAL+CLOUD should be anonymize, got {d3.privacy_action}"
    print(f"  CONFIDENTIAL+CLOUD->anonymize: {d3.privacy_action} [OK]")
else:
    print(f"  CONFIDENTIAL->{d3.privacy_action} (compute={d3.selected_compute_tier.value}) [OK]")

# 4.1.4 多能力子任务 -> collaborative
st4 = SubTask(
    name="complex_task", description="复杂任务",
    required_capabilities=[
        CapabilityRequirement(capability_type=CapabilityType.VISION, min_quality=0.5),
        CapabilityRequirement(capability_type=CapabilityType.REASONING, min_quality=0.5),
        CapabilityRequirement(capability_type=CapabilityType.SENSING, min_quality=0.5),
    ],
)
d4 = mtcc.orchestrate_subtask(st4)
assert d4.execution_mode == "collaborative", f"should be collaborative, got {d4.execution_mode}"
print(f"  多能力->collaborative: {d4.execution_mode} [OK]")

# 4.1.5 orchestrate_graph - 带依赖的子任务图
graph = SubTaskGraph(
    intent_id="test",
    subtasks=[st1, st2],
    edges=[SubTaskEdge(source_id=st1.id, target_id=st2.id)],
)
decisions = mtcc.orchestrate_graph(graph)
assert len(decisions) == 2, f"expected 2 decisions, got {len(decisions)}"
assert decisions[0].subtask_id == st1.id, "topo order: st1 first"
assert decisions[1].subtask_id == st2.id, "topo order: st2 second"
print(f"  orchestrate_graph: {len(decisions)} decisions, topo order correct [OK]")

# 4.1.6 评分维度完整性
expected_keys = {"capability", "model_quality", "tool_coverage", "context_relevance", "latency", "cost", "privacy"}
assert expected_keys == set(d1.score_breakdown.keys()), f"score keys: {set(d1.score_breakdown.keys())}"
print(f"  评分7维度: {sorted(d1.score_breakdown.keys())} [OK]")

# ============================================================
# 4.2 三个控制面
# ============================================================
print("\n--- 4.2 三个控制面 ---")

# ResourceControlPlane
from backend.control_planes.resource_control import ResourceControlPlane
rm = ResourceMonitor()
rm.register_node(NodeStatus(node_id="t1", location=Location.TERMINAL, cpu_usage=0.3))
rm.register_node(NodeStatus(node_id="e1", location=Location.EDGE, cpu_usage=0.7))
rm.register_node(NodeStatus(node_id="c1", location=Location.CLOUD, cpu_usage=0.9))
rcp = ResourceControlPlane(net, rm, agent_reg)

status = rcp.get_resource_status()
assert status["total_nodes"] == 3
assert status["online_nodes"] == 3
print(f'  Resource: {status["total_nodes"]} nodes, {status["online_nodes"]} online [OK]')

congestion = rcp.get_congestion_report()
assert not congestion["terminal"]["congested"]  # 0.3 < 0.8
assert not congestion["edge"]["congested"]      # 0.7 < 0.8
assert congestion["cloud"]["congested"]          # 0.9 > 0.8
print(f'  Congestion: terminal={congestion["terminal"]["congested"]}, cloud={congestion["cloud"]["congested"]} [OK]')

latency = rcp.estimate_end_to_end_latency(Location.TERMINAL, Location.CLOUD, 500)
assert latency == 80 + 500  # network + computation
print(f"  E2E latency: {latency}ms [OK]")

links = rcp.get_network_links()
assert len(links) == 7
print(f"  Network links: {len(links)} [OK]")

# SemanticControlPlane
from backend.control_planes.semantic_control import SemanticControlPlane
scp = SemanticControlPlane(agent_reg, model_reg, tool_reg, ctx_reg)

intent = Intent(
    text="test",
    intent_type=IntentType.EMERGENCY_RESPONSE,
    required_capabilities=[
        CapabilityRequirement(capability_type=CapabilityType.SENSING, min_quality=0.5),
        CapabilityRequirement(capability_type=CapabilityType.VISION, min_quality=0.5),
    ],
)
caps = scp.discover_capabilities(intent)
assert "sensing" in caps and "vision" in caps
print(f"  Semantic discover: {list(caps.keys())} [OK]")

topo = scp.get_collaboration_topology([
    AgentAssignment(subtask_id="s1", agent_id="a1", location=Location.TERMINAL),
    AgentAssignment(subtask_id="s2", agent_id="a2", location=Location.EDGE),
])
assert topo["num_agents"] == 2
assert topo["num_locations"] == 2
print(f'  Collaboration topo: {topo["num_agents"]} agents, {topo["num_locations"]} locations [OK]')

assert len(scp.get_available_models()) == 4
assert len(scp.get_available_tools()) == 8
assert len(scp.get_available_contexts()) == 8
print(f"  Resources: 4 models, 8 tools, 8 contexts [OK]")

# TrustPrivacyControlPlane
from backend.control_planes.trust_privacy_control import TrustPrivacyControlPlane
tpc = TrustPrivacyControlPlane()

agent = agent_reg.get_all_agents()[0]  # phone_agent, CONFIDENTIAL
st_conf = SubTask(name="t", privacy_level=PrivacyLevel.CONFIDENTIAL)
st_rest = SubTask(name="t", privacy_level=PrivacyLevel.RESTRICTED)
st_int = SubTask(name="t", privacy_level=PrivacyLevel.INTERNAL)

assert tpc.is_privacy_compatible(st_conf, agent), "CONFIDENTIAL agent handles CONFIDENTIAL task"
assert not tpc.is_privacy_compatible(st_rest, agent), "CONFIDENTIAL agent cannot handle RESTRICTED"
assert tpc.is_privacy_compatible(st_int, agent), "CONFIDENTIAL agent handles INTERNAL"
print(f"  Privacy compat: CONF={tpc.is_privacy_compatible(st_conf,agent)}, REST={tpc.is_privacy_compatible(st_rest,agent)} [OK]")

filtered = tpc.filter_sensitive_data(
    {"user_id": "123", "data": "test", "password": "x", "token": "y"},
    PrivacyLevel.CONFIDENTIAL,
)
assert set(filtered.keys()) == {"data"}, f"filtered keys: {set(filtered.keys())}"
print(f"  Data filter: {list(filtered.keys())} [OK]")

assert tpc.evaluate_trust(agent) == 1.0
print(f"  Trust score: {tpc.evaluate_trust(agent)} [OK]")

# ============================================================
# 4.3 TACNSystem 集成
# ============================================================
print("\n--- 4.3 TACNSystem 集成 ---")

from backend.orchestration.tacn_system import TACNSystem

# MTCC 模式
tacn_mtcc = TACNSystem(
    agent_reg,
    model_registry=model_reg,
    tool_registry=tool_reg,
    context_registry=ctx_reg,
    network_model=net,
)
assert tacn_mtcc.use_mtcc == True
assert hasattr(tacn_mtcc, "mtcc")
assert hasattr(tacn_mtcc, "resource_control")
assert hasattr(tacn_mtcc, "semantic_control")
assert hasattr(tacn_mtcc, "trust_control")
print(f"  MTCC mode: use_mtcc={tacn_mtcc.use_mtcc}, has mtcc/resource/semantic/trust [OK]")

# 简单模式（向后兼容）
tacn_simple = TACNSystem(agent_reg)
assert tacn_simple.use_mtcc == False
assert hasattr(tacn_simple, "router")
print(f"  Simple mode: use_mtcc={tacn_simple.use_mtcc}, has router [OK]")


# MTCC 模式处理请求
async def test_mtcc():
    plan = await tacn_mtcc.process_request("实验楼烟雾传感器报警，请判断是否触发消防告警")
    assert plan.metadata["routing_mode"] == "mtcc"
    assert len(plan.assignments) > 0
    return plan


plan = asyncio.run(test_mtcc())
print(f'  MTCC request: {len(plan.subtask_graph.subtasks)} subtasks, {len(plan.assignments)} assignments, mode={plan.metadata["routing_mode"]} [OK]')


# 简单模式处理请求
async def test_simple():
    plan = await tacn_simple.process_request("实验楼烟雾传感器报警")
    assert plan.metadata["routing_mode"] == "simple"
    return plan


plan2 = asyncio.run(test_simple())
print(f'  Simple request: {len(plan2.subtask_graph.subtasks)} subtasks, mode={plan2.metadata["routing_mode"]} [OK]')

# ============================================================
# 4.4 demo 回归测试
# ============================================================
print("\n--- 4.4 demo 回归测试 ---")

import subprocess

demos = [
    "examples/demo_tacn.py",
    "examples/demo.py",
    "examples/demo_agent.py",
    "examples/demo_multi_agent.py",
    "examples/demo_agent_communication.py",
]
all_pass = True
for d in demos:
    r = subprocess.run([sys.executable, d], capture_output=True, timeout=60)
    status = "PASS" if r.returncode == 0 else "FAIL"
    print(f"  {status}: {d}")
    if r.returncode != 0:
        all_pass = False
        lines = r.stderr.decode(errors="replace").strip().split("\n")
        for l in lines[-3:]:
            print(f"    {l}")

print("\n" + "=" * 60)
if all_pass:
    print("阶段四 全部验证通过")
else:
    print("阶段四 部分验证失败")
print("=" * 60)
