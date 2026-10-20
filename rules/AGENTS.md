# Invariantes SQF/HPP — Arma 3

- Toda variable local declarada con private o recibida por params; sin fugas al scope global.
- Evaluación perezosa (if (a && {b})): útil cuando b es costosa; con condiciones triviales puede ser más lenta que la evaluación normal.
- sleep y waitUntil solo en entorno programado; en no programado no están permitidos.
- Lo no ejecutado en servidor dedicado se reporta NO VERIFICADO; nunca se declara completo.
- Nomenclatura consistente con las convenciones ya usadas en el proyecto.
- Comentarios inline marcando puntos de reutilización.
- En .hpp/HUDs: jerarquía visual clara, carga cognitiva mínima, evitar interfaces genéricas por defecto.

Para scripts o sistemas nuevos o cambios de locality y red (remoteExec, publicVariable, JIP), usa la skill arma3-sqf-review, que levanta la revisión de subagentes.
