"""Conector autónomo de consulta offline a la base de conocimiento BIKI (a3ref).

Proporciona resolución determinista en dos pasos para comandos y funciones SQF,
caché en proceso de alta velocidad para linters y subagentes, y utilidades CLI.
"""

from __future__ import annotations

import argparse
import copy
import gc
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

# ==============================================================================
# RESOLUCIÓN DE RUTA E IMPORTACIÓN DE MÓDULOS (D10):
# Este módulo reside en 'skills/arma3-sqf-review/scripts/'. Cuando es ejecutado
# como script o importado desde la raíz del plugin, subdirectorios o arnés de
# pruebas, asegura la inclusión de su directorio contenedor en 'sys.path' para
# permitir la resolución directa de sus módulos hermanos.
# ==============================================================================
_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))


def _discover_default_wiki_path() -> Path:
    """Descubre dinámicamente la ubicación de los datos de la wiki por proximidad o estándar de usuario."""
    plugin_root = _SCRIPT_DIR.parents[2]
    candidates = [
        plugin_root.parent / "Wiki" / "data",
        plugin_root.parent / "wiki" / "data",
        plugin_root / "data",
        Path.home() / ".a3ref" / "data",
        Path.home() / ".gemini" / "wiki" / "data",
    ]
    for candidate in candidates:
        if candidate.is_dir() and (candidate / "syntax.json").exists():
            return candidate
    return plugin_root / "data"


DEFAULT_WIKI_PATH = _discover_default_wiki_path()

# Cachés indexadas por ruta canónica resuelta (D3)
_syntax_caches: dict[str, dict[str, Any]] = {}
_index_caches: dict[str, dict[str, Any]] = {}
_index_by_lower_caches: dict[str, dict[str, list[dict[str, Any]]]] = {}
_commands_caches: dict[str, dict[str, dict[str, Any]]] = {}
_functions_caches: dict[str, dict[str, dict[str, Any]]] = {}


def clear_caches() -> None:
    """Limpia todas las cachés en memoria del conector."""
    _syntax_caches.clear()
    _index_caches.clear()
    _index_by_lower_caches.clear()
    _commands_caches.clear()
    _functions_caches.clear()


def resolve_wiki_root(override_path: str | Path | None = None) -> Path:
    """Resuelve la ruta a los datos de la wiki por jerarquía estricta (D6):

    1. override_path explícito si se provee.
    2. Variable de entorno A3REF_WIKI_PATH si está definida. Si la ruta especificada
       en la variable de entorno no existe en disco, se retorna directamente
       (sin caer en silencio al valor por defecto) para que las operaciones subsecuentes
       reporten un estado NO VERIFICADO explícito.
    3. Ruta local por defecto (DEFAULT_WIKI_PATH descubierta dinámicamente).
    """
    if override_path:
        return Path(override_path)
    env_path = os.environ.get("A3REF_WIKI_PATH")
    if env_path is not None:
        return Path(env_path)
    return _discover_default_wiki_path()


def get_data_git_sha(data_dir: Path | None = None) -> str:
    """Obtiene en tiempo de ejecución el commit SHA de la réplica offline data."""
    target_dir = resolve_wiki_root(data_dir)
    if not target_dir.exists():
        return f"NO_VERIFICADO (directorio no existe: {target_dir})"
    try:
        res = subprocess.run(
            ["git", "-C", str(target_dir), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip()
    except (subprocess.SubprocessError, OSError):
        pass
    return "NO_VERIFICADO"


def get_dataset_updated_timestamp(data_dir: Path | None = None) -> str:
    """Obtiene el valor de la clave 'updated' de syntax.json."""
    syn = load_syntax(data_dir)
    if syn and "updated" in syn:
        return str(syn["updated"])
    return "NO_VERIFICADO"


def _cache_key(root: Path) -> str:
    return str(root)


def load_syntax(data_dir: Path | None = None) -> dict[str, Any]:
    """Carga syntax.json con caché en memoria indexada por ruta resuelta (D3)."""
    root = resolve_wiki_root(data_dir)
    key = _cache_key(root)
    if key in _syntax_caches:
        return _syntax_caches[key]

    target = root / "syntax.json"
    if not target.exists():
        _syntax_caches[key] = {}
        return {}
    with open(target, "r", encoding="utf-8") as f:
        data = json.load(f)
    _syntax_caches[key] = data
    return data


def load_index(data_dir: Path | None = None) -> dict[str, Any]:
    """Carga index.json en memoria y construye el índice por nombre en minúsculas (D3)."""
    root = resolve_wiki_root(data_dir)
    key = _cache_key(root)
    if key in _index_caches:
        return _index_caches[key]

    target = root / "index.json"
    if not target.exists():
        _index_caches[key] = {}
        _index_by_lower_caches[key] = {}
        return {}
    with open(target, "r", encoding="utf-8") as f:
        data = json.load(f)
    by_lower: dict[str, list[dict[str, Any]]] = {}
    items = data.get("items", []) if isinstance(data, dict) else data
    for item in items:
        name_lower = str(item.get("name", "")).lower()
        by_lower.setdefault(name_lower, []).append(item)
    _index_caches[key] = data
    _index_by_lower_caches[key] = by_lower
    return data


def _ensure_commands_loaded(data_dir: Path | None = None) -> dict[str, dict[str, Any]]:
    """Carga commands.json en caché por nombre en minúsculas (D3, D5)."""
    root = resolve_wiki_root(data_dir)
    key = _cache_key(root)
    if key in _commands_caches:
        return _commands_caches[key]

    target = root / "commands.json"
    cmd_map: dict[str, dict[str, Any]] = {}
    if not target.exists():
        _commands_caches[key] = cmd_map
        return cmd_map
    with open(target, "r", encoding="utf-8") as f:
        raw = json.load(f)
    items = raw.get("items", []) if isinstance(raw, dict) else raw
    for it in items:
        name = it.get("name", "")
        name_lower = name.lower()
        status = it.get("status", "ok")
        version = it.get("arma3_since") or it.get("since") or "versión no disponible en el snapshot"
        url = it.get("url") or f"https://community.bistudio.com/wiki/{name} (NO_VERIFICADO: url ausente en snapshot)"
        locality = it.get("locality", {})
        enriched = dict(it)
        enriched["canonical_name"] = name
        enriched["status"] = status
        enriched["version"] = version
        enriched["url"] = url
        enriched["locality"] = locality
        cmd_map[name_lower] = enriched
    _commands_caches[key] = cmd_map
    return cmd_map


def _ensure_functions_loaded(data_dir: Path | None = None) -> dict[str, dict[str, Any]]:
    """Carga functions.json en caché por nombre en minúsculas (D3, D5)."""
    root = resolve_wiki_root(data_dir)
    key = _cache_key(root)
    if key in _functions_caches:
        return _functions_caches[key]

    target = root / "functions.json"
    fn_map: dict[str, dict[str, Any]] = {}
    if not target.exists():
        _functions_caches[key] = fn_map
        return fn_map
    with open(target, "r", encoding="utf-8") as f:
        raw = json.load(f)
    items = raw.get("items", []) if isinstance(raw, dict) else raw
    for it in items:
        name = it.get("name", "")
        name_lower = name.lower()
        status = it.get("status", "ok")
        version = it.get("arma3_since") or it.get("since") or "versión no disponible en el snapshot"
        url = it.get("url") or f"https://community.bistudio.com/wiki/{name} (NO_VERIFICADO: url ausente en snapshot)"
        enriched = dict(it)
        enriched["canonical_name"] = name
        enriched["status"] = status
        enriched["version"] = version
        enriched["url"] = url
        fn_map[name_lower] = enriched
    _functions_caches[key] = fn_map
    return fn_map


def lookup_syntax_symbol(token: str, data_dir: Path | None = None) -> dict[str, Any] | None:
    """Resolución en dos pasos con desempate por tipo (command > topic, function > topic) y URL oficial (D5).

    Retorna un diccionario con canonical_name, status, version, replaced_by, url y type,
    o None si el símbolo no existe como comando o función oficial.
    """
    if not token or not token.strip():
        return None
    t_lower = token.strip().lower()

    # Paso 1: Comprobar presencia en syntax.json
    syn = load_syntax(data_dir)
    if not syn:
        return None
    syn_cmd = syn.get("commands", {}).get(t_lower)
    syn_fn = syn.get("functions", {}).get(t_lower)
    if not syn_cmd and not syn_fn:
        return None

    syn_data = syn_cmd or syn_fn

    # Paso 2: Desempate y grafía canónica desde index.json
    root = resolve_wiki_root(data_dir)
    key = _cache_key(root)
    idx = load_index(data_dir)
    if not idx:
        return None
    candidates = _index_by_lower_caches.get(key, {}).get(t_lower, [])
    if not candidates:
        items = idx.get("items", []) if isinstance(idx, dict) else idx
        for it in items:
            if str(it.get("name", "")).lower() == t_lower:
                candidates.append(it)

    # Desempate priorizando type matching
    chosen = None
    if syn_cmd:
        for c in candidates:
            if c.get("type") == "command":
                chosen = c
                break
    if not chosen and syn_fn:
        for c in candidates:
            if c.get("type") == "function":
                chosen = c
                break
    if not chosen:
        for c in candidates:
            if c.get("type") in ("command", "function"):
                chosen = c
                break

    canonical_name = chosen.get("name") if chosen else syn_data.get("name", token.strip())
    status = syn_data.get("status") or (chosen.get("status") if chosen else "ok")
    replaced_by = syn_data.get("replaced_by") or (chosen.get("replaced_by") if chosen else None)
    version = (chosen.get("arma3_since") or chosen.get("since")) if chosen else None
    version_str = version if version else "versión no disponible en el snapshot"
    item_type = chosen.get("type") if chosen else ("command" if syn_cmd else "function")

    # Tomar la URL oficial del registro oficial de commands o functions (D5)
    rec = get_command(canonical_name, data_dir) if syn_cmd else get_function(canonical_name, data_dir)
    if not rec:
        rec = get_command(canonical_name, data_dir) or get_function(canonical_name, data_dir)

    if rec and rec.get("url"):
        url = rec["url"]
    elif chosen and chosen.get("url"):
        url = chosen["url"]
    elif syn_data and syn_data.get("url"):
        url = syn_data["url"]
    else:
        url = f"https://community.bistudio.com/wiki/{canonical_name} (NO_VERIFICADO: url ausente en snapshot)"

    return {
        "canonical_name": canonical_name,
        "status": status,
        "version": version_str,
        "replaced_by": replaced_by,
        "url": url,
        "type": item_type,
    }


def get_command(name: str, data_dir: Path | None = None) -> dict[str, Any] | None:
    """Consulta detallada en commands.json."""
    if not name or not name.strip():
        return None
    cache = _ensure_commands_loaded(data_dir)
    return cache.get(name.strip().lower())


def get_function(name: str, data_dir: Path | None = None) -> dict[str, Any] | None:
    """Consulta detallada en functions.json."""
    if not name or not name.strip():
        return None
    cache = _ensure_functions_loaded(data_dir)
    return cache.get(name.strip().lower())


def get_topic(title: str, data_dir: Path | None = None) -> dict[str, Any] | None:
    """Lectura puntual bajo demanda de topics.json, liberando inmediatamente la memoria (D9)."""
    if not title or not title.strip():
        return None
    root = resolve_wiki_root(data_dir)
    target = root / "topics.json"
    if not target.exists():
        return None
    target_low = title.strip().lower()
    with open(target, "r", encoding="utf-8") as f:
        raw = json.load(f)
    items = raw.get("items", []) if isinstance(raw, dict) else raw
    match = None
    for it in items:
        t_name = str(it.get("title") or it.get("name") or "").lower()
        if t_name == target_low:
            match = copy.deepcopy(it)
            break
    del raw, items
    gc.collect()
    return match


def update_wiki(data_dir: Path | None = None) -> tuple[bool, str]:
    """Sincronización git pull secuencial con timeout de 30s, verificación de repositorio limpio

    y captura explícita de excepciones (D4). Orden estricto: primero data_dir y luego raíz.
    """
    root = resolve_wiki_root(data_dir)
    if not root.exists():
        return False, f"NO_VERIFICADO: Directorio de datos no existe: {root}"

    repos_to_sync = [root, root.parent]
    messages = []
    for r in repos_to_sync:
        git_dir = r / ".git"
        if not git_dir.exists() and not (r.parent / ".git").exists():
            return False, f"Directorio {r.name} no contiene repositorio git (.git ausente)."

        try:
            res_stat = subprocess.run(
                ["git", "-C", str(r), "status", "--porcelain"],
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )
            if res_stat.returncode != 0:
                return False, f"Error al verificar estado de git en {r.name}: {res_stat.stderr.strip()}"
            if res_stat.stdout.strip():
                return False, f"Repositorio sucio en {r.name}; contiene cambios no confirmados."

            res_pull = subprocess.run(
                ["git", "-C", str(r), "pull", "--ff-only"],
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )
            if res_pull.returncode != 0:
                return False, f"Error en git pull en {r.name}: {res_pull.stderr.strip()}"
            messages.append(f"{r.name}: {res_pull.stdout.strip()}")
        except FileNotFoundError:
            return False, "Comando 'git' no encontrado en el sistema; control de versiones no disponible."
        except subprocess.TimeoutExpired:
            return False, f"Tiempo de espera agotado (30s) al sincronizar repositorio {r.name}."
        except (subprocess.SubprocessError, OSError) as e:
            return False, f"Excepción al ejecutar git en {r.name}: {e}"

    return True, " | ".join(messages)


def main():
    parser = argparse.ArgumentParser(description="Lector autónomo de la base de conocimiento BIKI (a3ref)")
    parser.add_argument("--command", type=str, default=None, help="Consultar información completa de un comando")
    parser.add_argument("--function", type=str, default=None, help="Consultar información completa de una función")
    parser.add_argument("--topic", type=str, default=None, help="Consultar un tópico de la wiki")
    parser.add_argument("--lookup", type=str, default=None, help="Búsqueda sintáctica en 2 pasos de un símbolo")
    parser.add_argument("--wiki-path", type=str, default=None, help="Ruta personalizada a la carpeta data")
    parser.add_argument("--update-wiki", "--update", action="store_true", help="Actualizar repositorios git")
    parser.add_argument("--sha", action="store_true", help="Mostrar commit SHA de la réplica data")

    args = parser.parse_args()
    data_path = resolve_wiki_root(args.wiki_path)

    if args.sha:
        print(get_data_git_sha(data_path))
        sys.exit(0)

    if args.update_wiki:
        ok, msg = update_wiki(data_path)
        if ok:
            print(msg)
            sys.exit(0)
        else:
            print(f"Error al sincronizar wiki: {msg}", file=sys.stderr)
            sys.exit(1)

    if args.command:
        info = get_command(args.command, data_path)
        if info:
            print(json.dumps(info, indent=2, ensure_ascii=False))
            sys.exit(0)
        else:
            print(f"Comando no encontrado: {args.command}", file=sys.stderr)
            sys.exit(1)

    if args.function:
        info = get_function(args.function, data_path)
        if info:
            print(json.dumps(info, indent=2, ensure_ascii=False))
            sys.exit(0)
        else:
            print(f"Función no encontrada: {args.function}", file=sys.stderr)
            sys.exit(1)

    if args.topic:
        info = get_topic(args.topic, data_path)
        if info:
            print(json.dumps(info, indent=2, ensure_ascii=False))
            sys.exit(0)
        else:
            print(f"Tópico no encontrado: {args.topic}", file=sys.stderr)
            sys.exit(1)

    if args.lookup:
        info = lookup_syntax_symbol(args.lookup, data_path)
        if info:
            print(json.dumps(info, indent=2, ensure_ascii=False))
            sys.exit(0)
        else:
            print(f"Símbolo no identificado: {args.lookup}", file=sys.stderr)
            sys.exit(1)

    parser.print_help()


if __name__ == "__main__":
    main()
