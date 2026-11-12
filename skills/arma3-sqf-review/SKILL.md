---
name: arma3-sqf-review
description: >-
  Equipo de subagentes para desarrollar y revisar código SQF de Arma 3 con estándares altos: diseño, implementación por módulos, verificación en wiki, sqflint, best-practices, locality/JIP, plan de prueba y guía de uso. Activar para scripts o sistemas nuevos, cambios de remoteExec/publicVariable/JIP/HC, auditoría de código existente o al pedir documentar un script. Escala solo (modo Micro/Estándar/Completo). No usar para typos, ajustar un valor, preguntas conceptuales. No usar para código Python ni otros lenguajes.
---

# Equipo SQF — orquestación

El agente principal es el **orquestador**: único que decide, integra y entrega. Los subagentes trabajan en paralelo sobre partes separadas; ninguno invoca a otro subagente.

## Roles

| Rol | Agente | Qué hace |
|---|---|---|
| Orquestador | agente principal | Triage, paquetes de contexto, integración, correcciones, entrega |
| Innovación | `sqf-innovator` | Propone mecánicas viables (red, frame, JIP, dedicado) separando idea de implementación verificada |
| Diseño | `sqf-architect` | Plan de desarrollo: módulos, contrato de interfaces, estado compartido, JIP, orden de init |
| Implementación | `sqf-developer` (hasta 3 en paralelo, un módulo cada uno) | Escribe SOLO los archivos asignados, cumpliendo el contrato y el estándar |
| Determinístico | `sqf-static-analyzer` | sqflint vía script |
| Configuración | `sqf-mission-config-auditor` | Hechos de description.ext, CfgRemoteExec, init |
| Calidad | `sqf-best-practices-reviewer` | Estándar de código |
| Red | `sqf-locality-auditor` | Locality, JIP, HC, softlocks |
| Rendimiento | `sqf-performance-auditor` | Carga del scheduler, escaneos, fugas, plan de medición |
| Prueba | `sqf-test-plan-generator` | Plan manual dedicado + JIP |
| Documentación | `sqf-doc-writer` | Guía de uso del script/sistema |
| Verificación Declarativa | `sqf-claim-verifier` | Audita afirmaciones técnicas contra BIKI y fuentes primarias oficiales (URLs + fechas) |

**Estándar único:** `references/sqf-standards.md`. Lo leen developer, reviewers y el orquestador; así se escribe y se revisa con la misma vara y hay menos iteraciones.

## Paso 0 — Perfil del Proyecto y Triage

### Perfil del Proyecto (declarado una sola vez y transmitido a todos los subagentes)
Antes de clasificar el modo o despachar trabajo, el orquestador determina o valida los **7 parámetros** del **Perfil del Proyecto**:
- **ARMA_VERSION**: [p. ej. retail 2.22]
- **DESTINO**: [mision | addon]   ← nombre único de este campo en todo el plugin
- **CBA**: [sí (v3.19.0) | no]
- **ACE3**: [sí (v3.21.2) | no]
- **SERVIDOR_DEDICADO**: [ruta o no]
- **SQFLINT**: [ruta o no]
- **MODO**: [Micro | Estándar | Completo]

*Reglas de Framework CBA/ACE3*:
1. **Con CBA (`CBA: sí`)**:
   - Usar obligatoriamente Per-Frame Handlers (`CBA_fnc_addPerFrameHandler` / `CBA_fnc_removePerFrameHandler`) en lugar de bucles `spawn-while` persistentes.
   - Usar eventos desacoplados CBA (`CBA_fnc_addEventHandler`, `CBA_fnc_localEvent`, `CBA_fnc_serverEvent`, etc.).
   - Detección en tiempo de ejecución: `isClass (configFile >> "CfgPatches" >> "cba_main")` (Docs oficiales: https://github.com/CBATeam/CBA_A3, consultado 2026-10-03).
2. **Con ACE3 (`ACE3: sí`)**:
   - Detección en tiempo de ejecución: `isClass (configFile >> "CfgPatches" >> "ace_main")` (Docs oficiales: https://ace3.acemod.org/, consultado 2026-10-03).
3. **Sin CBA (`CBA: no`) — Vanilla Estricto**:
   - Usar exclusivamente alternativas vanilla (`spawn { while {...} do { sleep ...; }; }` con salida controlada, `addMissionEventHandler ["EachFrame"]`, o `BIS_fnc_addScriptedEventHandler`).
   - PROHIBICIÓN ABSOLUTA: Jamás introducir dependencias de `CBA_fnc_*` o `ace_*` en silencio si el perfil declara `CBA: no` o `ACE3: no` (constituye defecto Bloqueante).

### Triage de Modo: el script decide el modo determinísticamente

El modo de revisión (`Micro`, `Estándar` o `Completo`) se determina obligatoriamente mediante la ejecución del script:
```bat
python skills/arma3-sqf-review/scripts/sqf_orchestrator.py --root <raíz del proyecto> --mode-query
```
*(Nota: `<raíz del proyecto>` es la carpeta del proyecto SQF bajo revisión, nunca la raíz del plugin. Códigos de salida del script: `0` = cálculo exitoso, `1` = error duro de ruta o argumentos, `10` = completado con `NO VERIFICADO`).*

El script analiza el inventario de archivos `.sqf` del proyecto y emite el informe estructurado (`MODO: ...`, `MOTIVO: ...`, `RESUMEN: modo=...; escalado=...`).
**Inventario vacío:** Si el script devuelve `NO VERIFICADO` por inventario vacío (cero archivos `.sqf` encontrados), **el modo no se decide y hay que preguntar la ruta**. Un modo nunca se concede por defecto ante un inventario vacío; un resultado vacío no es un resultado limpio ni es Micro.
**Fallback obligatorio:** Si el script no está disponible o falla su invocación por causas del entorno, el modo por defecto es `Estándar` y se declara `NO VERIFICADO` en el informe; **NUNCA se clasifica como Micro por criterio manual**.

| Modo | Criterio determinista del script |
|---|---|
| Sin flujo | Typo, ajuste de un valor puntual, pregunta conceptual |
| **Micro** | Exactamente 1 archivo `.sqf` aislado, ≤50 líneas, sin dependencias externas, sin archivos de ciclo de vida (`init*.sqf`, `description.ext`), sin señales de red ni scheduler |
| **Estándar** | Proyecto multi-archivo (2–3 archivos), o >50 líneas, o ciclo de vida de misión, o señales de red (`remoteExec`, `publicVariable`), o modificación de código con red |
| **Completo** | ≥4 archivos o ≥3 módulos, JIP, Headless Client, persistencia, o encargo explícito de auditoría completa |

**Prelectura informativa (orientativa, no decisoria):**
Las expresiones regulares de señales de red y rendimiento se usan únicamente como prelectura informativa previa; la decisión formal reside exclusivamente en `sqf_orchestrator.py` (mediante `sqf_models.py`):
- **Señales de red (prelectura informativa)**: `remoteExec|remoteExecCall|publicVariable|publicVariableServer|publicVariableClient|setVariable\s*\[.*true|isServer|isDedicated|hasInterface|BIS_fnc_MP|addPublicVariableEventHandler|remoteExecutedOwner|setOwner|HeadlessClient|initServer|initPlayer`.
- **Señales de rendimiento (prelectura informativa)**: `while|waitUntil|EachFrame|onEachFrame|Draw3D|allUnits|allGroups|allMissionObjects|nearestObjects|nearEntities|createVehicle|createUnit|createGroup|addEventHandler|addMissionEventHandler|spawn|execVM`.
- **Override**: si el usuario pide explícitamente un modo, se le pasa `--mode <modo>` al orquestador para no re-escalar (salvo Micro con señales de red: avisar del riesgo técnico y escalar).

## Participación por modo

| Rol | Micro | Estándar | Completo |
|---|---|---|---|
| Innovator | — | opcional (si se piden mecánicas nuevas o mejoras) | ✔ si es sistema nuevo o diseño de mecánicas |
| Architect | — (checklist propio) | — (mini-plan de 5 líneas del orquestador) | ✔ |
| Developer | — (escribe el orquestador) | opcional (si hay módulos independientes) | ✔ por módulo |
| Verificación wiki (la hace el orquestador, no es un subagente) | solo comandos no triviales | ✔ (verificando en la Biki) | ✔ (sobre el plan, antes de codificar) |
| Static analyzer | ✔ si hay archivo | ✔ si hay archivo | ✔ |
| Config auditor | — | si hay red y raíz de proyecto (misión o addon) | ✔ |
| Best-practices | 1 pasada: solo bloqueantes + máx. 3 sugerencias | ✔ | ✔ |
| Locality | — | solo con señales de red | ✔ |
| Performance | — (checklist) | solo con señales de rendimiento | ✔ |
| Test plan | — | si intervino locality | ✔ |
| Doc writer | — (cabecera en el código) | si hay API pública o parámetros | ✔ si el sistema tiene interfaz de uso |

**Micro** = 1–2 agentes, cero ceremonia, pero con el **checklist de autoverificación de dedicado** de `sqf-standards.md` aplicado estrictamente por el orquestador antes de entregar.
- **Invariantes de Servidor Dedicado en Micro**: En Micro se mantienen rigurosamente todas las invariantes de dedicado: `player` jamás se utiliza sin verificar `hasInterface`, los comandos de interfaz UI (`hint`, `cutText`) se consideran inútiles o prohibidos en servidor, y jamás se permite `sleep` o `waitUntil` en contextos unscheduled.
- **Análisis Estático Obligatorio**: Si hay archivo en disco, Micro ejecuta OBLIGATORIAMENTE el análisis estático mediante:
  `python skills/arma3-sqf-review/scripts/sqf_orchestrator.py --root <raíz> --lint`
  (o pasando la ruta del archivo). Códigos de salida del script: `0` = reporte producido sin error fatal, `1` = error duro o ruta inválida, `10` = linter no disponible (`NO VERIFICADO`). Si `sqflint` no está disponible (`SQFLINT_NO_DISPONIBLE`), el análisis se reporta como `NO VERIFICADO` (NUNCA como PASA).

## Flujo Completo

1. **Contexto**: objetivo, perfil del proyecto, raíz de misión, máquina de ejecución, si hay archivo en disco. Si el objetivo es ambiguo, haz UNA pregunta al usuario; si no, asume y declara supuestos.
1b. **Innovación** (Estándar/Completo si se piden mecánicas nuevas o mejoras creativas): `sqf-innovator` propone mecánicas viables aplicando los 4 filtros de viabilidad (ancho de banda de red, presupuesto de scheduler/frame, persistencia JIP e invariantes de dedicado) y separando ideas de implementaciones verificadas antes de fijar la arquitectura.
2. **Diseño**: `sqf-architect` → Plan de desarrollo. El orquestador lo valida (¿cubre el objetivo? ¿contratos completos, incluyendo definición explícita de `CfgRemoteExec` para funciones remotas? ¿módulos con archivos disjuntos?).
3. **Verificación previa (paralelo)**: consulta de comandos contra la réplica local `a3ref` (`skills/arma3-sqf-review/scripts/sqf_wiki_reader.py`) como fuente primaria obligatoria, inyectando URL oficial, `revid` y commit SHA dinámico obtenido en tiempo de ejecución (`git rev-parse HEAD`), más `sqf-mission-config-auditor` (hechos de configuración y comprobación cruzada obligatoria de funciones invocadas remotamente contra la whitelist de `CfgRemoteExec`).
   **La caché NO es evidencia sin procedencia.** `references/wiki-cache.md` contiene entradas que deben contrastarse contra `a3ref`. Regla: todo comando se verifica prioritariamente contra la réplica local `a3ref` (`python sqf_wiki_reader.py --command <cmd>`). La búsqueda web opera exclusivamente como fallback secundario cuando una consulta no esté cubierta por el catálogo local y exista herramienta de búsqueda web activa en el entorno. Si un comando no está en la réplica local ni en la web, queda `NO VERIFICADO` — prohibido terminantemente usar comandos de memoria sin verificación.
4. **Implementación**: un `sqf-developer` por módulo, en paralelo (máx. 3 simultáneos). Cada uno recibe: su módulo, el contrato **completo**, hechos de wiki, `sqf-standards.md`. El contrato es inmutable: si un developer lo necesita cambiar, devuelve una *solicitud de cambio de contrato* y el orquestador decide.
5. **Integración** (orquestador): interfaces coinciden con el contrato, orden de init, nombres de variables compartidas sin colisión.
6. **Oleada de revisión (paralelo)**:
   - **Análisis estático (`sqf-static-analyzer`)**: se ejecuta mediante el script orquestador:
     ```bat
     python skills/arma3-sqf-review/scripts/sqf_orchestrator.py --root <raíz> --lint
     ```
     (Códigos de salida del script: `0` = reporte producido sin error fatal, `1` = error duro o ruta inválida, `10` = linter no disponible / `NO VERIFICADO`). El subagente `sqf-static-analyzer` lee directamente el informe estructurado generado por el script (`[BLOQUEANTE|SUGERENCIA|NO_VERIFICADO] archivo:línea (disciplina): descripción` y `RESUMEN: ...`) sin parsear stdout a mano ni aplicar mapeos divergentes de severidad.
   - **Revisores semánticos**: best-practices, locality y performance-auditor, con paquete de contexto.
7. **Corrección** (máx. **3 iteraciones**): orden locality → performance → best-practices. Los arreglos de un archivo los hace su developer (o el orquestador si es trivial). Re-invoca al agente que señaló + `python skills/arma3-sqf-review/scripts/sqf_orchestrator.py --root <raíz> --lint` siempre + best-practices si cambió estructura.
   - **Definición precisa de Bloqueante (P0)** — esta es la ÚNICA definición normativa; no la dupliques en otra sección, refiérela:
     1. **Errores de sintaxis SQF**: errores detectados determinísticamente por `references/run_sqflint.py` (exit code 1) **o variables locales fugadas al scope exterior sin `private`/`params`**. *(Nota: comandos no reconocidos por sqflint se tratan como Sugerencia/Pista a confirmar contra el Biki antes de tratarlos como error. Un warning de scope de sqflint cuenta como BLOQUEANTE, no como sugerencia.)*
     2. **Softlocks potenciales, bucles infinitos o bloqueos de init**: `waitUntil` sin condición alcanzable garantizada ni timeout de seguridad, bucles infinitos sin cadencia (`while {true}` sin suspensión o PFH), retrasos bloqueantes prolongados (`sleep`/`uiSleep`/`waitUntil`) en el hilo principal de scripts de inicialización (`init.sqf`, `initServer.sqf`, `postInit`) que congelan la carga de la misión (deben delegarse a `spawn` desacoplado o PFH), o esperas cruzadas cliente-servidor donde un nodo espera indefinidamente una variable nunca emitida.
     3. **Violaciones críticas de dedicado**: uso de `player` o `waitUntil {!isNull player}` en servidor dedicado (`isDedicated == true`), donde `player` es permanentemente `objNull`; **o ejecución de comandos de interfaz UI (`hint`, `hintC`, `titleText`, `cutText`, `dialog`, `createDialog`, `ctrlCreate`, `displayCtrl`, `findDisplay`, `uiNamespace`, `ppEffect`) en cualquier ruta que pueda ejecutarse en el servidor** — una guarda `if (hasInterface)` NO lo legitima: solo evita el error, no el trabajo inútil. La retroalimentación visual va por `remoteExec` al cliente.
     4. **Suspensión en contexto unscheduled**: `sleep`, `uiSleep` o `waitUntil` donde `canSuspend == false` (`preInit` con `preInit = 1`, Event Handlers del motor, `remoteExecCall`, o código invocado desde un contexto unscheduled). **Ambos** (`sleep` y `uiSleep`) requieren obligatoriamente entorno scheduled.
     5. **Violaciones de whitelist en `CfgRemoteExec`**: invocaciones remotas (`remoteExec`, `remoteExecCall`) de funciones ausentes de la lista blanca de `CfgRemoteExec >> Functions` cuando `mode = 1`.
     6. **Contratos de interfaz rotos o parámetros incompatibles**: discrepancias en cantidad, orden o tipos de datos requeridos en `params` entre módulos o llamadas de función.
     7. **Inyección no permitida de dependencias de framework**: uso de funciones o identificadores de CBA o ACE3 (`CBA_fnc_*`, `ace_*`) cuando el perfil del proyecto declara `CBA: no` o `ACE3: no`.
   - **PUERTA DE CALIDAD INFRANQUEABLE**:
     - El conteo de bloqueantes y la lista de `archivo:línea` provienen directamente del informe estructurado emitido por `sqf_orchestrator.py --lint` (`RESUMEN: bloqueantes=N...`) y de los revisores semánticos.
     - Si tras **3 iteraciones** todavía queda **AL MENOS UN BLOQUEANTE** abierto:
       1. **DETENER** el proceso de forma inmediata.
       2. **INFORMAR AL USUARIO** con el desglose exacto de cada bloqueante sin resolver (agente/disciplina detector, archivo, línea, causa raíz e intentos fallidos extraídos del informe).
       3. **PROHIBIDO DECLARAR "TERMINADO" O ENTREGAR COMO FINAL**. El resultado se marca como `DETENIDO (NO PASA)` y se solicita intervención humana. Se elimina cualquier cláusula de entrega permisiva; código con bloqueantes jamás se entrega como terminado.
     - Solo se avanza a los pasos 8 (Plan de prueba), 9 (Doc writer) y 10 (Entrega) si el número de bloqueantes abiertos es **CERO**.
8. **Plan de prueba**: `sqf-test-plan-generator` con riesgos, "no verificable" y el plan de medición del performance-auditor.
9. **Documentación**: `sqf-doc-writer` **después** del código final (para que la guía coincida con lo entregado).
10. **Entrega**: Aplicación del checklist de salida completo (`references/checklist-entrega.md`) y generación obligatoria del informe de estados por ítem.

**Estándar** = pasos 1, 3 (sin config si no aplica), 4 (orquestador o developers opcionales), 6, 7, y 8–9 según la tabla, con validación de `references/checklist-entrega.md` en el paso 10.
**Micro** = escribir → checklist de invariantes de dedicado (`sqf-standards.md` y `references/checklist-entrega.md`) → análisis estático obligatorio si hay archivo (`python skills/arma3-sqf-review/scripts/sqf_orchestrator.py --root <raíz> --lint`) → `sqf-best-practices-reviewer` → **ciclo de corrección (máx. 3 iteraciones, igual que el modo Estándar)**: si la pasada reporta un BLOQUEANTE en el informe del script o del revisor, se corrige y se vuelve a pasar `sqf-best-practices-reviewer` + `sqf_orchestrator.py --lint`; al alcanzar 3 iteraciones con un BLOQUEANTE abierto se aplica la PUERTA DE CALIDAD INFRANQUEABLE (`DETENIDO (NO PASA)`, sin entrega) → generar informe obligatorio de estados por ítem (`PASA` / `NO PASA` / `NO VERIFICADO`) → entregar (únicamente si CERO bloqueantes).

## Paquete de contexto (formato de traspaso a cualquier subagente)

```
PERFIL:
  ARMA_VERSION: <ej. 2.22>
  DESTINO: <mision | addon>
  CBA: <si (v3.19.0) | no>
  ACE3: <si (v3.21.2) | no>
  SERVIDOR_DEDICADO: <ruta o no>
  SQFLINT: <ruta o no>
  MODO: <Micro | Estándar | Completo>
MODO: Micro|Estándar|Completo
OBJETIVO: <1-3 líneas>
ARCHIVOS / RUTA RAÍZ: <rutas absolutas>
MÁQUINA DE EJECUCIÓN: <por archivo/bloque: servidor|cliente|HC|todos>
ESCALA: <jugadores, IA y objetos esperados; "desconocida" si no se sabe>
CONTRATO (si existe): <interfaces del plan>
HECHOS WIKI: <comando → efecto AL/AG/EL/EG, notas>
INFORMES PREVIOS: <static-analyzer / config-auditor / hallazgos a corregir>
ESTÁNDAR: <ruta absoluta a references/sqf-standards.md>
RESTRICCIONES: <archivos que NO debe tocar, límites del encargo>
```

## Propiedad de reglas (sin hallazgos duplicados)

| Tema | Dueño único |
|---|---|
| Propuesta y viabilidad de mecánicas nuevas (filtros red/frame/JIP/dedicado) | innovator |
| Sintaxis, variable sin `private` (detectable por linter) | static-analyzer |
| Scope/`private`/`params` si el linter no está disponible | best-practices |
| Evaluación perezosa, nomenclatura, tags de globales locales, compileFinal, micro-optimizaciones de sintaxis (`findIf`, `isEqualTo`, `getVariable` con default) | best-practices |
| remoteExec, JIP, publicVariable (tag y frecuencia), sleep/uiSleep/waitUntil, HC, softlocks | locality |
| Coste en ejecución: scheduler, bucles, handlers por frame, escaneos globales, estructuras de datos, fugas de scripts/EH/grupos/objetos, reparto servidor/HC | performance-auditor |
| CfgRemoteExec, CfgFunctions, init, allowFunctionsRecompile | config-auditor (hechos) |
| Diseño de módulos e interfaces | architect |
| Guía de uso | doc-writer |

Un agente que ve algo ajeno lo anota en una línea: "derivado a <agente>".

## Rúbrica de Severidad y Puerta de Calidad

- **Bloqueante (P0)**: ver la definición normativa en el Paso 7 ("Definición precisa de Bloqueante (P0)"). Esa lista es la única fuente; cualquier cambio se hace allí y se referencia desde aquí. Resumen: sintaxis y fugas de scope, softlocks y bloqueos de init, violaciones de dedicado (incluida UI en rutas de servidor), suspensión en unscheduled, whitelist `CfgRemoteExec`, contratos de interfaz rotos, dependencias de framework no autorizadas.
- **Sugerencia**:
  Cuestiones de estilo, legibilidad, nomenclatura secundaria, micro-optimizaciones que no corrigen un bug activo, sugerencias de refactorización opcional.
- **Regla del ciclo**:
  Solo los defectos **Bloqueantes** reinician el ciclo de corrección (Paso 7).
- **Precedencia ante conflictos**:
  1) Correctitud de red y estabilidad en servidor dedicado (locality, desync, softlock, JIP), 2) Rendimiento y scheduler, 3) Estilo y legibilidad. Una optimización de rendimiento JAMÁS se aplica si compromete la estabilidad o la localidad.

## Cuándo se genera guía de uso (`sqf-doc-writer`)

Sí, si se cumple alguno: el script/sistema tiene funciones públicas o parámetros configurables; requiere colocar objetos, triggers o líneas en `init`/`description.ext` (o `config.cpp` si es addon); tiene comportamiento MP relevante (JIP, HC, servidor); lo usará otra persona o tú mismo más adelante; o el usuario lo pide.
No, si es un helper interno, un fix, o un script Micro (basta la cabecera comentada del código).

## Entrega final y Puerta de Calidad Transversal

**REGLA OBLIGATORIA DE ENTREGA EN TODOS LOS MODOS (Micro / Estándar / Completo)**:
Ningún modo puede declarar el trabajo como "terminado" ni entregar código como definitivo sin verificar contra el checklist de entrega (`references/checklist-entrega.md`, bloques A a I) e incluir el **Informe Desglosado de Estados por Ítem** con evaluación estricta: `PASA` / `NO PASA` / `NO VERIFICADO`.
- Si existe al menos un ítem obligatorio en estado `NO PASA` (bloqueante), la entrega se RECHAZA automáticamente, el proceso se DETIENE de forma inmediata y se solicita intervención humana.
- Estados formales permitidos por ítem: `PASA`, `NO PASA`, `NO VERIFICADO` (y `NO APLICA` únicamente si el componente no aplica al modo).
- **Principio de Honestidad Técnica (Invariante de Entorno)**: los ítems correspondientes a ejecución real en servidor dedicado (ítem 10) se marcan `NO VERIFICADO` **salvo que el Perfil del Proyecto declare que el entorno existe y se haya ejecutado**. El Perfil incorpora dos parámetros: `SERVIDOR_DEDICADO: <ruta o no>` y `SQFLINT: <ruta o no>`. Si no están declarados, el ítem es `NO VERIFICADO` por definición y la skill y todos los informes deben declararlo explícitamente. Nunca se afirma haber probado en servidor dedicado si no se ha ejecutado en esta máquina, en esta sesión.
- Si `sqflint` no está disponible (`SQFLINT_NO_DISPONIBLE`), el análisis estático de `run_sqflint.py` se reporta obligatoriamente como `NO VERIFICADO` (JAMÁS como PASA).

### Criterios de Entrega según Destino (Misión vs Addon)

La entrega y validación estructural deben ajustarse estrictamente al valor de `DESTINO` declarado en el perfil del proyecto:
- **Si el destino es Misión (`DESTINO: mision`)**:
  * Configuración central: `description.ext` y scripts de ciclo de vida de misión (`init.sqf`, `initServer.sqf`, `initPlayerLocal.sqf`, `initPlayerServer.sqf`).
  * Estructura: carpetas dentro de la misión (ej. `scripts/`, `core/`).
  * **Regla estricta**: PROHIBIDO exigir o evaluar `CfgPatches`, parámetros de lanzamiento de mod (`-serverMod`, `-mod`), prefijos `$PBOPREFIX$` ni empaquetado PBO. Una misión reside en la carpeta de misiones de Eden/MP.
- **Si el destino es Addon (`DESTINO: addon`)**:
  * Configuración central: `config.cpp` (o `config.bin`) con declaración obligatoria de `CfgPatches` (`name`, `author`, `requiredVersion`, `requiredAddons[]`), `CfgFunctions` y `CfgRemoteExec`.
  * Estructura: código con rutas absolutas de prefijo PBO (`\tag_addon\...`).
  * Distribución: empaquetado PBO (makepbo / hemtt), firma digital (`.bikey`) y parámetros de mod (`-mod=@tag_addon` o `-serverMod=@tag_addon` si es exclusivo de servidor).
  * **Regla estricta**: PROHIBIDO exigir o evaluar `description.ext` ni scripts de ciclo de vida de misión.

### Formato Obligatorio de Entrega

```markdown
## Resumen de revisión
- Modo: [Micro / Estándar / Completo] (escalado: sí/no)
- Iteraciones de corrección: N/3
- Estado global: [PASA / NO PASA (DETENIDO) / NO VERIFICADO]

### Informe de Estados por Ítem
| Ítem / Disciplina | Estado | Evidencia y Justificación |
|---|---|---|
| 1. Análisis Estático / Sintaxis (`run_sqflint.py`) | PASA / NO PASA / NO VERIFICADO | [0 errores / N errores detectados / NO VERIFICADO si sqflint no disponible] |
| 2. Ausencia de softlocks, loops infinitos y bloqueos de init | PASA / NO PASA | [Condición de salida con timeout, loops con cadencia o PFH, sin sleep bloqueante en init] |
| 3. Invariantes de Servidor Dedicado (Estático) | PASA / NO PASA / NO VERIFICADO | [Sin player ni waitUntil {!isNull player} en server, guardas hasInterface] |
| 4. Contexto unscheduled (preInit / EH / remoteExecCall) | PASA / NO PASA | [Sin sleep/uiSleep/waitUntil en preInit, Event Handlers o remoteExecCall; uiSleep requiere canSuspend] |
| 5. Whitelist CfgRemoteExec | PASA / NO PASA / NO APLICA | [Todas las funciones remotas declaradas en CfgRemoteExec mode=1 (description.ext en misión / config.cpp en addon) / NO APLICA] |
| 6. Contratos de interfaz y parámetros (`params`) | PASA / NO PASA | [Parámetros y tipos alineados entre módulos y llamadas de función] |
| 7. Dependencias de Framework (CBA / ACE3 vs Vanilla) | PASA / NO PASA | [Alineado con perfil: PFH/eventos con CBA; vanilla estricto sin dependencias silenciosas si no CBA] |
| 8. Rendimiento y Scheduler | PASA / NO PASA / NO APLICA | [Bucles con cadencia, sin fugas ni escaneos globales intensivos por frame] |
| 9. Verificación de Comandos en Wiki / Biki | PASA / NO VERIFICADO | Regla de Cobertura Documental: - PASA: 100% de tokens candidatos del código contrastados contra réplica offline a3ref (commit: <git_sha_runtime>; 0 ausentes; 0 bloqueantes asociados). - NO VERIFICADO: < 100% contrastados o sqflint no disponible (SQFLINT_NO_DISPONIBLE). Acompañado del número de hallazgos Bloqueantes por comando no identificado. |
| 10. Ejecución en Servidor Dedicado (Runtime Arma3Server) | NO VERIFICADO | [NO VERIFICADO: No existe entorno local Arma3Server ni sqfvm para pruebas dinámicas] |
```

Luego: código final (solo si Estado global es PASA), sugerencias no bloqueantes y plan de prueba manual (Completo / Estándar).

## Validación de la Puerta de Calidad (T09 — diseño del gate)

La regla de detención obligatoria tras 3 iteraciones con bloqueantes abiertos está implementada en `scripts/sqf_orchestrator.py` (condición `iteraciones >= 3 && bloqueantes_abiertos > 0` → `DETENER` + `ESTADO: DETENIDO (NO PASA)` + estado fallido + salida con código 1).

**Estado: NO VERIFICADO en runtime.** La verificación de esta puerta es un test unitario del orquestador (`tests/test_orchestrator_loop.py`), que debe estar presente y en verde en el paquete del plugin. Si ese test no está o no pasa, esta sección declara: `PUERTA DE CALIDAD SIN TEST ADJUNTO — NO VERIFICADA`.

**Consecuencia práctica:** si en algún momento el orquestador no está disponible, el gate sigue aplicando en prosa (Paso 7, "PUERTA DE CALIDAD INFRANQUEABLE") y el resultado se marca `NO VERIFICADO` en la puerta, nunca `PASA`.

## Limitaciones

Los revisores son estáticos: "sin bloqueantes" no garantiza ausencia de carreras JIP, timing o softlocks reales en dedicado con un cliente tardío. Los subagentes no heredan esta skill: todo va en el paquete de contexto. Revisa `/agents` si alguno tarda; no programes timeouts manuales. Toda prueba de ejecución dinámica en servidor dedicado o compilación con sqfvm permanece en estado **NO VERIFICADO** por carecer de tales herramientas en el entorno local.
