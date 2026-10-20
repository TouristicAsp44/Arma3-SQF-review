# Arma 3 SQF Review Plugin

Plugin unificado para desarrollo, revisión arquitectónica, localidad multijugador, mejores prácticas y auditoría de calidad de scripts SQF en Arma 3.

## Arquitectura de Ejecución (Opción C+)

El plugin implementa el modelo **"el script es la puerta, la prosa es el flujo"**:
- **La prosa (`SKILL.md`)** gobierna el flujo conversacional y el ciclo de corrección de hasta 3 iteraciones entre subagentes.
- **El script (`sqf_orchestrator.py`)** actúa como puerta de calidad determinista e inmutable para el cálculo del modo de proyecto y la clasificación de hallazgos del linter.

### Puntos de Invocación del Orquestador

#### 1. Consulta Determinista de Modo (`--mode-query`)
Calcula el modo de revisión (`Micro`, `Estándar`, `Completo`) analizando el inventario completo de archivos `.sqf` del proyecto:

```bash
python skills/arma3-sqf-review/scripts/sqf_orchestrator.py --root <raíz_del_proyecto> --mode-query
```

- Salida: Informe estructurado (`MODO: ...`, `MOTIVO: ...`, `RESUMEN: modo=...; escalado=...`).
- Códigos de salida:
  * `0`: Cálculo de modo exitoso.
  * `1`: Error de ruta o sintaxis de argumentos.
  * `10`: Ejecución completada con `NO VERIFICADO`.

#### 2. Análisis Estático Clasificado (`--lint`)
Ejecuta el linter sobre un archivo o directorio y emite el informe con severidad determinista unificada (convirtiendo advertencias de scope en `BLOQUEANTE`):

```bash
python skills/arma3-sqf-review/scripts/sqf_orchestrator.py --root <raíz_del_proyecto> --lint
```
*(o sobre un archivo individual: `python skills/arma3-sqf-review/scripts/sqf_orchestrator.py <archivo.sqf> --lint`).*

- Salida: Lista de hallazgos en formato `[SEVERIDAD] archivo:línea (disciplina): descripción` y `RESUMEN: bloqueantes=N; sugerencias=M; no_verificado=K`.
- Códigos de salida:
  * `0`: Análisis completado e informe producido (incluso cuando contiene hallazgos bloqueantes).
  * `1`: Error fatal de ruta o argumentos.
  * `10`: Linter no disponible (`SQFLINT_NO_DISPONIBLE` / `NO VERIFICADO`).

#### 3. Modo Explícito (`--mode`)
Permite forzar un modo determinado (`Micro`, `Estándar`, `Completo`) desactivando el re-escalado automático para respetar la decisión previa del flujo:

```bash
python skills/arma3-sqf-review/scripts/sqf_orchestrator.py --root <raíz> --mode Micro --lint
```

## Componentes del Plugin

- **Skill**: `arma3-sqf-review` (`skills/arma3-sqf-review/SKILL.md`), proporciona los modos de operación Micro, Estándar y Completo, con triaje de criticidad y escalado dinámico invocando al orquestador.
- **Subagentes** (`agents/`): 10 agentes especializados (`sqf-architect`, `sqf-developer`, `sqf-static-analyzer`, `sqf-best-practices-reviewer`, `sqf-locality-auditor`, `sqf-performance-auditor`, `sqf-test-plan-generator`, `sqf-doc-writer`, `sqf-innovator`, `sqf-mission-config-auditor`).
- **Reglas del agente** (`rules/AGENTS.md`): Invariantes SQF/HPP obligatorias con trigger `always_on` (scope privado, evaluación perezosa, contexto scheduled/unscheduled, postura estricta de interfaz humana y honestidad técnica de verificación).
- **Referencias normativas** (`skills/arma3-sqf-review/references/`):
  - `sqf-standards.md`: Estándar SQF canónico de escritura del equipo (11 reglas de código, perfiles CBA/ACE3, checklist Micro).
  - `checklist-entrega.md`: Checklist integral de criterios de verificación de 9 bloques (A–I) para misiones y addons (`DESTINO: mision | addon`).
  - `wiki-cache.md`: Índice de referencia para verificación de comandos en la Biki oficial.
  - `run_sqflint.py`: Envoltorio CLI multiplataforma con normalización de salidas.
- **Herramientas y scripts** (`skills/arma3-sqf-review/scripts/`):
  - `sqf_orchestrator.py`: Motor de orquestación, CLI con `--mode-query`, `--lint`, `--mode` y bucle T09.
  - `sqf_models.py`: Modelado de hallazgos SQF, normalización de severidades, reportes estructurados y heurísticas de escalado.
  - `sqf_agent_loader.py`: Carga y validación declarativa de subagentes del plugin.
  - `fake_linter.py`: Arnés de simulación determinista del linter para suites de pruebas.

## Arnés de Pruebas

Para ejecutar la suite de pruebas unitarias y de integración:

```bash
python -m pytest tests/ -v
```
