import javalang
from typing import List

def parse_java_methods(file_path: str) -> List[str]:
    """
    Return list of public method names in the first top-level type (class).
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            src = f.read()
        tree = javalang.parse.parse(src)
        types = [t for t in tree.types if hasattr(t, 'methods')]
        if not types:
            return []
        methods = []
        # take first top-level class/interface
        t0 = types[0]
        for m in getattr(t0, 'methods', []):
            modifiers = getattr(m, 'modifiers', set())
            if 'public' in modifiers:
                # include signature
                params = []
                for p in m.parameters:
                    params.append(f"{p.type.name} {p.name}")
                sig = f"{m.name}({', '.join(params)})"
                methods.append(sig)
        return methods
    except Exception as e:
        print("parse_java_methods error:", e)
        return []
