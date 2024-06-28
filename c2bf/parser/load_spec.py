import json

from pathlib import Path

def load_spec(spec_path: str | Path):
    if not str(spec_path).endswith(".json"):
        spec_path = str(spec_path) + ".json"
    spec = json.load(open(spec_path, "r"))
    if "include" not in spec:
        return spec
    
    include = spec["include"]
    if isinstance(include, str):
        include = [include]

    del spec["include"]
    for inc in include:
        inc_spec = load_spec(Path(spec_path).parent.joinpath(inc))
        if common_keys := set(spec.keys()) & set(inc_spec.keys()):
            raise Exception(f"Duplicate keys in spec: {common_keys}")
        spec.update(inc_spec)
    
    return spec
