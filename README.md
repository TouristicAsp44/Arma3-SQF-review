# Arma 3 SQF Review Plugin

Plugin unificado para desarrollo, revisión arquitectónica, localidad multijugador, mejores prácticas y auditoría de calidad de scripts SQF en Arma 3.

## Componentes del Plugin

- **Skill**: `arma3-sqf-review` (`skills/arma3-sqf-review/SKILL.md`), proporciona los modos de operación Micro, Estándar y Completo, con triaje de criticidad y escalado dinámico.
- **Subagentes** (`agents/`): 10 agentes especializados (`sqf-architect`, `sqf-developer`, `sqf-static-analyzer`, `sqf-best-practices-reviewer`, `sqf-locality-auditor`, `sqf-performance-auditor`, `sqf-test-plan-generator`, `sqf-doc-writer`, `sqf-innovator`, `sqf-mission-config-auditor`).
- **Reglas del agente** (`rules/AGENTS.md`): Invariantes SQF/HPP obligatorias con trigger `always_on` (scope privado, evaluación perezosa, contexto scheduled/unscheduled, postura estricta de interfaz humana y honestidad técnica de verificación).
- **Referencias normativas** (`skills/arma3-sqf-review/references/`):
  - `sqf-standards.md`: Estándar SQF unificado del equipo (11 reglas de código, perfiles CBA/ACE3, checklist Micro).
  - `checklist-entrega.md`: Checklist integral de entrega de 9 bloques (A–I) para misiones y addons (`DESTINO: mision | addon`).
  - `wiki-cache.md`: Índice de referencia para verificación de comandos en la Biki oficial.
  - `run_sqflint.py`: Envoltorio CLI de análisis estático con normalización de salidas.
- **Herramientas y scripts** (`skills/arma3-sqf-review/scripts/`):
  - `sqf_orchestrator.py`: Motor de orquestación, bucle de desarrollo T09 y reporte.
  - `sqf_models.py`: Modelado de hallazgos SQF, normalización de severidades y heurísticas de escalado.
  - `sqf_agent_loader.py`: Carga y validación declarativa de subagentes del plugin.
  - `fake_linter.py`: Arnés de simulación determinista del linter para suites de pruebas.

## Uso del Linter

Para ejecutar el análisis estático sobre un archivo o directorio de scripts SQF:

```bash
python skills/arma3-sqf-review/references/run_sqflint.py <ruta_archivo_o_directorio>
```

Códigos de retorno del linter:
- `0`: Análisis finalizado sin errores (`SIN ERRORES`).
- `1`: Errores de sintaxis o comandos no reconocidos.
- `2`: Error en argumentos de invocación.
- `3`: Directorio vacío o sin archivos `.sqf`.

## Arnés de Pruebas

Para ejecutar la suite de pruebas unitarias y de integración:

```bash
python -m pytest tests/ -v
```
