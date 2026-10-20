---
trigger: always_on
description: Invariantes SQF/HPP — Arma 3 (scope privado, evaluación perezosa, contexto scheduled, honestidad de verificación y servidor dedicado headless)
---

# Invariantes SQF/HPP — Arma 3

- Toda variable local declarada con `private` o recibida por `params`; sin fugas al scope global.
- Evaluación perezosa (if (a && {b})): útil cuando b es costosa; con condiciones triviales puede ser más lenta que la evaluación normal.
- `sleep` y `waitUntil` solo en entorno programado; en no programado no están permitidos.
- Lo no ejecutado en servidor dedicado se reporta NO VERIFICADO; nunca se declara completo.
- Nomenclatura consistente con las convenciones ya usadas en el proyecto.
- Comentarios inline marcando puntos de reutilización.
- En .hpp/HUDs: jerarquía visual clara, carga cognitiva mínima, evitar interfaces genéricas por defecto.

## Servidor dedicado (headless)

Este producto corre en un servidor dedicado (`Arma3Server.exe`): sin interfaz, sin jugador local, `player` es `objNull`. La máquina local es un entorno de prueba, nunca la especificación.

- **Interfaz prohibida en rutas de servidor.** `hint`, `hintC`, `titleText`, `cutText`, `dialog`, `createDialog`, `ctrlCreate`, `displayCtrl`, `findDisplay`, `uiNamespace`, `ppEffect` y afines no se usan en ninguna ruta que pueda ejecutarse en el servidor. **Una guarda `if (hasInterface)` no las legitima**: la guarda solo evita el error, no el trabajo inútil. Si hace falta retroalimentación visual, va por `remoteExec` al cliente.
- **`player` no existe en el servidor.** `player` es `objNull` permanentemente en dedicado. Si la lógica necesita al jugador, va en `initPlayerLocal.sqf` o por `remoteExec` dirigido a su `owner`.
- **Diagnóstico por `diag_log`**, no con `systemChat` ni `format` hacia `player` (invisibles en dedicado).
- **Banderas de localidad:** `isServer` (servidor o host), `isDedicated` (dedicado sin interfaz), `hasInterface` (máquina con jugador). No las confundas: un `if (isDedicated)` donde debía ir `if (isServer)` rompe el hosted.
- **Sin esperas bloqueantes en el arranque.** `sleep`, `uiSleep` y `waitUntil` en `init.sqf`, `initServer.sqf` o `postInit` retienen el hilo de inicialización. Delega a `spawn` desacoplado o Per-Frame Handler.

Para scripts o sistemas nuevos o cambios de locality y red (remoteExec, publicVariable, JIP), usa la skill arma3-sqf-review, que levanta la revisión de subagentes.
