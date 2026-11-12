# FICHA OPERATIVA: INTEGRACIÓN WIKI BIKI / A3REF (ARMA 3 SQF REVIEW)

**Documento:** `FICHA-INTEGRACION-A3REF.md`  
**Destino:** Guía Operativa de Consulta, Uso y Mantenimiento  
**Plugin:** `arma3-sqf-review` (`C:\Users\Touri\.gemini\config\plugins\arma3-sqf-review`)  
**Versión del Plugin:** `1.1.0`  
**Fecha de Actualización:** 12 de Noviembre de 2026  
**Estado:** **OPERATIVO (VERIFICADO EN SUITE DE 48 PRUEBAS Y PRUEBA REAL V2 SOBRE AL_SNOWSTORM)**  

---

## 1. Prerrequisitos de Entorno

1. **Python 3.10 o superior:** Probado y certificado en Python 3.14.4 (Windows).
2. **Analizador Estático `sqflint`:**  
   Declarado como dependencia formal en `requirements.txt` (`sqflint==0.3.2`).  
   > [!IMPORTANT]
   > `sqflint` es una **dependencia de entorno preinstalada**. Si el ejecutable `sqflint` no está presente o accesible en el entorno del usuario, el orquestador reporta de forma controlada y determinista `SQFLINT_NO_DISPONIBLE` (código de salida 10) y degrada el Ítem 9 a `NO VERIFICADO`, sin provocar caídas ni tracebacks del proceso.
3. **Réplica Local `a3ref`:**  
   Conjunto de datos estructurados JSON de la Bohemia Interactive Community Wiki (BIKI).

---

## 2. Ubicación del Espejo Local y Reglas de Sobreescritura

La ruta hacia la base de datos local de la wiki se resuelve mediante la siguiente jerarquía estricta:

1. **Parámetro CLI explícito:**  
   `--wiki-path "<ruta_hacia_data>"` en cualquier script (`sqf_wiki_reader.py`, `sqf_orchestrator.py` o `sync_wiki_cache.py`).
2. **Variable de Entorno `A3REF_WIKI_PATH`:**  
   Si la variable está definida en la sesión (`$env:A3REF_WIKI_PATH = "C:\ruta\data"`), tiene prioridad sobre el valor por defecto.
3. **Ruta Local por Defecto:**  
   `c:\Users\Touri\Documents\EDEN EDITOR\Skills Antigravity\Wiki\data`

> [!WARNING]
> **Protección contra caídas silenciosas (Regla D6):**  
> Si la variable de entorno `A3REF_WIKI_PATH` está definida pero apunta a una ruta inexistente en disco, el sistema **no cae silenciosamente a la ruta por defecto**. Notifica explícitamente el fallo y reporta estado `NO_VERIFICADO (directorio no existe: <ruta>)`.

---

## 3. Conector Autónomo (`sqf_wiki_reader.py`)

Ubicación del script:  
`C:\Users\Touri\.gemini\config\plugins\arma3-sqf-review\skills\arma3-sqf-review\scripts\sqf_wiki_reader.py`

### 3.1 Consulta de Comandos (`--command`)
Obtiene la información técnica detallada de un comando SQF desde `commands.json`.
```powershell
python "C:\Users\Touri\.gemini\config\plugins\arma3-sqf-review\skills\arma3-sqf-review\scripts\sqf_wiki_reader.py" --command "setPos"
```
* **Salida esperada:** Objeto JSON con nombre canónico, estado, versión Arma 3 (`arma3_since`), localidad de argumentos y efecto (`locality: {"argument": "global", "effect": "global"}`) y URL oficial de la BIKI tomada directamente del registro.

### 3.2 Consulta de Funciones (`--function`)
Consulta funciones oficiales de Bohemia (`BIS_fnc_...`) desde `functions.json`.
```powershell
python "C:\Users\Touri\.gemini\config\plugins\arma3-sqf-review\skills\arma3-sqf-review\scripts\sqf_wiki_reader.py" --function "BIS_fnc_dynamicGroups"
```
* **Salida esperada:** Objeto JSON de la función con versión y URL oficial.

### 3.3 Búsqueda Sintáctica en Dos Pasos (`--lookup`)
Resolución rápida utilizada por el pipeline de análisis estático: comprueba primero `syntax.json` y desempata tipos (comando > función > tópico) contra `index.json`.
```powershell
python "C:\Users\Touri\.gemini\config\plugins\arma3-sqf-review\skills\arma3-sqf-review\scripts\sqf_wiki_reader.py" --lookup "playSoundUI"
```
* **Salida esperada:**
  ```json
  {
    "canonical_name": "playSoundUI",
    "status": "ok",
    "version": "2.10",
    "replaced_by": null,
    "url": "https://community.bistudio.com/wiki/playSoundUI",
    "type": "command"
  }
  ```

### 3.4 Consulta de Tópicos con Liberación de Memoria (`--topic`)
Lectura puntual bajo demanda de artículos temáticos (`topics.json`), liberando inmediatamente la estructura de datos pesada de la memoria RAM (Regla D9).
```powershell
python "C:\Users\Touri\.gemini\config\plugins\arma3-sqf-review\skills\arma3-sqf-review\scripts\sqf_wiki_reader.py" --topic "Multiplayer Scripting"
```
* **Salida esperada:** JSON del tópico seleccionado con menos de 0.09 MB retenidos post-consulta.

### 3.5 Huella Criptográfica del Snapshot (`--sha`)
Obtiene en tiempo de ejecución el commit SHA de Git del repositorio local de datos.
```powershell
python "C:\Users\Touri\.gemini\config\plugins\arma3-sqf-review\skills\arma3-sqf-review\scripts\sqf_wiki_reader.py" --sha
```
* **Salida esperada:** Hash SHA de 40 caracteres (ej. `2c396002987f3ab536931b5a4f627ae03397d449`).

### 3.6 Sincronización Git de Repositorios (`--update-wiki`)
Actualización `git pull --ff-only` secuencial y segura (Regla D4).
```powershell
python "C:\Users\Touri\.gemini\config\plugins\arma3-sqf-review\skills\arma3-sqf-review\scripts\sqf_wiki_reader.py" --update-wiki
```
* **Comportamiento:**
  - Límite de tiempo estricto de 30 segundos por operación.
  - Verificación previa de árbol limpio (`git status --porcelain`). Si hay modificaciones locales, aborta.
  - Sincroniza primero `data/` y luego la raíz. Si el primero falla, el segundo no se ejecuta.
  - Salida limpia de una sola línea en `stderr` y código 1 ante errores, sin tracebacks.

---

## 4. Script de Sincronización de Caché (`sync_wiki_cache.py`)

Ubicación del script:  
`C:\Users\Touri\.gemini\config\plugins\arma3-sqf-review\skills\arma3-sqf-review\scripts\sync_wiki_cache.py`

### 4.1 Modo Simulación (`--dry-run`)
Es la forma segura de inspeccionar qué celdas se completarían y qué filas se marcarían como ausentes antes de escribir en la tabla. **No modifica el archivo en disco ni crea respaldos.**
```powershell
python "C:\Users\Touri\.gemini\config\plugins\arma3-sqf-review\skills\arma3-sqf-review\scripts\sync_wiki_cache.py" --dry-run
```
* **Salida esperada:**
  ```text
  [DRY-RUN] Sincronización analizada: 31 filas totales | 31 verificadas | 0 ausentes | 0 no revisadas | Git SHA: 2c396002987f3ab536931b5a4f627ae03397d449 (Sin escrituras en disco).
  ```

### 4.2 Sincronización Real Idempotente
Actualiza `wiki-cache.md` completando exclusivamente celdas vacías (`-`) y preservando intactas las notas humanas preexistentes.
```powershell
python "C:\Users\Touri\.gemini\config\plugins\arma3-sqf-review\skills\arma3-sqf-review\scripts\sync_wiki_cache.py"
```
> [!NOTE]
> **Idempotencia Garantizada:** El script de sincronización es estrictamente idempotente. Una segunda ejecución sobre un archivo ya sincronizado no produce diferencias, verificado mediante huellas criptográficas SHA-256 idénticas entre ejecuciones consecutivas.

---

## 5. Comandos del Orquestador (`sqf_orchestrator.py`)

Ubicación del script:  
`C:\Users\Touri\.gemini\config\plugins\arma3-sqf-review\skills\arma3-sqf-review\scripts\sqf_orchestrator.py`

### 5.1 Revisión Estática de Archivo SQF o Carpeta con Enriquecimiento BIKI
Ejecuta el pipeline completo: `sqflint` -> enriquecimiento documental en dos pasos -> degradación controlada de severidad -> cálculo dinámico del Ítem 9 del Checklist.
```powershell
# Revisión de un archivo individual
python "C:\Users\Touri\.gemini\config\plugins\arma3-sqf-review\skills\arma3-sqf-review\scripts\sqf_orchestrator.py" --file "C:\ruta\a\mi_script.sqf"

# Revisión de una carpeta completa de proyecto
python "C:\Users\Touri\.gemini\config\plugins\arma3-sqf-review\skills\arma3-sqf-review\scripts\sqf_orchestrator.py" --lint --input "C:\ruta\a\carpeta_mision"
```
* **Salida esperada:**
  1. Lista de hallazgos estructurada: `[SEVERIDAD] archivo:línea (Disciplina): descripción`.
  2. Línea de resumen: `RESUMEN: bloqueantes=X; sugerencias=Y; no_verificado=Z`.
  3. Fila del Ítem 9 del Checklist con cobertura dinámica de tokens y commit SHA en runtime.

#### Comportamiento del Ítem 9 en Modo Archivo vs Modo Carpeta
El orquestador adapta el cálculo documental según la naturaleza del objetivo analizado:
1. **Modo Archivo Individual (`--file` o `--input <archivo.sqf>`):**
   - Extrae el código fuente del archivo individual.
   - Aplica las dos fuentes de candidatos: marcas de identificadores no interpretables del analizador (`Fuente 1`) e identificadores que inician sentencia en el código fuente (`Fuente 2`).
   - Contrasta los candidatos contra la réplica offline `a3ref` (índice sintáctico `syntax.json`).
   - Asocia hallazgos bloqueantes del mismo archivo si algún token resulta ausente.
2. **Modo Carpeta / Directorio (`--lint --input <carpeta>`):**
   - Enumera de forma determinística y ordenada todos los archivos `.sqf` del árbol especificado.
   - Aplica lectura robusta multi-codificación (`read_sqf_file_robust`), soportando de forma transparente UTF-8 (con y sin BOM), UTF-16 Little Endian (con BOM), UTF-16 Big Endian (con BOM) y Windows-1252 / ANSI. Ningún archivo con codificación válida de Arma 3 es omitido ni produce caracteres corruptos.
   - **Cobertura Documental Agregada:** El universo de candidatos se calcula de forma agregada sumando los identificadores de todos los archivos válidos analizados en la carpeta, garantizando que la cobertura refleje el código real completo del proyecto.
   - **Asociación Estricta de Bloqueantes por Archivo:** Para prevenir falsos positivos por contaminación cruzada en proyectos grandes, la búsqueda de bloqueantes asociados a un token ausente se acota estrictamente a los hallazgos generados en ese mismo archivo (`file_findings`). Un token ausente en el archivo A jamás capturará un bloqueante del archivo B.
   - **Coherencia Contractual de Resumen:** Si el Ítem 9 resulta en `NO VERIFICADO` (por ejemplo, ante ausencia del linter o presencia de tokens ausentes sin clasificar), el contador `no_verificado` en la línea de resumen final reporta obligatoriamente un valor $\ge 1$, eliminando cualquier discrepancia entre el resumen numérico y la tabla del checklist.

> [!IMPORTANT]
> **Advertencia Normativa sobre Fugas de Ámbito en Lógica de Addons (Ruido Conocido sin Degradación):**  
> El analizador estático (`sqflint`) evalúa variables locales no declaradas privadamente (`scope leaks`) sin disponer del contexto de inicialización global del motor de Arma 3 (`CfgFunctions`, preInits o variables globales del entorno). En módulos de addons o scripts de terceros (como librerías ambientales o de efectos), esto suele disparar decenas de advertencias de variables de ámbito (`Variable ... is not private`).  
> **Política de Calidad del Equipo:** Dichas fugas de ámbito constituyen ruido conocido derivado de la ausencia de contexto de addons, pero **NO se degradan bajo ninguna circunstancia a sugerencias o advertencias informativas**. Se mantienen estrictamente como **`BLOQUEANTE`** con disciplina `Scope`, preservando el estándar riguroso de servidor dedicado headless en el que toda fuga local representa un riesgo de colisión de variables entre clientes y servidor.
Ejecuta el pipeline completo: `sqflint` -> enriquecimiento documental en dos pasos -> degradación controlada de severidad -> cálculo dinámico del Ítem 9 del Checklist.
```powershell
# Revisión de un archivo individual
python "C:\Users\Touri\.gemini\config\plugins\arma3-sqf-review\skills\arma3-sqf-review\scripts\sqf_orchestrator.py" --file "C:\ruta\a\mi_script.sqf"

# Revisión de una carpeta completa de proyecto
python "C:\Users\Touri\.gemini\config\plugins\arma3-sqf-review\skills\arma3-sqf-review\scripts\sqf_orchestrator.py" --lint --input "C:\ruta\a\carpeta_mision"
```
* **Salida esperada:**
  1. Lista de hallazgos estructurada: `[SEVERIDAD] archivo:línea (Disciplina): descripción`.
  2. Línea de resumen: `RESUMEN: bloqueantes=X; sugerencias=Y; no_verificado=Z`.
  3. Fila del Ítem 9 del Checklist con cobertura dinámica de tokens y commit SHA en runtime.

### 5.2 Consulta Rápida desde el Orquestador (`--wiki`)
```powershell
python "C:\Users\Touri\.gemini\config\plugins\arma3-sqf-review\skills\arma3-sqf-review\scripts\sqf_orchestrator.py" --wiki "setPos"
```

### 5.3 Actualización de Wiki desde el Orquestador (`--update-wiki`)
```powershell
python "C:\Users\Touri\.gemini\config\plugins\arma3-sqf-review\skills\arma3-sqf-review\scripts\sqf_orchestrator.py" --update-wiki
```

---

## 6. Procedimiento de Verificación del Snapshot

Para certificar que el pipeline está utilizando el snapshot esperado y no una fuente degradada:
1. Ejecute `python sqf_wiki_reader.py --sha`.
2. Inspeccione la salida de cualquier revisión con `sqf_orchestrator.py`: la fila del Ítem 9 incluye la procedencia exacta:
   `... contrastados contra réplica offline a3ref (commit: <sha_runtime>; ...)`
3. Compruebe que coincide con el commit de su repositorio local:
   ```powershell
   git -C "c:\Users\Touri\Documents\EDEN EDITOR\Skills Antigravity\Wiki\data" rev-parse HEAD
   ```

---

## 7. Procedimiento de Vuelta Atrás (Rollback) y Política de Retención

Toda la reversibilidad de la integración descansa en dos mecanismos complementarios:

### 7.1 Esquema de Respaldos Externos Fechados
* **Directorio de Respaldos:**  
  `C:\Users\Touri\.gemini\antigravity\backups\arma3-sqf-review\`
* **Nomenclatura de Archivos:**  
  Cada archivo modificado cuenta con una copia fechada (`<archivo>.<YYYYMMDD_HHMMSS>.bak`) y una copia de referencia rápida (`<archivo>.bak.latest`).
* **Política de Retención Acumulativa e Inalterable:**  
  Tanto el script de sincronización como las herramientas del plugin generan copias fechadas y de referencia rápida sin purgar ninguna de las dos. **Las copias se acumulan en cada ejecución de forma permanente e inalterable fuera del árbol del plugin**, garantizando la trazabilidad histórica completa sin borrados automáticos.
* **Restauración Manual desde Respaldos:**  
  ```powershell
  # Ejemplo: restaurar sqf_models.py a su última versión previa
  Copy-Item "C:\Users\Touri\.gemini\antigravity\backups\arma3-sqf-review\scripts\sqf_models.py.bak.latest" "C:\Users\Touri\.gemini\config\plugins\arma3-sqf-review\skills\arma3-sqf-review\scripts\sqf_models.py" -Force
  ```

### 7.2 Línea Base en Repositorio Git Local del Plugin
La raíz del plugin está inicializada como repositorio Git local independiente (sin remotos configurados):
* **Commit Baseline:** `51a00a0fff6c17970cde2a09b12c59a7059ce679` (`baseline: estado previo a la integracion del espejo local y a la version 1.1.0 del plugin`).
* **Commit Versión 1.1.0:** `b4d1815f9d784a896d8e87498c09192455938458` (`feat: bump version to 1.1.0 and declare sqflint==0.3.2 in requirements.txt`).
* **Commit Corrección Defecto 11 (Modo Carpeta):** `a133ebcfe6dfa181f38b18a6fcef18a158e7c237` (`fix(orchestrator): habilitar calculo del Item 9 en modo carpeta con asociacion por archivo y coherencia de resumen`).
* **Vuelta Atrás en una Línea al Baseline:**  
  ```powershell
  git -C "C:\Users\Touri\.gemini\config\plugins\arma3-sqf-review" reset --hard 51a00a0fff6c17970cde2a09b12c59a7059ce679
  ```

---

## 8. Tabla de Límites del Alcance Operativo

| Dimensión | Límite Operativo / Regla Estricta |
|---|---|
| **Naturaleza Estática** | La revisión es puramente estática. No sustituye la matriz de decisión arquitectónica ni la lista de comandos bloqueantes del contrato de auditoría de red y localidad multijugador. |
| **Coincidencia Exacta de Grafía** | La degradación de severidad (`BLOQUEANTE` -> `SUGERENCIA`) opera **únicamente** cuando la grafía del identificador coincide de forma exacta y con la misma combinación de mayúsculas y minúsculas que el catálogo oficial (`commands.json`/`functions.json`). El casing divergente preserva `BLOQUEANTE`. |
| **Honestidad Técnica de Afirmaciones** | Ninguna afirmación técnica sobre el comportamiento de un comando (localidad de argumentos/efecto, versión mínima, sintaxis admitida) puede ser utilizada como hecho sin su correspondiente ficha contrastada y verificada contra el snapshot local. |
| **Límites de Multijugador y Servidor Dedicado** | El análisis estático no detecta condiciones de carrera dinámicas en el scheduler de Arma 3, saturación de la red por broadcast de variables ni bloqueos producidos por jugadores que se unen tarde (JIP). Todo código crítico requiere validación en servidor dedicado según el checklist. |
| **Servidor MCP de Biki Deshabilitado** | La vía de servidor de referencia MCP permanece deshabilitada por ausencia de Node.js en el host. La Vía A de lectura directa local asume el 100% de la carga de verificación. |
| **Cobertura Documental Agregada en Modo Carpeta** | En análisis de carpetas, el universo de candidatos del Ítem 9 agrega todos los archivos `.sqf` válidos con soporte robusto multi-codificación (UTF-8, UTF-16, ANSI), mientras que la asociación de bloqueantes a tokens ausentes se restringe estrictamente por archivo. |
| **Invariante de Severidad ante Fugas de Ámbito en Addons** | Las fugas de ámbito en lógica de addons representan ruido conocido por falta de contexto global en análisis estático, pero nunca se degradan: permanecen como `BLOQUEANTE` para proteger la estabilidad de servidor dedicado. |
| **Alcance Real del Escaneo Documental** | El universo de candidatos del Ítem 9 se construye con dos fuentes: los identificadores que inician sentencia en el código real y los identificadores que el analizador reporta como no interpretables; los identificadores que aparecen en posición de argumento solo quedan cubiertos cuando el analizador los reporta como no interpretables; en consecuencia el Ítem 9 mide la cobertura documental de ese subconjunto de candidatos y no de la superficie completa de comandos que el código invoca; y la cifra de porcentaje que aparece en la fila se refiere siempre al denominador de candidatos, nunca al total de comandos usados por el código. |

---

## 9. Lista de Verificación Manual para el Usuario (UI)

La versión del plugin publicada en el manifiesto es formalmente la **`1.1.0`**. Las siguientes cuatro comprobaciones manuales de la interfaz se mantienen formalmente en estado **`NO VERIFICADO`** hasta que el usuario las confirme visualmente en su entorno de cliente Antigravity:

| # | Observación a Realizar en la Interfaz | Estado Actual | Criterio de Aceptación |
|---|---|---|---|
| 1 | **Panel de Plugins de Antigravity:** Verificar que `arma3-sqf-review` no muestra advertencias de carga ni errores (versión visible `1.1.0`). | **NO VERIFICADO** | Sin banderas rojas ni avisos; versión 1.1.0 activa. |
| 2 | **Carga de Skill:** Confirmar que la skill carga y que su Paso 3 describe la consulta prioritaria a la réplica local `a3ref`. | **NO VERIFICADO** | Texto normativo actualizado visible en el prompt de la skill. |
| 3 | **Carga de Subagentes:** Confirmar que `sqf-claim-verifier` y `sqf-locality-auditor` reflejan la réplica local como fuente documental primaria. | **NO VERIFICADO** | Subagentes activos con instrucciones locales. |
| 4 | **Revisión de Comando Moderno:** Ejecutar revisión de un script con `playSoundUI` y verificar que emite `[SUGERENCIA]` Biki sin bloquear la entrega. | **NO VERIFICADO** | Sugerencia informativa sin bloqueo. |
