import re
from pydantic import BaseModel
from typing import Literal

class SQFFinding(BaseModel):
    severity: Literal["BLOQUEANTE", "SUGERENCIA", "NO_VERIFICADO"]
    file: str
    line: int
    description: str
    evidence: str
    discipline: str

def parse_sqflint_output(rc: int, stdout: str) -> list[SQFFinding]:
    if rc == 0:
        return []
    if rc == 2:
        raise ValueError(f"Error de uso de sqflint (rc=2): {stdout.strip()}")

    if rc == 1:
        if "Excepción al ejecutar sqflint" in stdout:
            return [SQFFinding(
                severity="NO_VERIFICADO",
                file="desconocido",
                line=0,
                description="El linter fue bloqueado por el sistema o no se pudo ejecutar",
                evidence=stdout.strip(),
                discipline="Sistema"
            )]

        findings: list[SQFFinding] = []
        pattern = re.compile(r'^(.*?):(\d+):\s*(error|warning):\s*(.*)$', re.IGNORECASE)
        for line_text in stdout.splitlines():
            match = pattern.match(line_text.strip())
            if match:
                file_path, line_num, level, msg = match.groups()
                severity = "BLOQUEANTE" if level.lower() == "error" else "SUGERENCIA"
                findings.append(SQFFinding(
                    severity=severity,
                    file=file_path,
                    line=int(line_num),
                    description=msg,
                    evidence=line_text,
                    discipline="Sintaxis"
                ))
        if not findings:
            findings.append(SQFFinding(
                severity="BLOQUEANTE",
                file="desconocido",
                line=0,
                description="Error de sintaxis o formato no reconocido del linter (rc=1)",
                evidence=stdout,
                discipline="Sintaxis"
            ))
        return findings

    return [SQFFinding(
        severity="NO_VERIFICADO",
        file="desconocido",
        line=0,
        description=f"Fallo del linter o rc desconocido (rc={rc})",
        evidence=stdout,
        discipline="Sintaxis"
    )]


def strip_comments_and_strings(code: str) -> str:
    pattern = r'/\*[\s\S]*?\*/|//.*|"(?:[^"]|"")*"|\'(?:[^\']|\'\')*\''
    # Reemplazar con ESPACIO
    return re.sub(pattern, ' ', code)

def check_escalation_needed(raw_code: str, current_mode: str) -> str:
    if current_mode != "Micro": return current_mode
    clean_code = strip_comments_and_strings(raw_code)
    network_pattern = re.compile(r'\b(remoteExec|remoteExecCall|publicVariable|publicVariableServer|publicVariableClient)\b', re.IGNORECASE)
    if network_pattern.search(clean_code):
         return "Estándar"
    return current_mode
