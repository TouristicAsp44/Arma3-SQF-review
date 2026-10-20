# Checklist de Entrega y Salida — arma3-sqf-review

Guía normativa de control de calidad e invariantes de multijugador para misiones y addons de Arma 3.
Ningún desarrollo se considerará finalizado sin haber evaluado la totalidad de los bloques aplicables.

---

## 1. Regla de Estados

Cada punto de control debe evaluarse de forma determinista y honesta bajo uno de los siguientes tres estados formales:

- **`PASA`**: Comprobado positivamente mediante análisis estático (`run_sqflint.py`), inspección de código o evidencia lógica verificada en documentación oficial.
- **`NO PASA`**: Defecto, discrepancia o violación de invariante detectada. Constituye un **Bloqueante** que detiene el flujo y prohíbe la entrega como finalizado.
- **`NO VERIFICADO`**: Punto de control no comprobable en este entorno (p. ej., pruebas de ejecución dinámica en runtime de `Arma3Server` o máquina virtual `sqfvm` por ausencia de binarios en el host). Debe declararse explícitamente en el informe final; **NUNCA** se asume como `PASA`.

---

## 2. Bloques de Verificación (A – I)

### Bloque A: Compilación y Sintaxis
- [ ] **A.1 Parseo determinista**: El código analizado con `references/run_sqflint.py` finaliza con código de salida `0` (`SIN ERRORES`). Cero errores sintácticos de comillas, llaves o puntos y coma.
- [ ] **A.2 Compatibilidad de versión**: Todos los comandos SQF utilizados están soportados y vigentes según la versión declarada en el Perfil del Proyecto (ARMA_VERSION).
- [ ] **A.3 Ausencia de comandos obsoletos**: Prohibido el uso de primitivas obsoletas de red o scripting (p. ej., `BIS_fnc_MP`, reemplazado por `remoteExec`/`remoteExecCall`).
- [ ] **A.4 Resolución de directivas e inclusión**: Todas las directivas `#include`, `#define` y rutas relativas resuelven archivos existentes sin enlaces rotos ni dependencias locales del autor.

### Bloque B: Invariantes de Servidor Dedicado
- [ ] **B.1 Arranque headless y RPT limpio**: No existen errores de script ni warnings de pre-inicialización al cargar en un servidor dedicado sin interfaz humana.
- [ ] **B.2 Aislamiento de entidad `player`**: Cero referencias a la variable `player` en hilos exclusivos del servidor (`isDedicated == true`), donde `player` devuelve permanentemente `objNull`.
- [ ] **B.3 Prohibición de softlock por espera de jugador**: NUNCA utilizar `waitUntil {!isNull player}` en `initServer.sqf` o en funciones exclusivas del servidor (provoca bloqueo infinito del arranque).
- [ ] **B.4 Interfaz en servidor dedicado**: Los comandos de interfaz (`hint`, `hintC`, `titleText`, `cutText`, `dialog`, `createDialog`, `ctrlCreate`, `displayCtrl`, `findDisplay`, `uiNamespace`, `ppEffect` y afines) no se usan en ninguna ruta que pueda ejecutarse en el servidor, y una guarda `if (hasInterface)` no los legitima. Si hace falta retroalimentación visual, va por `remoteExec` al cliente.
- [ ] **B.5 Prohibición de suspensión en unscheduled**: Cero llamadas a `sleep`, `uiSleep` o `waitUntil` en contextos unscheduled (`preInit`, Event Handlers del motor, `remoteExecCall`).
- [ ] **B.6 Acotamiento de `waitUntil`**: Todo `waitUntil` implementa cadencia de verificación y condición de salida por tiempo límite (timeout) para evitar hilos colgados.

### Bloque C: Red, Locality y Seguridad
- [ ] **C.1 Destinos de `remoteExec` explícitos y justificados**: Toda llamada remota define un destino concreto (`0` = global, `2` = servidor, `-2` = clientes excluyendo servidor, o ID específico de cliente); prohibido el broadcast indiscriminado.
- [ ] **C.2 Whitelist estricta en `CfgRemoteExec`**: Toda función invocada remotamente está registrada en `CfgRemoteExec >> Functions` con `mode = 1` y las directivas `allowedTargets` y `jip` coherentes con el código.
- [ ] **C.3 Validación de remitente en servidor**: Las funciones remotas que alteran estado sensible en el servidor validan el ID emisor con `remoteExecutedOwner`.
- [ ] **C.4 Prohibición de broadcast de alta frecuencia**: Prohibido el envío de `remoteExec`, `remoteExecCall` o `publicVariable` por frame (`EachFrame`) o en bucles rápidos sin temporizador.
- [ ] **C.5 Persistencia y ciclo JIP**: Las llamadas con bandera `JIP = true` cuentan con registro de JIP ID o limpieza posterior (`remoteExec ["", _jipId]`); los clientes tardíos sincronizan estado desde `initPlayerLocal.sqf`.

### Bloque D: Ciclo de Vida y Limpieza
- [ ] **D.1 Baja obligatoria de handlers y acciones**: Todo manejador (`addEventHandler`, `addMissionEventHandler`) y acción de usuario (`addAction`) cuenta con su correspondiente mecanismo de baja (`removeEventHandler`, `removeMissionEventHandler`, `removeAction`) para evitar fugas al reiniciar o finalizar la misión.
- [ ] **D.2 Control de variables globales y scope**: Cero fugas de variables locales al ámbito global (uso sistemático de `private` y `params`).
- [ ] **D.3 Convención de nombres globales**: Todas las variables y funciones globales utilizan obligatoriamente el prefijo de tag del proyecto (`TAG_` o `TAG_fnc_`).
- [ ] **D.4 Orden de inicialización**: Las funciones públicas están compiladas y disponibles antes de que cualquier script o evento remoto las invoque.

### Bloque E: Robustez y Manejo de Errores
- [ ] **E.1 Parámetros tipados con valores por defecto**: Uso de sintaxis extendida de `params` con defaults defensivos y tipos esperados (`[param, def, [types]]`).
- [ ] **E.2 Validación de límites de arrays y objetos nulos**: Validación de existencia previa con `isNull` y verificación de tamaño antes de acceder a índices mediante `select`.
- [ ] **E.3 Evaluación perezosa defensiva**: Uso de operadores perezosos `&& { ... }` y `|| { ... }` en expresiones compuestas con riesgo de evaluación nula o cálculos pesados.
- [ ] **E.4 Degradación limpia de frameworks**: Si CBA o ACE3 están activos según el perfil, se verifica su presencia mediante `isClass (configFile >> "CfgPatches" >> "cba_main")` / `ace_main`. Si no están declarados, se mantiene código vanilla estricto sin dependencias no autorizadas.

### Bloque F: Rendimiento y Scheduler
- [ ] **F.1 Cadencia en bucles periódicos**: Bucles recurrentes gestionados con Per-Frame Handler (`CBA_fnc_addPerFrameHandler` si CBA = sí) o manejador `EachFrame` con delta time si CBA = no. Prohibido el uso de `spawn { while {true} do { sleep ...; }; }` sin handle ni control de terminación.
- [ ] **F.2 Cero compilaciones repetitivas**: Prohibido el uso de `execVM` dentro de bucles o funciones frecuentes; las funciones se compilan una sola vez vía `CfgFunctions` o `compileFinal`.
- [ ] **F.3 Inicialización ágil**: `init.sqf`, `initServer.sqf` y funciones `postInit` libres de trabajo pesado bloqueante prolongado para no congelar la pantalla de carga.

### Bloque G: Plan de Pruebas
- [ ] **G.1 Cobertura de escenarios**: Plan de pruebas manual con casos detallados para Servidor Dedicado, Cliente con interfaz, Cliente JIP tardío y desconexión/reconexión de clientes.
- [ ] **G.2 Procedimientos reproducibles**: Cada caso define precondición, acción concreta, resultado esperado y señal inequívoca de fallo.
- [ ] **G.3 Registro de RPT**: Directrices para auditar el log `arma3server.rpt` en busca de errores y advertencias de script.

### Bloque H: Entrega y Empaquetado
- [ ] **H.1 Rutas relativas universales**: Ausencia absoluta de rutas absolutas locales del equipo de desarrollo.
- [ ] **H.2 Dependencias documentadas**: Requisitos de versión y mods declarados expresamente en la documentación y en los archivos de configuración.
- [ ] **H.3 Guía de instalación y uso**: Documentación de despliegue clara y alineada exactamente con el destino del proyecto (Misión vs Addon).

### Bloque I: Honestidad Técnica
- [ ] **I.1 Desglose de estados obligatorio**: El informe final presenta la tabla completa de estados por ítem (`PASA` / `NO PASA` / `NO VERIFICADO`).
- [ ] **I.2 Cero bloqueantes abiertos**: Prohibido declarar "terminado" si existe al menos un ítem obligatorio en `NO PASA`.
- [ ] **I.3 Transparencia de limitaciones**: Las pruebas dinámicas de servidor dedicado se reportan obligatoriamente como `NO VERIFICADO` por limitación del entorno local, sin simular ejecuciones inexistentes.

---

## 3. Sección Diferencial: Misiones (Eden) vs Addons (Mods)

Los requisitos estructurales y de configuración varían radicalmente según el tipo de proyecto declarado en el perfil (`DESTINO: mision` vs `DESTINO: addon`):

| Característica / Criterio | Variante Misión (Eden / Campaña MP) | Variante Addon (Mod empaquetado PBO) |
|---|---|---|
| **Archivo principal de configuración** | `description.ext` en la raíz de la carpeta de la misión. | `config.cpp` (compilado a `config.bin`) en la raíz del addon. |
| **Declaración `CfgPatches`** | **NO APLICA / PROHIBIDO EXIGIR**. Las misiones no definen `CfgPatches`. | **OBLIGATORIO**. Define la clase del addon, `name`, `author`, `requiredVersion` y `requiredAddons[]`. |
| **Lista blanca de `CfgRemoteExec`** | Declarada dentro de `description.ext >> CfgRemoteExec >> Functions`. | Declarada dentro de `config.cpp >> CfgRemoteExec >> Functions`. |
| **Declaración `CfgFunctions`** | En `description.ext >> CfgFunctions`. Rutas relativas a la carpeta de la misión (ej. `file = "scripts\miFuncion.sqf";`). | En `config.cpp >> CfgFunctions`. Rutas absolutas con prefijo PBO (ej. `file = "\tag_addon\functions\fn_miFuncion.sqf";`). |
| **Scripts de ciclo de vida del motor** | `init.sqf`, `initServer.sqf`, `initPlayerLocal.sqf`, `initPlayerServer.sqf`. | No utiliza scripts de ciclo de vida de misión. Utiliza funciones con `preInit = 1` o `postInit = 1` en `CfgFunctions`. |
| **Prefijo de empaquetado ($PBOPREFIX$)** | No aplica durante la edición en Eden ni en carpetas descomprimidas de misión. | Obligatorio en el proyecto fuente para definir la ruta virtual del PBO (ej. `tag_addon`). |
| **Distribución y Empaquetado** | Carpeta de misión de Eden o archivo `.pbo` en directorio `MPMissions/`. | Compilado a archivo `.pbo` mediante herramientas como MakePBO / HEMTT, ubicado en `@tu_mod/addons/`. |
| **Parámetros de lanzamiento del servidor** | Parámetros estándar de misión en `server.cfg` (`template = "mision.mapa";`). | Lanzado mediante `-mod=@tu_mod` (clientes y servidor) o `-serverMod=@tu_mod` (exclusivo servidor). |
| **Firmas digitales y claves** | No requiere firmas `.bikey` a nivel de misión. | Requiere firmado con clave privada (`.biprivatekey`) y distribución de clave pública `.bikey` en carpeta `keys/`. |
