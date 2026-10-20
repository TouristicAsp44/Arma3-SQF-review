import re
from typing import Literal
from pydantic import BaseModel

class SQFFinding(BaseModel):
    severity: Literal["BLOQUEANTE", "SUGERENCIA", "NO_VERIFICADO"]
    file: str
    line: int
    description: str
    evidence: str
    discipline: str

# Advertencias de scope de sqflint: "Local variable \"_x\" is not from this scope (not private)"
# El linter las reporta como warning, no como error, asi que con rc==0 el codigo previously
# las descartaba. SKILL.md declara esa misma categoria como BLOQUEANTE (P0), de modo que
# el mapeo se hace por patron estable y no por texto libre.
SCOPE_WARNING_RE = re.compile(
    r"not from this scope|not private|is not defined but was used",
    re.IGNORECASE,
)


def parse_sqflint_output(rc: int, stdout: str) -> list[SQFFinding]:
    if rc == 2:
        raise ValueError(f"Error de uso de sqflint (rc=2): {stdout.strip()}")
    # NOTA: ya no hay retorno temprano para rc == 0. Un rc == 0 significa "sin errores de
    # sintaxis", no "sin hallazgos": las advertencias de scope siguen siendo hallazgos.

    if "Excepción al ejecutar sqflint" in stdout or "TIMEOUT EXPIRED" in stdout:
        return [SQFFinding(
            severity="NO_VERIFICADO",
            file="desconocido",
            line=0,
            description="El linter fue bloqueado, no se pudo ejecutar o supero el tiempo limite",
            evidence=stdout.strip(),
            discipline="Sistema"
        )]

    findings: list[SQFFinding] = []
    seen: set[tuple[str, int, str]] = set()
    pattern = re.compile(r'^(.*?):(\d+):\s*(error|warning):\s*(.*)$', re.IGNORECASE)
    for line_text in stdout.splitlines():
        match = pattern.match(line_text.strip())
        if match:
            file_path, line_num, level, msg = match.groups()
            key = (file_path, int(line_num), msg)
            if key in seen:
                continue
            seen.add(key)
            is_scope = bool(SCOPE_WARNING_RE.search(msg))
            if level.lower() == "error" or is_scope:
                severity = "BLOQUEANTE"
            else:
                severity = "SUGERENCIA"
            findings.append(SQFFinding(
                severity=severity,
                file=file_path,
                line=int(line_num),
                description=msg,
                evidence=line_text,
                discipline="Scope" if is_scope else "Sintaxis"
            ))

    if not findings and rc not in (0, 1):
        findings.append(SQFFinding(
            severity="NO_VERIFICADO",
            file="desconocido",
            line=0,
            description=f"Fallo del linter o rc desconocido (rc={rc})",
            evidence=stdout,
            discipline="Sintaxis"
        ))
    elif not findings and rc == 1:
        findings.append(SQFFinding(
            severity="BLOQUEANTE",
            file="desconocido",
            line=0,
            description="Error de sintaxis o formato no reconocido del linter (rc=1)",
            evidence=stdout,
            discipline="Sintaxis"
        ))
    return findings


def strip_comments_and_strings(code: str) -> str:
    pattern = r'/\*[\s\S]*?\*/|//.*|"(?:[^"]|"")*"|\'(?:[^\']|\'\')*\''
    return re.sub(pattern, ' ', code)


# Estos dos patrones deben ser IDENTICOS a los de SKILL.md lineas 70 y 72.
# Si divergen, el codigo deja de detectar lo que la skill prohibe en modo Micro.
NETWORK_SIGNALS_RE = re.compile(
    r"\b(remoteExec|remoteExecCall|publicVariable|publicVariableServer|publicVariableClient"
    r"|addPublicVariableEventHandler|remoteExecutedOwner|setOwner|BIS_fnc_MP|isDedicated"
    r"|isServer|hasInterface|HeadlessClient)\b"
    r"|setVariable\s*\[.*true",
    re.IGNORECASE,
)

PERFORMANCE_SIGNALS_RE = re.compile(
    r"\b(while|waitUntil|EachFrame|onEachFrame|Draw3D|allUnits|allGroups|allMissionObjects"
    r"|nearestObjects|nearEntities|createVehicle|createUnit|createGroup|addEventHandler"
    r"|addMissionEventHandler|spawn|execVM)\b",
    re.IGNORECASE,
)

LIFECYCLE_SIGNALS_RE = re.compile(
    r"init\.sqf|initServer\.sqf|initPlayerLocal\.sqf|initPlayerServer\.sqf"
    r"|description\.ext|config\.cpp|CfgRemoteExec|CfgFunctions",
    re.IGNORECASE,
)


def check_escalation_needed(raw_code: str, current_mode: str) -> str:
    """Escala fuera de Micro si el codigo cumple CUALQUIER criterio de exclusion de SKILL.md."""
    if current_mode != "Micro":
        return current_mode
    clean_code = strip_comments_and_strings(raw_code)
    if (NETWORK_SIGNALS_RE.search(clean_code)
            or PERFORMANCE_SIGNALS_RE.search(clean_code)
            or LIFECYCLE_SIGNALS_RE.search(clean_code)):
        return "Estándar"
    return current_mode


def check_escalation_needed_for_files(files: dict[str, str] | list[Any], current_mode: str) -> str:
    """Variante multi-archivo: el modo Micro exige un UNICO archivo autocontenido."""
    if current_mode != "Micro":
        return current_mode
    if len(files) > 1:
        return "Estándar"
    if isinstance(files, dict):
        for raw in files.values():
            if check_escalation_needed(raw, current_mode) != "Micro":
                return "Estándar"
    else:
        for f in files:
            from pathlib import Path
            p = Path(f)
            raw = p.read_text(encoding="utf-8", errors="replace") if p.is_file() else str(f)
            if check_escalation_needed(raw, current_mode) != "Micro":
                return "Estándar"
    return current_mode


def determine_escalation_reason(files: dict[str, str] | list[Any], mode: str) -> str:
    """Determina la causa exacta del escalado o de la permanencia en Micro."""
    if len(files) > 1:
        return f"Proyecto multi-archivo ({len(files)} archivos .sqf)"
    
    code = ""
    if isinstance(files, dict) and files:
        code = next(iter(files.values()))
    elif isinstance(files, list) and files:
        from pathlib import Path
        p = Path(files[0])
        code = p.read_text(encoding="utf-8", errors="replace") if p.is_file() else str(files[0])
    
    clean = strip_comments_and_strings(code)
    if NETWORK_SIGNALS_RE.search(clean):
        return "Señales de red / MP detectadas"
    if PERFORMANCE_SIGNALS_RE.search(clean):
        return "Señales de scheduler / rendimiento detectadas"
    if LIFECYCLE_SIGNALS_RE.search(clean):
        return "Scripts de ciclo de vida / configuración detectados"
    
    if mode == "Micro":
        return "Archivo único autocontenido sin señales de red ni scheduler"
    return "Configuración manual o modo previo preservado"


def format_findings_report(findings: list[SQFFinding]) -> str:
    """Produce el informe de hallazgos estructurado de una línea por hallazgo más RESUMEN."""
    lines: list[str] = []
    bloqueantes = 0
    sugerencias = 0
    no_verificado = 0

    for f in findings:
        lines.append(f"[{f.severity}] {f.file}:{f.line} ({f.discipline}): {f.description}")
        if f.severity == "BLOQUEANTE":
            bloqueantes += 1
        elif f.severity == "SUGERENCIA":
            sugerencias += 1
        elif f.severity == "NO_VERIFICADO":
            no_verificado += 1

    lines.append(f"RESUMEN: bloqueantes={bloqueantes}; sugerencias={sugerencias}; no_verificado={no_verificado}")
    return "\n".join(lines)


def summarize_escalation(mode: str, reason: str = "") -> str:
    """Produce el informe estructurado del resultado de triage / escalado de modo."""
    lines: list[str] = [f"MODO: {mode}"]
    if reason:
        lines.append(f"MOTIVO: {reason}")
    escalado = "si" if mode != "Micro" else "no"
    lines.append(f"RESUMEN: modo={mode}; escalado={escalado}")
    return "\n".join(lines)
