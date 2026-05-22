import threading
_local = threading.local()

def start():
    _local.trace = []

def log(tool_name: str, framework: str, label: str):
    if not hasattr(_local, 'trace'):
        _local.trace = []
    _local.trace.append({"tool": tool_name, "framework": framework, "label": label})

def get() -> list:
    return list(getattr(_local, 'trace', []))
