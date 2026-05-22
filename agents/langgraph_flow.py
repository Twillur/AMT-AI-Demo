"""
LangGraph orchestration layer — routes queries to the correct department agent
and collects the full tool trace.
LangSmith @traceable decorators capture each run in the tracing dashboard.
"""
from typing import TypedDict, Annotated
import operator
from langgraph.graph import StateGraph, END
from . import trace

try:
    from langsmith import traceable as _traceable
except ImportError:
    def _traceable(**kwargs):
        return lambda fn: fn


class AgentState(TypedDict):
    department: str
    message: str
    history: list
    response: str
    tools_used: Annotated[list, operator.add]


def _run_department_agent(state: AgentState) -> dict:
    from . import sales, distribution, finance, service
    dept_map = {
        "sales": sales,
        "distribution": distribution,
        "finance": finance,
        "service": service,
    }
    dept = state["department"]
    agent_mod = dept_map[dept]

    trace.log("department_router", "LangGraph", f"→ {dept.capitalize()} Agent")
    response = agent_mod.run(state["message"], state["history"])
    trace.log("llm_response", "GPT-4o", "Response generated")

    return {"response": response, "tools_used": trace.get()}


_builder = StateGraph(AgentState)
_builder.add_node("department_agent", _run_department_agent)
_builder.set_entry_point("department_agent")
_builder.add_edge("department_agent", END)

_graph = _builder.compile()


@_traceable(name="AMT-Agent-Run", run_type="chain")
def run(department: str, message: str, history: list) -> tuple:
    trace.start()
    trace.log("graph_entry", "LangGraph", "Graph invoked — routing request")

    result = _graph.invoke({
        "department": department,
        "message": message,
        "history": history,
        "response": "",
        "tools_used": [],
    })

    return result["response"], trace.get()
