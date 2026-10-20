"""
Módulo de carga y configuración de subagentes SQF para Google Antigravity SDK.

Etapa 2 (R1): Carga programática de subagentes desde archivos Markdown con frontmatter YAML.
Construcción de configuraciones Pydantic puras (SubagentConfig y LocalAgentConfig)
sin instanciación del runtime de Agent y sin requerir credenciales ni llamadas a red.
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Any, Optional

import yaml
try:
    from google.antigravity import LocalAgentConfig, types
except ImportError:
    LocalAgentConfig = None  # type: ignore
    types = None  # type: ignore

logger = logging.getLogger(__name__)

# Los subagentes de este plugin viven en <plugin>/agents, no en el directorio global
# de agentes de la maquina. La ruta se deriva del propio archivo.
def _resolve_default_agents_dir() -> Path:
    curr = Path(__file__).resolve().parent
    for p in [curr] + list(curr.parents):
        cand = p / "agents"
        if cand.is_dir() and any(cand.glob("sqf-*.md")):
            return cand
    return Path(__file__).resolve().parent.parent.parent.parent / "agents"


DEFAULT_AGENTS_DIR = _resolve_default_agents_dir()

# Campos presentes en la especificación/frontmatter pero NO CONFIRMADOS en el SDK
# Campos del frontmatter que el SDK no expone y que por tanto se descartan con aviso.
NO_CONFIRMADO_FIELDS: list[str] = [
    "mode",
    "role",
    "instructions",
    "commandExecutionPolicy",
    "subagent",
    "mainAgent",
]

# Campos que ademas se deben volcar a un log para que la diferencia entre lo que
# declara el .md y lo que construye el SDK sea visible, no silenciosa.
REPORTAR_EN_LOG: list[str] = [
    "commandExecutionPolicy",
    "subagent",
    "mainAgent",
]
PROJECT_MODES = ["Micro", "Estándar", "Completo"]

def parse_agent_markdown(content: str, filename: str) -> tuple[dict[str, Any], str]:
    if not content or not content.strip():
        raise ValueError(f"El archivo '{filename}' está vacío o solo contiene espacios.")

    pattern = r"^---\s*\r?\n(.*?)\r?\n---\s*\r?\n?(.*)$"
    match = re.match(pattern, content, re.DOTALL)
    if not match:
        raise ValueError(
            f"El archivo '{filename}' no contiene un encabezado YAML frontmatter válido delimitado por '---'."
        )

    fm_raw = match.group(1)
    body = match.group(2).strip()

    try:
        fm = yaml.safe_load(fm_raw)
    except yaml.YAMLError as exc:
        raise ValueError(f"Error de sintaxis YAML en frontmatter de '{filename}': {exc}") from exc

    if not isinstance(fm, dict):
        raise ValueError(
            f"El frontmatter de '{filename}' no es un diccionario YAML válido (obtenido: {type(fm).__name__})."
        )

    return fm, body


def load_sqf_subagents(
    agents_dir: Optional[Path | str] = None,
    expected_count: int = 10,
    mode: Optional[str] = None,
) -> list[types.SubagentConfig]:
    target_dir = Path(agents_dir) if agents_dir is not None else DEFAULT_AGENTS_DIR

    if not target_dir.exists():
        raise FileNotFoundError(f"El directorio de agentes no existe: '{target_dir}'")
    if not target_dir.is_dir():
        raise NotADirectoryError(f"La ruta especificada no es un directorio: '{target_dir}'")

    if mode is not None:
        if mode in PROJECT_MODES:
            logger.info("Modo de orquestación SQF: %s (triage de flujo)", mode)
        else:
            logger.warning("Modo no estándar recibido ('%s') - NO CONFIRMADO en SDK", mode)

    if types is None:
        logger.warning("SDK google-antigravity no instalado en el entorno: NO VERIFICADO")
        raise RuntimeError("google-antigravity no está instalado en este entorno (NO VERIFICADO)")

    # Filtrado estricto: únicamente archivos sqf-*.md, excluyendo py-*.md y otros
    sqf_files = sorted([
        f for f in target_dir.iterdir()
        if f.is_file() and f.name.startswith("sqf-") and f.name.endswith(".md")
    ])

    if len(sqf_files) != expected_count:
        raise ValueError(
            f"Se esperaban {expected_count} agentes sqf-*.md en '{target_dir}', "
            f"pero se encontraron {len(sqf_files)}."
        )

    subagents: list[types.SubagentConfig] = []
    seen_names: set[str] = set()

    for file_path in sqf_files:
        # Lectura estricta de solo lectura
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        fm, body = parse_agent_markdown(content, filename=file_path.name)

        name = fm.get("name")
        if not name or not isinstance(name, str):
            raise ValueError(f"El archivo '{file_path.name}' no define un campo 'name' válido.")

        if not name.startswith("sqf-"):
            raise ValueError(f"El campo 'name' ('{name}') en '{file_path.name}' debe comenzar con 'sqf-'.")

        if name != file_path.stem:
            raise ValueError(f"El campo 'name' ('{name}') no coincide con el stem '{file_path.stem}'.")

        if name in seen_names:
            raise ValueError(f"Nombre duplicado: '{name}'.")
        seen_names.add(name)

        for unconfirmed in NO_CONFIRMADO_FIELDS:
            if unconfirmed in fm:
                nivel = logging.WARNING if unconfirmed in REPORTAR_EN_LOG else logging.INFO
                logger.log(
                    nivel,
                    "Campo '%s' = %s en '%s'. %s",
                    unconfirmed,
                    fm[unconfirmed],
                    file_path.name,
                    "El SDK no lo expone: la config construida puede no equivaler a la que "
                    "Antigravity aplica." if unconfirmed in REPORTAR_EN_LOG
                    else "NO CONFIRMADO en SDK.",
                )

        description = str(fm.get("description", ""))
        raw_tools = fm.get("tools")
        tools: list[Any] = raw_tools if isinstance(raw_tools, list) else []

        raw_model = fm.get("model")
        model: Optional[str] = raw_model if isinstance(raw_model, str) else None

        subagent_config = types.SubagentConfig(
            name=name,
            description=description,
            system_instructions=body,
            tools=tools,
            model=model,
            capabilities=types.SubagentCapabilities(),
        )
        subagents.append(subagent_config)

    return subagents


def build_orchestrator_config(
    subagents: list[types.SubagentConfig],
    workspaces: Optional[list[str]] = None,
) -> LocalAgentConfig:
    if not subagents:
        raise ValueError("La lista de subagentes no puede estar vacía.")

    allowed_subagents: list[str] = []
    seen: set[str] = set()

    for s in subagents:
        if not s.name or not s.name.startswith("sqf-"):
            raise ValueError(f"Subagente no permitido: '{getattr(s, 'name', None)}'")
        if s.name in seen:
            raise ValueError(f"Subagente duplicado: '{s.name}'.")
        seen.add(s.name)
        allowed_subagents.append(s.name)

    capabilities = types.CapabilitiesConfig(
        enable_subagents=True,
        allowed_subagents=allowed_subagents,
    )

    kwargs: dict[str, Any] = {
        "subagents": subagents,
        "capabilities": capabilities,
    }
    if workspaces is not None:
        kwargs["workspaces"] = workspaces

    return LocalAgentConfig(**kwargs)
