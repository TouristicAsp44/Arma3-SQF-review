# Project: Arma 3 SQF Antigravity Orchestrator (Etapas 2 y 3)

## Architecture
- **Language & Environment**: Python 3.14.4 within virtual environment `venv/`.
- **Core SDK**: `google-antigravity 0.1.20` (`LocalAgentConfig`, `SubagentConfig`, `CapabilitiesConfig`).
- **Subagent Configuration Module**: Loads and validates `sqf-*.md` subagent declarations, constructs pure Pydantic configurations without network/credentials.
- **Orchestration Engine**: `sqf_orchestrator.py` provides `run_orchestrator(...)` with full dependency injection for state file, linter executable, and simulated agent chat function.
- **SQF Models & Linting**: `sqf_models.py` models SQF findings and parses linter outputs. `run_sqflint.py` is the production linter; `fake_linter.py` provides deterministic mock responses (rc=0, 1, 2, 3).
- **Execution Boundaries**: All temporary `.sqf` files and state artifacts remain exclusively inside `C:\Users\Touri\Documents\EDEN EDITOR\Skills Antigravity`. Zero modifications outside this folder.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | R3.1 SQFLINT Parser Fix | Fix `sqf_models.py:parse_sqflint_output` so rc=1 with unrecognized output becomes generic BLOQUEANTE | M1 | ORIGINAL_REQUEST §R3 |
| 2 | R3.2 Test Linter (`fake_linter.py`) | Create `fake_linter.py` mimicking `run_sqflint.py` output format with rc=0, 1 (syntax + unrecognized), 2, 3 | M1 | ORIGINAL_REQUEST §R3 |
| 3 | R3.3 Pinned Dependencies (`requirements.txt`) | Install `PyYAML==6.0.3` in venv (approved exception) and generate `requirements.txt` with exact 53+1 pinned versions | M1 | ORIGINAL_REQUEST §R3 |
| 4 | R1.1 Subagent File Loading & Count Validation | Load exactly expected count (default 10) of `sqf-*.md` files from injectable path; raise ValueError on mismatch | M2 | ORIGINAL_REQUEST §R1 |
| 5 | R1.2 Filter `sqf-*.md` vs `py-*.md` | Strictly ignore `py-*.md` files and ensure only `sqf-*.md` files are loaded | M2 | ORIGINAL_REQUEST §R1 |
| 6 | R1.3 Frontmatter Validation | Validate YAML `name` starts with `sqf-` and matches filename stem exactly | M2 | ORIGINAL_REQUEST §R1 |
| 7 | R1.4 Read-only Offline Config Construction | Construct `LocalAgentConfig` and `SubagentConfig` with `allowed_subagents` restricted to `sqf-*`; no Agent instantiation | M2 | ORIGINAL_REQUEST §R1 |
| 8 | R1.5 SDK Attributes & `NO CONFIRMADO` Documentation | Verify real fields of `SubagentConfig`; document `NO CONFIRMADO` for `mode`, `role`, `instructions`, `commandExecutionPolicy` | M2 | ORIGINAL_REQUEST §R1 |
| 9 | R2.1 Dependency Injection in Orchestrator | Refactor `sqf_orchestrator.py` with injectable `state_file`, `linter_executable`, `agent_func`, `work_dir` | M3 | ORIGINAL_REQUEST §R2 |
| 10 | R2.2 Orchestrator Loop & Iteration Limit | Maximum 3 iterations loop, state anchored to script folder | M3 | ORIGINAL_REQUEST §R2 |
| 11 | R2.3 Resume & Notes Archiving | `--continuar` requires existing state; read `notas_revision.txt`, append to agent prompt, archive to `archived_notes\` | M3 | ORIGINAL_REQUEST §R2 |
| 12 | R2.4 Temporary SQF File in Experimental Dir | Write SQF code to temporary `.sqf` strictly inside project root | M3 | ORIGINAL_REQUEST §R2 |
| 13 | R2.5 Default Linter Subprocess Execution | Run `run_sqflint.py` via `sys.executable` with `-B` and `PYTHONDONTWRITEBYTECODE=1` and timeout | M3 | ORIGINAL_REQUEST §R2 |
| 14 | R2.6 Network Escalation Trigger | `check_escalation_needed` escalates based on network primitives | M3 | ORIGINAL_REQUEST §R2 |
| 15 | R2.7 T09 Abort Logic | If iteration 3 fails with at least one `BLOQUEANTE` (pure or mixed), save `orchestrator_state.fallido.json` and exit 1 | M3 | ORIGINAL_REQUEST §R2 |
| 16 | R2.8 NO_VERIFICADO Clean Exit | If finished strictly with `NO_VERIFICADO` (zero `BLOQUEANTE`), exit with custom code 10 and "completado con NO VERIFICADO" | M3 | ORIGINAL_REQUEST §R2 |
| 17 | E2E & Integrity Verification | Run full `pytest -v` suite, verify pre/post file listings and SHA256 hashes, verify zero tampering | M4 | ORIGINAL_REQUEST §AC |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | SQFLINT Parser, fake_linter & Dependencies | Features 1, 2, 3 | none | DONE |
| M2 | SDK Subagent Configuration | Features 4, 5, 6, 7, 8 | M1 (PyYAML) | DONE |
| M3 | Python Orchestrator Bucle | Features 9, 10, 11, 12, 13, 14, 15, 16 | M1, M2 | DONE |
| M4 | Comprehensive Testing & Integrity Audit | Feature 17 (100% tests pass, pre/post integrity diff, audit report) | M1, M2, M3 | DONE |

## Interface Contracts
### `sqf_models.py`
- `parse_sqflint_output(rc: int, stdout: str) -> list[SQFFinding]`
  - `rc == 0`: returns empty list `[]`
  - `rc == 1`: parsed regex syntax errors as `BLOQUEANTE`; if no regex match, returns single `SQFFinding(severity="BLOQUEANTE", file="desconocido", line=0, description="Error de sintaxis o formato no reconocido del linter (rc=1)", evidence=stdout, discipline="Sintaxis")`
  - `rc == 2`: raises `ValueError(f"Error de uso de sqflint (rc=2): {stdout.strip()}")`
  - `rc == 3` or other: returns single `SQFFinding(severity="NO_VERIFICADO", file="desconocido", line=0, description=f"Fallo del linter o rc desconocido (rc={rc})", evidence=stdout, discipline="Sintaxis")`
- `check_escalation_needed(code: str) -> bool`:
  - Returns `True` if code contains network primitives outside comments/strings.

### `sqf_agent_loader.py` (or integrated in orchestrator)
- `load_sqf_subagents(agents_dir: Optional[Path | str] = None, expected_count: int = 10) -> list[types.SubagentConfig]`
  - Scans `agents_dir` for `sqf-*.md`
  - Validates count == `expected_count`, raises `ValueError` on mismatch
  - Ignores any `py-*.md`
  - Parses frontmatter, verifies `name` starts with `sqf-` and matches `file.stem`
  - Returns `list[SubagentConfig]`
- `build_orchestrator_config(subagents: list[types.SubagentConfig]) -> LocalAgentConfig`
  - Builds `LocalAgentConfig` with `subagents=subagents` and `CapabilitiesConfig(enable_subagents=True, allowed_subagents=[s.name for s in subagents])`

### `sqf_orchestrator.py`
- `run_orchestrator(state_file: str = "orchestrator_state.json", notes_file: str = "notas_revision.txt", archived_notes_dir: str = "archived_notes", linter_executable: Optional[str] = None, agent_func: Optional[Callable] = None, work_dir: Optional[str] = None, continuar: bool = False, max_iterations: int = 3) -> int`
  - Returns exit code: `0` (clean success), `1` (aborted on T09 limit with blocker), `10` (clean completed with NO_VERIFICADO).

## Code Layout
- `sqf_models.py`: Findings model, network escalation check, sqflint parser.
- `fake_linter.py`: Test linter returning rc=0, 1, 2, 3.
- `requirements.txt`: Pinned Python dependencies.
- `sqf_agent_loader.py` (or `sqf_agent_config.py`): Subagent loader and validator.
- `sqf_orchestrator.py`: Orchestrator main execution loop and CLI.
- `tests/` or root `test_*.py`:
  - `test_sqf_models.py`: Unit tests for models and escalation.
  - `test_parser_fixture.py`: Tests for real fixture parser.
  - `test_fake_linter.py` / `test_parser_fake_linter.py`: Tests for fake_linter and parser translation.
  - `test_sqf_agent_loader.py`: Tests for subagent loading, count validation, frontmatter validation, injectable path.
  - `test_orchestrator_loop.py`: Tests for orchestrator loop, T09 abort, exit code 10, notes archiving, prompt inclusion, `--continuar`.
