# Project: Arma 3 SQF Antigravity Orchestrator

## Architecture
- **Language & Environment**: Python 3.10+ (compatible con Python 3.14).
- **Core SDK**: `google-antigravity` (`LocalAgentConfig`, `SubagentConfig`, `CapabilitiesConfig`).
- **Execution Model (Opción C+)**: "El script es la puerta, la prosa es el flujo". `SKILL.md` invoca a `sqf_orchestrator.py` para calcular el modo (`--mode-query`) y obtener el informe clasificado de análisis estático (`--lint`). El flujo de corrección conversacional (máx. 3 iteraciones) vive en la prosa del agente Antigravity, pero juzga los bloqueantes producidos determinísticamente por el script.
- **Subagent Configuration Module**: `sqf_agent_loader.py` carga y valida las declaraciones `sqf-*.md` del propio plugin (`<plugin>/agents`), construyendo configuraciones Pydantic puras sin instanciación del runtime ni credenciales.
- **Orchestration Engine**: `sqf_orchestrator.py` provee los modos CLI `--mode-query`, `--lint`, `--mode <modo>` y el bucle programático `run_orchestrator(...)` con inyección de dependencias. Requiere un agente real o `--dry-run` (código de salida 10).
- **SQF Models & Linting**: `sqf_models.py` modela hallazgos (`SQFFinding`), normaliza severidades (`BLOQUEANTE` para errores y advertencias de scope), formatea reportes estables (`format_findings_report`, `summarize_escalation`), y evalúa escalado por primitivas de red y scheduler (`check_escalation_needed_for_files`, `determine_escalation_reason`).
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
| 9 | Distributed Test Harness | Paquete incluye `tests/**` (11 tests Onda 1 + 8 tests Onda 2) y `scripts/fake_linter.py` | Onda 0/1/2 | DONE |
| 10 | Mode Query CLI Wiring | `--mode-query` analiza el inventario de archivos con `check_escalation_needed_for_files` y emite reporte | Onda 2 | DONE |
| 11 | Classified Lint CLI Wiring | `--lint` ejecuta el linter y emite reporte determinista con severidades unificadas | Onda 2 | DONE |
| 12 | Explicit Mode Support | Parámetro `--mode` previene el re-escalado automático eliminando la doble autoridad | Onda 2 | DONE |
| 13 | Documented Wiring Invocations | `SKILL.md` y `agents/` invocan directamente las rutas completas del script orquestador | Onda 2 | DONE |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Parser de Linter y Modelos | `sqf_models.py`, `run_sqflint.py` | none | DONE |
| M2 | Loader de Subagentes | `sqf_agent_loader.py` | M1 | DONE |
| M3 | Orquestador y CLI | `sqf_orchestrator.py` | M1, M2 | DONE |
| M4 | Arnés de Pruebas y Verificación | `tests/**`, `fake_linter.py` | M1, M2, M3 | DONE |
| M5 | Cableado de Skill y Agentes (Onda 2) | `SKILL.md`, `agents/`, `--mode-query`, `--lint`, `test_wiring.py` | M1, M2, M3, M4 | DONE |

## Interface Contracts
### `sqf_models.py`
- `parse_sqflint_output(rc: int, stdout: str) -> list[SQFFinding]`
- `check_escalation_needed(code: str, current_mode: str) -> str`
- `check_escalation_needed_for_files(files: dict[str, str] | list[Any], current_mode: str) -> str`
- `determine_escalation_reason(files: dict[str, str] | list[Any], mode: str) -> str`
- `format_findings_report(findings: list[SQFFinding]) -> str`
- `summarize_escalation(mode: str, reason: str = "") -> str`

### `sqf_agent_loader.py`
- `load_sqf_subagents(agents_dir: Optional[Path | str] = None, expected_count: int = 10, mode: Optional[str] = None) -> list[types.SubagentConfig]`
- `build_orchestrator_config(subagents: list[types.SubagentConfig], workspaces: Optional[list[str]] = None) -> LocalAgentConfig`

### `sqf_orchestrator.py`
- `mode_query(root: Optional[str] = None) -> int`:
  - Retorna 0 (éxito con modo calculado), 1 (error de ruta).
- `run_lint(target: Optional[str] = None, linter_executable: Optional[str] = None, mode: Optional[str] = None, timeout: int = 30) -> int`:
  - Retorna 0 (análisis emitido con o sin hallazgos), 1 (error duro de ruta), 10 (linter no disponible / NO VERIFICADO).
- `run_orchestrator(...) -> int`:
  - Retorna 0 (éxito), 1 (aborto T09 con bloqueante), 10 (NO VERIFICADO).
