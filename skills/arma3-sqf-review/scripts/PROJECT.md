# Project: Arma 3 SQF Antigravity Orchestrator

## Architecture
- **Language & Environment**: Python 3.10+ (compatible con Python 3.14).
- **Core SDK**: `google-antigravity` (`LocalAgentConfig`, `SubagentConfig`, `CapabilitiesConfig`).
- **Subagent Configuration Module**: `sqf_agent_loader.py` carga y valida las declaraciones `sqf-*.md` del propio plugin (`<plugin>/agents`), construyendo configuraciones Pydantic puras sin instanciación del runtime ni credenciales.
- **Orchestration Engine**: `sqf_orchestrator.py` provee `run_orchestrator(...)` con inyección de dependencias para archivo de estado, ejecutable de linter, función de agente y directorio de trabajo. Requiere un agente real o `--dry-run` (código de salida 10).
- **SQF Models & Linting**: `sqf_models.py` modela hallazgos (`SQFFinding`), preserva advertencias en rc=0, clasifica advertencias de scope como `BLOQUEANTE` y evalúa escalado por primitivas de red y scheduler. `run_sqflint.py` normaliza la salida y sale con código 3 ante directorios sin `.sqf`. `fake_linter.py` proporciona simulación determinista (rc=0, 1, 2, 3).
- **Execution Boundaries**: Los archivos temporales `.sqf` e informes de auditoría se generan dentro del directorio de trabajo configurado sin modificar archivos fuera del workspace.

## Feature Inventory
| # | Feature | Description | Milestone | Status |
|---|---------|-------------|-----------|--------|
| 1 | Linter Output Parser & Scope Blocker | `sqf_models.py:parse_sqflint_output` parsea rc=0 sin descartar warnings; mapea advertencias de scope a `BLOQUEANTE` | Onda 0/1 | DONE |
| 2 | Unified Escalation Heuristics | `check_escalation_needed` y `check_escalation_needed_for_files` unifican criterios con `SKILL.md` | Onda 0/1 | DONE |
| 3 | Linter Empty Dir Handling | `run_sqflint.py` retorna código 3 ante directorios sin archivos `.sqf` | Onda 0/1 | DONE |
| 4 | Linter Output Normalization | `run_sqflint.py` normaliza todas las líneas a `archivo:línea: nivel: mensaje` | Onda 0/1 | DONE |
| 5 | Orchestrator Agent Requirement | `sqf_orchestrator.py` exige `agent_func` real; `--dry-run` retorna código 10 `NO VERIFICADO` | Onda 0/1 | DONE |
| 6 | Orchestrator Existing Code Support | CLI expone `--input`, `--root` y `--dry-run`, leyendo inventario real del proyecto | Onda 0/1 | DONE |
| 7 | Plugin-relative Paths | Derivación de rutas por defecto desde el propio archivo en loader y orchestrator | Onda 0/1 | DONE |
| 8 | Subagent Frontmatter Logging | `sqf_agent_loader.py` registra campos no expuestos en log con nivel `WARNING` para campos críticos | Onda 0/1 | DONE |
| 9 | Distributed Test Harness | Paquete incluye `tests/**` (11 tests) y `scripts/fake_linter.py` para verificación determinista | Onda 0/1 | DONE |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Parser de Linter y Modelos | `sqf_models.py`, `run_sqflint.py` | none | DONE |
| M2 | Loader de Subagentes | `sqf_agent_loader.py` | M1 | DONE |
| M3 | Orquestador y CLI | `sqf_orchestrator.py` | M1, M2 | DONE |
| M4 | Arnés de Pruebas y Verificación | `tests/**`, `fake_linter.py` | M1, M2, M3 | DONE |

## Interface Contracts
### `sqf_models.py`
- `parse_sqflint_output(rc: int, stdout: str) -> list[SQFFinding]`
  - Preserva advertencias independientemente del `rc`.
  - Mapea advertencias de variable no privada / scope a `BLOQUEANTE`.
- `check_escalation_needed(code: str, current_mode: str) -> str`
- `check_escalation_needed_for_files(files: list[Path | str], current_mode: str) -> str`

### `sqf_agent_loader.py`
- `load_sqf_subagents(agents_dir: Optional[Path | str] = None, expected_count: int = 10, mode: Optional[str] = None) -> list[types.SubagentConfig]`
- `build_orchestrator_config(subagents: list[types.SubagentConfig], workspaces: Optional[list[str]] = None) -> LocalAgentConfig`

### `sqf_orchestrator.py`
- `run_orchestrator(...) -> int`:
  - Retorna 0 (éxito), 1 (aborto T09 con bloqueante), 10 (NO VERIFICADO).
