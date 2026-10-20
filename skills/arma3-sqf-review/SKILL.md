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

**Estándar único:** `references/sqf-standards.md`. Lo leen developer, reviewers y el orquestador; así se escribe y se revisa con la misma vara y hay menos iteraciones.

## Paso 0 — Perfil del Proyecto y Triage

### Perfil del Proyecto (declarado una sola vez y transmitido a todos los subagentes)
Antes de clasificar el modo o despachar trabajo, el orquestador determina o valida los 5 parámetros del **Perfil del Proyecto**:
- **Versión de Arma 3**: [p. ej. retail 2.22]
- **Tipo de proyecto**: [Misión (Eden) | Addon]
- **CBA**: [sí (v3.19.0) | no]
- **ACE3**: [sí (v3.21.2) | no]
- **Modo**: [Micro | Estándar | Completo]

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

### Triage de Modo: el modo lo fija la señal más alta

| Modo | Se activa si… |
|---|---|
| Sin flujo | Typo, ajuste de un valor, pregunta conceptual |
| **Micro** | Exactamente 1 archivo aislado, ≤50 líneas (función única autocontenida o corrección puntual), SIN dependencias externas, SIN archivos de ciclo de vida (`init*.sqf`, `description.ext`), SIN señales de red ni estado compartido ni persistencia |
| **Estándar** | 2–3 archivos, o >50 líneas, o presencia de archivos de ciclo de vida de misión, o una señal de red puntual (un remoteExec/publicVariable), o modificación de código existente con red |
| **Completo** | ≥4 archivos o ≥3 módulos, o JIP/estado persistente, o Headless Client, o remoteExec + estado compartido, o sistema nuevo con interfaz para el editor de misiones, o se pide "auditoría completa" |

**Salvaguardas de Modo Micro y Criterios Estrictos de Exclusión**:
Un proyecto grande o complejo no puede caer en modo Micro por error. Para clasificar en Micro, deben cumplirse TODAS las condiciones básicas simultáneamente (un único archivo autocontenido, ≤50 líneas, sin red ni dependencias).
Si el encargo o código cumple **CUALQUIERA** de los siguientes criterios de exclusión, **SE PROHÍBE EL MODO MICRO Y ESCALA OBLIGATORIAMENTE A ESTÁNDAR O COMPLETO**:
1. **Volumen de código y archivos**: Más de 3 archivos (>3 archivos) o más de 150 líneas de código en total (>150 líneas total, en cualquier archivo individual o suma del proyecto).
2. **Primitivas de red MP**: Uso o modificación de primitivas de red multijugador (`remoteExec`, `remoteExecCall`, `publicVariable`, variables de broadcast o sincronización remota).
3. **Lógica JIP y sincronización de estado**: Manejo de Join In Progress (JIP), persistencia o sincronización de estado compartido entre clientes y servidor.
4. **Configuración de misión**: Modificaciones, creación o dependencias en `description.ext` (incluyendo `CfgRemoteExec`, `CfgFunctions`) o scripts de ciclo de vida de misión (`init.sqf`, `initServer.sqf`, `initPlayerLocal.sqf`).
5. **Infraestructura de servidor dedicado**: Lógica orientada a servidor dedicado (`isDedicated`, Headless Client, gestión de ownership y migración de localidad).
6. **Carga y control del scheduler**: Bucles persistentes (`while`), esperas (`waitUntil`), handlers por frame (`onEachFrame`, `EachFrame`) o escaneos globales masivos (`allUnits`, `allMissionObjects`).
→ **ESCALA INMEDIATAMENTE a Estándar (o Completo)**. Ante la duda o ambigüedad, NUNCA usar Micro. Un proyecto grande jamás puede caer en Micro.

**Señales de red** (grep): `remoteExec|remoteExecCall|publicVariable|setVariable\s*\[.*true|isServer|isDedicated|hasInterface|BIS_fnc_MP|addPublicVariableEventHandler|remoteExecutedOwner|setOwner|HeadlessClient|initServer|initPlayer`.

**Señales de rendimiento** (grep): `while|waitUntil|EachFrame|onEachFrame|Draw3D|allUnits|allGroups|allMissionObjects|nearestObjects|nearEntities|createVehicle|createUnit|createGroup|addEventHandler|addMissionEventHandler|spawn|execVM`. Un script Micro con bucle persistente, handler por frame o escaneo global sube a Estándar.

- **Escalada**: si durante el trabajo se cruza un umbral, sube de modo y avisa en una línea. Nunca bajes.
- **Override**: si el usuario pide un modo, se respeta (salvo Micro con señales de red: avisa del riesgo y escala).

## Participación por modo

| Rol | Micro | Estándar | Completo |
|---|---|---|---|
| Innovator | — | opcional (si se piden mecánicas nuevas o mejoras) | ✔ si es sistema nuevo o diseño de mecánicas |
| Architect | — (checklist propio) | — (mini-plan de 5 líneas del orquestador) | ✔ |
| Developer | — (escribe el orquestador) | opcional (si hay módulos independientes) | ✔ por módulo |
| Wiki | solo comandos no triviales | ✔ (con caché) | ✔ (sobre el plan, antes de codificar) |
| Static analyzer | ✔ si hay archivo | ✔ si hay archivo | ✔ |
| Config auditor | — | si hay red y raíz de proyecto (misión o addon) | ✔ |
| Best-practices | 1 pasada: solo bloqueantes + máx. 3 sugerencias | ✔ | ✔ |
| Locality | — | solo con señales de red | ✔ |
| Performance | — (checklist) | solo con señales de rendimiento | ✔ |
| Test plan | — | si intervino locality | ✔ |
| Doc writer | — (cabecera en el código) | si hay API pública o parámetros | ✔ si el sistema tiene interfaz de uso |

**Micro** = 1–2 agentes, cero ceremonia, pero con el **checklist de autoverificación de dedicado** de `sqf-standards.md` aplicado estrictamente por el orquestador antes de entregar.
- **Invariantes de Servidor Dedicado en Micro**: En Micro se mantienen rigurosamente todas las invariantes de dedicado: `player` jamás se utiliza sin verificar `hasInterface`, los comandos de interfaz UI (`hint`, `cutText`) se consideran inútiles o prohibidos en servidor, y jamás se permite `sleep` o `waitUntil` en contextos unscheduled.
- **Análisis Estático Obligatorio**: Si hay archivo en disco, Micro ejecuta OBLIGATORIAMENTE `sqf-static-analyzer` (mediante `references/run_sqflint.py`). (Fallback global si falla la resolución de ruta: `C:\Users\Touri\.gemini\config\skills\arma3-sqf-review\references\run_sqflint.py`). Si `sqflint` no está disponible (`SQFLINT_NO_DISPONIBLE`), el análisis se reporta como `NO VERIFICADO` (NUNCA como PASA).

## Flujo Completo

1. **Contexto**: objetivo, perfil del proyecto, raíz de misión, máquina de ejecución, si hay archivo en disco. Si el objetivo es ambiguo, haz UNA pregunta al usuario; si no, asume y declara supuestos.
1b. **Innovación** (Estándar/Completo si se piden mecánicas nuevas o mejoras creativas): `sqf-innovator` propone mecánicas viables aplicando los 4 filtros de viabilidad (ancho de banda de red, presupuesto de scheduler/frame, persistencia JIP e invariantes de dedicado) y separando ideas de implementaciones verificadas antes de fijar la arquitectura.
2. **Diseño**: `sqf-architect` → Plan de desarrollo. El orquestador lo valida (¿cubre el objetivo? ¿contratos completos, incluyendo definición explícita de `CfgRemoteExec` para funciones remotas? ¿módulos con archivos disjuntos?).
3. **Verificación previa (paralelo)**: wiki sobre los comandos del plan (caché primero, `references/wiki-cache.md`; navegador vía `/browser` solo lo que falte o tenga >6 meses) + `sqf-mission-config-auditor` (hechos de configuración y comprobación cruzada obligatoria de funciones invocadas remotamente contra la whitelist de `CfgRemoteExec`).
4. **Implementación**: un `sqf-developer` por módulo, en paralelo (máx. 3 simultáneos). Cada uno recibe: su módulo, el contrato **completo**, hechos de wiki, `sqf-standards.md`. El contrato es inmutable: si un developer lo necesita cambiar, devuelve una *solicitud de cambio de contrato* y el orquestador decide.
5. **Integración** (orquestador): interfaces coinciden con el contrato, orden de init, nombres de variables compartidas sin colisión.
6. **Oleada de revisión (paralelo)**: static-analyzer, best-practices, locality y performance-auditor, con paquete de contexto.
7. **Corrección** (máx. **3 iteraciones**): orden locality → performance → best-practices. Los arreglos de un archivo los hace su developer (o el orquestador si es trivial). Re-invoca al agente que señaló + static-analyzer siempre (`references/run_sqflint.py`) + best-practices si cambió estructura.
   - **Definición precisa de Bloqueante (P0)**:
     Cualquiera de los siguientes 7 tipos es un bloqueante estricto que reinicia el ciclo de corrección o detiene el flujo:
     1. **Errores de sintaxis SQF**: Errores detectados determinísticamente por `run_sqflint.py` (exit code 1).
     2. **Softlocks potenciales, bucles infinitos o bloqueos de init**: `waitUntil` sin condición alcanzable ni timeout de salvaguarda, esperas o bucles bloqueantes prolongados (`sleep`/`waitUntil`) en el flujo principal de `init.sqf`, `initServer.sqf` o `postInit` que congelan la carga de la misión (deben delegarse a `spawn` desacoplado o PFH), o esperas cruzadas cliente-servidor donde un nodo espera indefinidamente una variable nunca emitida.
     3. **Violaciones críticas de dedicado**: Uso de `player` o `waitUntil {!isNull player}` en servidor dedicado (`isDedicated == true`), donde `player` es permanentemente `objNull`.
     4. **Suspensión en contexto unscheduled**: `sleep`, `uiSleep` o `waitUntil` en contextos unscheduled (`canSuspend == false`): `preInit` (`preInit = 1`), Event Handlers (`addEventHandler`, `addMissionEventHandler`), `remoteExecCall` o funciones atómicas en `call`. Ambos (`sleep` y `uiSleep`) requieren obligatoriamente entorno scheduled (`canSuspend == true`).
     5. **Violaciones de whitelist en `CfgRemoteExec`**: Invocaciones remotas (`remoteExec`, `remoteExecCall`) de funciones no declaradas en la whitelist de `CfgRemoteExec` cuando `mode = 1`.
     6. **Contratos de interfaz rotos o parámetros incompatibles**: Desajustes en tipos, orden o cantidad de argumentos en `params` entre módulos o llamadas de función.
     7. **Inyección no permitida de dependencias de framework**: Uso de funciones o identificadores de CBA o ACE3 (`CBA_fnc_*`, `ace_*`) cuando el perfil del proyecto no las declara (`CBA: no` o `ACE3: no`).
   - **PUERTA DE CALIDAD INFRANQUEABLE**:
     - Si tras **3 iteraciones** todavía queda **AL MENOS UN BLOQUEANTE** abierto:
       1. **DETENER** el proceso de forma inmediata.
       2. **INFORMAR AL USUARIO** con el desglose exacto de cada bloqueante sin resolver (agente/disciplina detector, archivo, línea, causa raíz e intentos fallidos).
       3. **PROHIBIDO DECLARAR "TERMINADO" O ENTREGAR COMO FINAL**. El resultado se marca como `DETENIDO (NO PASA)` y se solicita intervención humana. Se elimina cualquier cláusula de entrega permisiva; código con bloqueantes jamás se entrega como terminado.
     - Solo se avanza a los pasos 8 (Plan de prueba), 9 (Doc writer) y 10 (Entrega) si el número de bloqueantes abiertos es **CERO**.
8. **Plan de prueba**: `sqf-test-plan-generator` con riesgos, "no verificable" y el plan de medición del performance-auditor.
9. **Documentación**: `sqf-doc-writer` **después** del código final (para que la guía coincida con lo entregado).
10. **Entrega**: Aplicación del checklist de salida completo (`references/checklist-entrega.md`) y generación obligatoria del informe de estados por ítem.

**Estándar** = pasos 1, 3 (sin config si no aplica), 4 (orquestador o developers opcionales), 6, 7, y 8–9 según la tabla, con validación de `references/checklist-entrega.md` en el paso 10.
**Micro** = escribir → checklist de invariantes de dedicado (`sqf-standards.md` y `references/checklist-entrega.md`) → `sqf-static-analyzer` (obligatorio si hay archivo, mediante `references/run_sqflint.py`) → 1 pasada de `sqf-best-practices-reviewer` → generar informe obligatorio de estados por ítem (`PASA` / `NO PASA` / `NO VERIFICADO`) → entregar (únicamente si CERO bloqueantes).

## Paquete de contexto (formato de traspaso a cualquier subagente)

```
PERFIL:
  ARMA_VERSION: <ej. 2.22>
  TIPO: <mision | addon>
  CBA: <si (v3.19.0) | no>
  ACE3: <si (v3.21.2) | no>
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

- **Bloqueante**: Defecto crítico que impide la compilación o ejecución, viola las invariantes de servidor dedicado, produce desincronización de red, satura el scheduler o cuelga hilos de ejecución. Se definen exhaustivamente las **7 categorías de bloqueante (P0)**:
  1. **Errores de sintaxis SQF**: Errores detectados determinísticamente por `references/run_sqflint.py` (código de salida 1: paréntesis/llaves desbalanceadas, comillas sin cerrar, sintaxis inválida, operadores erróneos) o variables locales fugadas al scope exterior sin `private`/`params`. *(Nota: Comandos no reconocidos por sqflint se tratan como Sugerencia/Pista a confirmar contra el Biki antes de tratarlos como error)*.
  2. **Softlocks potenciales, bucles infinitos o bloqueos de init**: `waitUntil` sin condición alcanzable garantizada ni timeout de seguridad, bucles infinitos sin cadencia (`while {true}` sin suspensión o PFH), retrasos bloqueantes prolongados (`sleep`/`waitUntil`) en el hilo principal de scripts de inicialización (`init.sqf`, `initServer.sqf`, `postInit`) que congelan la pantalla de carga de los clientes (deben desacoplarse a `spawn` o PFH), o esperas cruzadas cliente-servidor donde un nodo espera indefinidamente una variable nunca emitida o sincronizada.
  3. **Violaciones críticas de dedicado**: Uso de `player` o `waitUntil {!isNull player}` en servidor dedicado (`isDedicated == true`), donde `player` es permanentemente `objNull`, o ejecución de comandos de interfaz UI (`hint`, `titleText`, `cutText`, creación de diálogos) en servidor dedicado sin guarda `hasInterface`.
  4. **Suspensión en contexto unscheduled**: Uso de `sleep`, `uiSleep` o `waitUntil` en contextos unscheduled o atómicos (`canSuspend == false`): funciones con `preInit = 1`, Event Handlers del motor (`addEventHandler`, `addMissionEventHandler`), llamadas mediante `remoteExecCall` o código ejecutado dentro de `call`. Ambos (`sleep` y `uiSleep`) requieren obligatoriamente entorno scheduled (`canSuspend == true`).
  5. **Violaciones de whitelist en `CfgRemoteExec`**: Invocaciones remotas (`remoteExec`, `remoteExecCall`) de funciones ausentes de la lista blanca de `CfgRemoteExec` cuando `mode = 1` en `description.ext`.
  6. **Contratos de interfaz rotos o parámetros incompatibles**: Discrepancias en cantidad, orden o tipos de datos requeridos en `params` entre módulos o llamadas de función del sistema.
  7. **Inyección no permitida de dependencias de framework**: Uso de funciones o identificadores de CBA o ACE3 (`CBA_fnc_*`, `ace_*`) cuando el perfil del proyecto declara `CBA: no` o `ACE3: no`.
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
- **Principio de Honestidad Técnica (Invariante de Entorno)**: Dado que NO existe un ejecutable local de servidor dedicado (`Arma3Server`) ni compilador de máquina virtual (`sqfvm`), los ítems correspondientes a ejecución real en servidor dedicado permanecen OBLIGATORIAMENTE en estado `NO VERIFICADO`. La skill y todos los informes deben declararlo explícitamente y nunca asegurar haber probado en servidor dedicado si no se ha ejecutado.
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
| 9. Verificación de Comandos en Wiki / Biki | PASA / NO VERIFICADO | [Comandos contrastados en wiki-cache o Biki oficial con URL y fecha] |
| 10. Ejecución en Servidor Dedicado (Runtime Arma3Server) | NO VERIFICADO | [NO VERIFICADO: No existe entorno local Arma3Server ni sqfvm para pruebas dinámicas] |
```

Luego: código final (solo si Estado global es PASA), sugerencias no bloqueantes y plan de prueba manual (Completo / Estándar).

## Validación de la Puerta de Calidad (Caso Simulado T09 — Estado: LEÍDO)

La regla de detención obligatoria tras 3 iteraciones con bloqueantes abiertos se valida formalmente mediante el caso de prueba simulado T09:
- **Identificador de Caso**: T09 (Puerta de calidad: Parada inmediata tras 3 iteraciones con bloqueantes).
- **Estado de Evidencia**: **LEÍDO** (prueba simulada de diseño lógico del flujo del orquestador; clasificada explícitamente como estado `LEÍDO`, NO VERIFICADO en runtime, debido a la ausencia de ejecutable de servidor dedicado en la máquina local).
- **Escenario de simulación**:
  1. *Entrada*: Función invocada en Event Handler (`addEventHandler ["Killed", { [_this] call TAG_fnc_handleKilled; }];`) donde `TAG_fnc_handleKilled` contiene `sleep 2;`.
  2. *Iteración 1*: `sqf-locality-auditor` emite `[BLOQUEANTE 4] Suspensión en unscheduled: sleep en Event Handler`. El desarrollador intenta sustituir por `waitUntil { time > _timeout }` (sin spawn). Contador = 1.
  3. *Iteración 2*: `sqf-locality-auditor` re-audita y detecta que `waitUntil` también viola unscheduled (`[BLOQUEANTE 4] waitUntil en unscheduled`). El desarrollador envuelve en `spawn`, pero introduce un error de sintaxis SQF detectable por `run_sqflint.py` (exit code 1). `sqf-static-analyzer` emite `[BLOQUEANTE 1] Error sintáctico en run_sqflint.py`. Contador = 2.
  4. *Iteración 3*: Se corrige la sintaxis pero el desarrollador altera los argumentos esperados en `params` rompiendo la compatibilidad entre módulos (`[BLOQUEANTE 6] Parámetros incompatibles en contrato de interfaz`). Al finalizar la revisión de la iteración 3, permanece 1 bloqueante abierto. Contador = 3.
  5. *Evaluación de la Puerta (Paso 7)*:
     - Condición evaluada: `iteraciones >= 3 && bloqueantes_abiertos > 0`.
     - Acción del Orquestador: **DETENER INMEDIATAMENTE (DETENER)**. Emite `ESTADO: DETENIDO (NO PASA) TRAS 3 ITERACIONES`.
     - Reporta desglose pormenorizado del bloqueante abierto y solicita intervención humana al usuario.
     - **PROHIBIDO DECLARAR "TERMINADO" O ENTREGAR COMO FINAL**. Se cancela la entrega y no se avanzan a los pasos 8, 9 ni 10.
- **Resultado del Caso**: Bloqueo y detención garantizados. Código con bloqueantes jamás se promueve a producción ni se entrega como final. Estado: **LEÍDO**.

## Limitaciones

Los revisores son estáticos: "sin bloqueantes" no garantiza ausencia de carreras JIP, timing o softlocks reales en dedicado con un cliente tardío. Los subagentes no heredan esta skill: todo va en el paquete de contexto. Revisa `/agents` si alguno tarda; no programes timeouts manuales. Toda prueba de ejecución dinámica en servidor dedicado o compilación con sqfvm permanece en estado **NO VERIFICADO** por carecer de tales herramientas en el entorno local.
