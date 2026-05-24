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
    from .domain_router import classify

    dept_map = {
        "sales": sales,
        "distribution": distribution,
        "finance": finance,
        "service": service,
    }

    dept = state["department"]

    if dept == "auto":
        dept, confidence = classify(state["message"])
        trace.log("domain_classifier", "LangGraph", f"Classified → {dept.capitalize()} ({confidence}% confidence)")
    else:
        trace.log("department_router", "LangGraph", f"→ {dept.capitalize()} Agent")

    agent_mod = dept_map[dept]
    response = agent_mod.run(state["message"], state["history"])
    trace.log("llm_response", "GPT-4o", "Response generated")

    return {"response": response, "tools_used": trace.get(), "department": dept}


_builder = StateGraph(AgentState)
_builder.add_node("department_agent", _run_department_agent)
_builder.set_entry_point("department_agent")
_builder.add_edge("department_agent", END)

_graph = _builder.compile()


@_traceable(name="AMT-Agent-Run", run_type="chain")
def run(department: str, message: str, history: list) -> tuple:
    from .semantic_cache import check as cache_check, store as cache_store
    from .domain_router import classify

    trace.start()
    trace.log("graph_entry", "LangGraph", "Graph invoked — routing request")

    # Resolve actual department for cache key
    lookup_dept = department
    if department == "auto":
        lookup_dept, _ = classify(message)

    # Check semantic cache
    cached = cache_check(message, lookup_dept)
    if cached:
        trace.log("semantic_cache", "Cache", f"Hit ({cached['similarity']}% match) — 0 tokens spent")
        cache_entry = {"tool": "semantic_cache", "framework": "Cache",
                       "label": f"Hit ({cached['similarity']}% match) — 0 tokens spent"}
        original_tools = cached.get("tools", [])
        return cached["response"], [cache_entry] + original_tools, {"prompt": 0, "completion": 0, "total": 0}

    result = _graph.invoke({
        "department": department,
        "message": message,
        "history": history,
        "response": "",
        "tools_used": [],
    })

    tools  = trace.get()
    tokens = trace.get_tokens()
    cache_store(message, lookup_dept, result["response"], tools, tokens)

    return result["response"], tools, tokens
