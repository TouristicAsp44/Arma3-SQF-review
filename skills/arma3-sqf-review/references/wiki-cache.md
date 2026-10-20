# Caché de referencia wiki (community.bistudio.com)

AVISO: Esta tabla es un índice de referencia histórica interna, NO constituye evidencia de verificación formal.
Toda afirmación técnica sobre sintaxis, comportamiento multijugador, efectos de red o localidad debe verificarse
directamente en la documentación oficial de Bohemia Interactive (Biki) registrando la URL exacta y la fecha de consulta.
Las entradas sin fecha de consulta verificada no deben ser utilizadas como hecho demostrado.

Efectos:
- AL: Argumento Local
- AG: Argumento Global
- EL: Efecto Local
- EG: Efecto Global

| Comando | Sintaxis | Arg | Efe | Nota MP / Restricciones | URL Biki | Estado | Consultado | Fuente |
|---|---|---|---|---|---|---|---|---|
| `remoteExec` | `params remoteExec [fnc, targets, JIP]` | AG | EG | Sujeto a CfgRemoteExec (mode=1). Funciones en scheduled; comandos de script en unscheduled. Whitelist obligatoria. | https://community.bistudio.com/wiki/remoteExec | VERIFICADO | 2026-10-20 | Bohemia Interactive Community Wiki |
| `remoteExecCall` | `params remoteExecCall [fnc, targets, JIP]` | AG | EG | Ejecución síncrona en unscheduled en el target. PROHIBIDO sleep/waitUntil. Whitelist en CfgRemoteExec. | https://community.bistudio.com/wiki/remoteExecCall | VERIFICADO | 2026-10-20 | Bohemia Interactive Community Wiki |
| `publicVariable` | `publicVariable "varName"` | AL | EG | Broadcast global de variable. No dispara PVEH en la máquina emisora. Alto coste en bucles. | https://community.bistudio.com/wiki/publicVariable | VERIFICADO | 2026-10-20 | Bohemia Interactive Community Wiki |
| `addEventHandler` | `entity addEventHandler [type, code]` | AL | EL | Manejador local a la máquina. No transfiere al cambiar localidad con setOwner. Requiere removeEventHandler. | https://community.bistudio.com/wiki/addEventHandler | VERIFICADO | 2026-10-20 | Bohemia Interactive Community Wiki |
| `addMissionEventHandler` | `addMissionEventHandler [type, code]` | AL | EL | Manejador a nivel de misión (EachFrame, PlayerConnected, Ended). Requiere baja manual con removeMissionEventHandler. | https://community.bistudio.com/wiki/addMissionEventHandler | VERIFICADO | 2026-10-20 | Bohemia Interactive Community Wiki |
| `params` | `params [param1, [param2, def, [types]]]` | AL | EL | Declara y tipa variables locales con defaults seguros ante inputs inválidos. | https://community.bistudio.com/wiki/params | VERIFICADO | 2026-10-20 | Bohemia Interactive Community Wiki |
| `spawn` | `params spawn code` | AL | EL | Crea hilo asíncrono en scheduler. Permite sleep y waitUntil. Retorna Script Handle. | https://community.bistudio.com/wiki/spawn | VERIFICADO | 2026-10-20 | Bohemia Interactive Community Wiki |
| `call` | `params call code` | AL | EL | Ejecución síncrona en el entorno del llamador. Si es unscheduled, sleep causa error. | https://community.bistudio.com/wiki/call | VERIFICADO | 2026-10-20 | Bohemia Interactive Community Wiki |
| `execVM` | `params execVM "path.sqf"` | AL | EL | Compila y ejecuta script en hilo scheduled. Evitar en bucles por frame o llamadas recurrentes. | https://community.bistudio.com/wiki/execVM | VERIFICADO | 2026-10-20 | Bohemia Interactive Community Wiki |
| `waitUntil` | `waitUntil {condition}` | AL | EL | Suspende hilo scheduled hasta condición true. En servidor con player causa softlock infinito. Requiere cadencia y timeout. | https://community.bistudio.com/wiki/waitUntil | VERIFICADO | 2026-10-20 | Bohemia Interactive Community Wiki |
| `publicVariableServer` | `publicVariableServer "varName"` | AL | EL (Servidor) | Envía variable únicamente al servidor dedicado / host (clientOwner 2). | https://community.bistudio.com/wiki/publicVariableServer | NO VERIFICADA (no usar como hecho sin consultar Biki) | - | - |
| `publicVariableClient` | `clientId publicVariableClient "varName"` | AL | EL (Cliente) | Envía variable exclusivamente al ID de máquina especificado. | https://community.bistudio.com/wiki/publicVariableClient | NO VERIFICADA (no usar como hecho sin consultar Biki) | - | - |
| `removeEventHandler` | `entity removeEventHandler [type, id]` | AL | EL | Elimina un event handler por su identificador para evitar fugas. | https://community.bistudio.com/wiki/removeEventHandler | NO VERIFICADA (no usar como hecho sin consultar Biki) | - | - |
| `removeMissionEventHandler` | `removeMissionEventHandler [type, id]` | AL | EL | Elimina un manejador de misión para prevenir leaks de hilos EachFrame. | https://community.bistudio.com/wiki/removeMissionEventHandler | NO VERIFICADA (no usar como hecho sin consultar Biki) | - | - |
| `sleep` | `sleep seconds` | AL | EL | Pausa en tiempo de simulación de juego. Solo entorno scheduled. Mínimo ~0.03 s. | https://community.bistudio.com/wiki/sleep | NO VERIFICADA (no usar como hecho sin consultar Biki) | - | - |
| `uiSleep` | `uiSleep seconds` | AL | EL | Pausa en tiempo real de interfaz (no afectada por pause/setAccTime). Solo scheduled. | https://community.bistudio.com/wiki/uiSleep | NO VERIFICADA (no usar como hecho sin consultar Biki) | - | - |
| `isServer` | `isServer` | AL | EL | Retorna true en servidor dedicado y en host de partida; false en clientes puros y HC. | https://community.bistudio.com/wiki/isServer | NO VERIFICADA (no usar como hecho sin consultar Biki) | - | - |
| `isDedicated` | `isDedicated` | AL | EL | Retorna true ÚNICAMENTE en servidor dedicado sin interfaz humana. | https://community.bistudio.com/wiki/isDedicated | NO VERIFICADA (no usar como hecho sin consultar Biki) | - | - |
| `hasInterface` | `hasInterface` | AL | EL | Retorna true si hay UI/pantalla (jugador humano). False en dedicado y en Headless Client. | https://community.bistudio.com/wiki/hasInterface | NO VERIFICADA (no usar como hecho sin consultar Biki) | - | - |
| `createUnit` | `group createUnit [type, pos, ...]` | AL | EG | Crea unidad con localidad en la máquina emisora (o grupo). Sincronizada globalmente. | https://community.bistudio.com/wiki/createUnit | NO VERIFICADA (no usar como hecho sin consultar Biki) | - | - |
| `createVehicle` | `type createVehicle pos` | AG | EG | Crea vehículo con propagación global. Preferente ejecutar en servidor en MP. | https://community.bistudio.com/wiki/createVehicle | NO VERIFICADA (no usar como hecho sin consultar Biki) | - | - |
| `deleteVehicle` | `deleteVehicle entity` | AG | EG | Elimina entidad globalmente en todas las máquinas conectadas. | https://community.bistudio.com/wiki/deleteVehicle | NO VERIFICADA (no usar como hecho sin consultar Biki) | - | - |
| `addAction` | `object addAction [title, script, ...]` | AL | EL | Añade acción al menú contextual local. Debe ejecutarse en clientes para ser visible. | https://community.bistudio.com/wiki/addAction | NO VERIFICADA (no usar como hecho sin consultar Biki) | - | - |
| `removeAction` | `object removeAction id` | AL | EL | Elimina acción local por ID en la máquina donde fue añadida. | https://community.bistudio.com/wiki/removeAction | NO VERIFICADA (no usar como hecho sin consultar Biki) | - | - |
| `hint` | `hint "text"` | AL | EL | Muestra texto de UI en cliente humano. PROHIBIDO en rutas que puedan ejecutarse en servidor; hasInterface no lo legitima. Enviar por remoteExec al cliente. | https://community.bistudio.com/wiki/hint | NO VERIFICADA (no usar como hecho sin consultar Biki) | - | - |
| `diag_log` | `diag_log "text"` | AL | EL | Escribe línea en el log arma3.rpt de la máquina local. Crítico en servidor dedicado. | https://community.bistudio.com/wiki/diag_log | NO VERIFICADA (no usar como hecho sin consultar Biki) | - | - |
| `setOwner` | `object setOwner newOwnerId` | AL (Servidor) | EG | Transfiere localidad de IA a otro cliente o HC. Solo ejecutable en servidor. | https://community.bistudio.com/wiki/setOwner | NO VERIFICADA (no usar como hecho sin consultar Biki) | - | - |
| `owner` | `owner object` | AG | EL | Retorna el clientOwner ID de la máquina donde el objeto es actualmente local. | https://community.bistudio.com/wiki/owner | NO VERIFICADA (no usar como hecho sin consultar Biki) | - | - |
| `remoteExecutedOwner`| `remoteExecutedOwner` | AL | EL | Retorna el client ID de quien disparó el remoteExec actual. Validación de seguridad en servidor. | https://community.bistudio.com/wiki/remoteExecutedOwner | NO VERIFICADA (no usar como hecho sin consultar Biki) | - | - |
| `didJIP` | `didJIP` | AL | EL | Retorna true si la máquina cliente actual se unió a la partida en progreso (JIP). | https://community.bistudio.com/wiki/didJIP | NO VERIFICADA (no usar como hecho sin consultar Biki) | - | - |
