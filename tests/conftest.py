import sys
from pathlib import Path

plugin_root = Path(__file__).resolve().parent.parent
scripts_dir = plugin_root / "skills" / "arma3-sqf-review" / "scripts"
references_dir = plugin_root / "skills" / "arma3-sqf-review" / "references"

for d in [plugin_root, scripts_dir, references_dir]:
    sd = str(d)
    if sd not in sys.path:
        sys.path.insert(0, sd)
