Estado: NO VERIFICADO, usar como pista; ante cualquier duda, consultar el Biki

# Caché de verificación wiki (community.bistudio.com)

Usar solo como pista. Re-verificar si la entrada tiene más de 6 meses
o si cambió la versión del juego.
Efectos: AL = argumento local, AG = argumento global, EL = efecto local, EG = efecto global.

| Comando | Sintaxis | Arg | Efe | Nota MP / Restricciones | URL Biki | Verificado |
|---|---|---|---|---|---|---|
| `remoteExec` | `params remoteExec [fnc, targets, JIP]` | AG | EG | Sujeto a CfgRemoteExec (mode=1). Funciones en scheduled; comandos de script en unscheduled. | https://community.bistudio.com/wiki/remoteExec | NO VERIFICADO (memoria) |
| `remoteExecCall` | `params remoteExecCall [fnc, targets, JIP]` | AG | EG | Ejecución síncrona en unscheduled en el target. PROHIBIDO sleep/waitUntil. | https://community.bistudio.com/wiki/remoteExecCall | NO VERIFICADO (memoria) |
| `publicVariable` | `publicVariable "varName"` | AL | EG | Broadcast global de variable. No dispara PVEH en la máquina emisora. Alto coste en bucles. | https://community.bistudio.com/wiki/publicVariable | NO VERIFICADO (memoria) |
| `publicVariableServer` | `publicVariableServer "varName"` | AL | EL (Servidor) | Envía variable únicamente al servidor dedicado / host (clientOwner 2). | https://community.bistudio.com/wiki/publicVariableServer | NO VERIFICADO (memoria) |
| `publicVariableClient` | `clientId publicVariableClient "varName"` | AL | EL (Cliente) | Envía variable exclusivamente al ID de máquina especificado. | https://community.bistudio.com/wiki/publicVariableClient | NO VERIFICADO (memoria) |
| `addEventHandler` | `entity addEventHandler [type, code]` | AL | EL | Manejador local a la máquina. No transfiere al cambiar localidad con setOwner. | https://community.bistudio.com/wiki/addEventHandler | NO VERIFICADO (memoria) |
| `addMissionEventHandler` | `addMissionEventHandler [type, code]` | AL | EL | Manejador a nivel de misión (EachFrame, PlayerConnected, Ended). Requiere baja manual. | https://community.bistudio.com/wiki/addMissionEventHandler | NO VERIFICADO (memoria) |
| `removeEventHandler` | `entity removeEventHandler [type, id]` | AL | EL | Elimina un event handler por su identificador para evitar fugas. | https://community.bistudio.com/wiki/removeEventHandler | NO VERIFICADO (memoria) |
| `removeMissionEventHandler` | `removeMissionEventHandler [type, id]` | AL | EL | Elimina un manejador de misión para prevenir leaks de hilos EachFrame. | https://community.bistudio.com/wiki/removeMissionEventHandler | NO VERIFICADO (memoria) |
| `params` | `params [param1, [param2, def, [types]]]` | AL | EL | Declara y tipa variables locales con defaults seguros ante inputs inválidos. | https://community.bistudio.com/wiki/params | NO VERIFICADO (memoria) |
| `spawn` | `params spawn code` | AL | EL | Crea hilo asíncrono en scheduler. Permite sleep y waitUntil. Retorna Script Handle. | https://community.bistudio.com/wiki/spawn | NO VERIFICADO (memoria) |
| `call` | `params call code` | AL | EL | Ejecución síncrona en el entorno del llamador. Si es unscheduled, sleep falla. | https://community.bistudio.com/wiki/call | NO VERIFICADO (memoria) |
| `execVM` | `params execVM "path.sqf"` | AL | EL | Compila y ejecuta script en hilo scheduled. Evitar en bucles por frame. | https://community.bistudio.com/wiki/execVM | NO VERIFICADO (memoria) |
| `waitUntil` | `waitUntil {condition}` | AL | EL | Suspende hilo scheduled hasta condición true. En servidor con player causa softlock infinito. | https://community.bistudio.com/wiki/waitUntil | NO VERIFICADO (memoria) |
| `sleep` | `sleep seconds` | AL | EL | Pausa en tiempo de simulación de juego. Solo entorno scheduled. Mínimo ~0.03 s. | https://community.bistudio.com/wiki/sleep | NO VERIFICADO (memoria) |
| `uiSleep` | `uiSleep seconds` | AL | EL | Pausa en tiempo real de interfaz (no afectada por pause/setAccTime). Solo scheduled. | https://community.bistudio.com/wiki/uiSleep | NO VERIFICADO (memoria) |
| `isServer` | `isServer` | AL | EL | Retorna true en servidor dedicado y en host de partida; false en clientes puros y HC. | https://community.bistudio.com/wiki/isServer | NO VERIFICADO (memoria) |
| `isDedicated` | `isDedicated` | AL | EL | Retorna true ÚNICAMENTE en servidor dedicado sin interfaz humana. | https://community.bistudio.com/wiki/isDedicated | NO VERIFICADO (memoria) |
| `hasInterface` | `hasInterface` | AL | EL | Retorna true si hay UI/pantalla (jugador humano). False en dedicado y en Headless Client. | https://community.bistudio.com/wiki/hasInterface | NO VERIFICADO (memoria) |
| `createUnit` | `group createUnit [type, pos, ...]` | AL | EG | Crea unidad con localidad en la máquina emisora (o grupo). Sincronizada globalmente. | https://community.bistudio.com/wiki/createUnit | NO VERIFICADO (memoria) |
| `createVehicle` | `type createVehicle pos` | AG | EG | Crea vehículo con propagación global. Preferente ejecutar en servidor en MP. | https://community.bistudio.com/wiki/createVehicle | NO VERIFICADO (memoria) |
| `deleteVehicle` | `deleteVehicle entity` | AG | EG | Elimina entidad globalmente en todas las máquinas conectadas. | https://community.bistudio.com/wiki/deleteVehicle | NO VERIFICADO (memoria) |
| `addAction` | `object addAction [title, script, ...]` | AL | EL | Añade acción al menú contextual local. Debe ejecutarse en clientes para ser visible. | https://community.bistudio.com/wiki/addAction | NO VERIFICADO (memoria) |
| `removeAction` | `object removeAction id` | AL | EL | Elimina acción local por ID en la máquina donde fue añadida. | https://community.bistudio.com/wiki/removeAction | NO VERIFICADO (memoria) |
| `hint` | `hint "text"` | AL | EL | Muestra texto de interfaz. En servidor dedicado (sin interfaz) es un no-op inofensivo. | https://community.bistudio.com/wiki/hint | NO VERIFICADO (memoria) |
| `diag_log` | `diag_log "text"` | AL | EL | Escribe línea en el log arma3.rpt de la máquina local. Crítico en servidor dedicado. | https://community.bistudio.com/wiki/diag_log | NO VERIFICADO (memoria) |
| `setOwner` | `object setOwner newOwnerId` | AL (Servidor) | EG | Transfiere localidad de IA a otro cliente o HC. Solo ejecutable en servidor. | https://community.bistudio.com/wiki/setOwner | NO VERIFICADO (memoria) |
| `owner` | `owner object` | AG | EL | Retorna el clientOwner ID de la máquina donde el objeto es actualmente local. | https://community.bistudio.com/wiki/owner | NO VERIFICADO (memoria) |
| `remoteExecutedOwner`| `remoteExecutedOwner` | AL | EL | Retorna el client ID de quien disparó el remoteExec actual. Validación de seguridad en servidor. | https://community.bistudio.com/wiki/remoteExecutedOwner | NO VERIFICADO (memoria) |
| `didJIP` | `didJIP` | AL | EL | Retorna true si la máquina cliente actual se unió a la partida en progreso (JIP). | https://community.bistudio.com/wiki/didJIP | NO VERIFICADO (memoria) |



