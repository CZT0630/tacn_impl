"""TACN 系统集成测试."""

import pytest
from backend.core.models import TaskStatus
from backend.orchestration.tacn_system import TACNSystem
from backend.registry.agent_registry import create_default_registry
from backend.registry.model_registry import create_default_model_registry
from backend.registry.tool_registry import create_default_tool_registry
from backend.registry.context_registry import create_default_context_registry
from backend.infrastructure.network import NetworkModel


@pytest.fixture
def tacn_system():
    reg = create_default_registry()
    return TACNSystem(
        registry=reg,
        model_registry=create_default_model_registry(),
        tool_registry=create_default_tool_registry(),
        context_registry=create_default_context_registry(),
        network_model=NetworkModel(),
    )


@pytest.mark.asyncio
async def test_full_pipeline(tacn_system):
    plan = await tacn_system.process_request("实验楼烟雾传感器报警，请结合摄像头画面判断")
    assert plan is not None
    assert len(plan.subtask_graph.subtasks) > 0
    assert len(plan.assignments) > 0
    assert plan.metadata["routing_mode"] == "mtcc"


@pytest.mark.asyncio
async def test_execute_plan(tacn_system):
    plan = await tacn_system.process_request("请对A区设备进行全面巡检并生成巡检报告")
    result = await tacn_system.execute_plan(plan)
    assert result is not None
    assert result.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.TIMEOUT)
    assert result.actual_latency_ms >= 0
    assert result.actual_cost >= 0


@pytest.mark.asyncio
async def test_multiple_intent_types(tacn_system):
    requests = [
        "实验楼烟雾传感器报警，请判断是否触发消防告警",
        "请对A区设备进行全面巡检并生成巡检报告",
        "多个摄像头检测到异常行为，请分析并通知安保人员",
    ]
    for req in requests:
        plan = await tacn_system.process_request(req)
        assert len(plan.subtask_graph.subtasks) > 0


@pytest.mark.asyncio
async def test_subtask_results_structure(tacn_system):
    plan = await tacn_system.process_request("设备运行状态异常，请进行诊断")
    result = await tacn_system.execute_plan(plan)
    assert isinstance(result.subtask_results, dict)
    for key, val in result.subtask_results.items():
        assert isinstance(key, str)
        assert isinstance(val, dict)
        assert "agent_id" in val
        assert "success" in val
