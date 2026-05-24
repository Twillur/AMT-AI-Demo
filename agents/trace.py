import threading
_local = threading.local()

def start():
    _local.trace = []
    _local.tokens = {"prompt": 0, "completion": 0, "total": 0}

def log(tool_name: str, framework: str, label: str):
    if not hasattr(_local, 'trace'):
        _local.trace = []
    _local.trace.append({"tool": tool_name, "framework": framework, "label": label})

def add_tokens(usage):
    if not hasattr(_local, 'tokens'):
        _local.tokens = {"prompt": 0, "completion": 0, "total": 0}
    if usage:
        _local.tokens["prompt"]     += getattr(usage, "prompt_tokens", 0)
        _local.tokens["completion"] += getattr(usage, "completion_tokens", 0)
        _local.tokens["total"]      += getattr(usage, "total_tokens", 0)

def get() -> list:
    return list(getattr(_local, 'trace', []))

def get_tokens() -> dict:
    return dict(getattr(_local, 'tokens', {"prompt": 0, "completion": 0, "total": 0}))
