"""
Orquestador de ejecución SQF para Arma 3.

Etapa 3 (R2): Bucle de validación interactiva, linter como subprocess, y
archivo de notas. Todo anclado al directorio de trabajo experimental.
"""

import argparse
import datetime
import json
import os
import shutil
import subprocess
import sys
from typing import Callable, Optional

from sqf_models import check_escalation_needed, parse_sqflint_output

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_LINTER = r"C:\Users\Touri\.gemini\config\skills\arma3-sqf-review\references\run_sqflint.py"

def default_mock_agent(prompt: str) -> str:
    """Mock agent simulado por defecto para inyección sin dependencias reales."""
    return f"/* Código simulado en respuesta a: {prompt[:30]}... */\npublicVariableServer 'P_Var';"


def run_orchestrator(
    state_file: Optional[str] = None,
    failed_file: Optional[str] = None,
    notes_file: Optional[str] = None,
    archived_notes_dir: Optional[str] = None,
    linter_executable: Optional[str] = None,
    agent_func: Optional[Callable[[str], str]] = None,
    work_dir: Optional[str] = None,
    continuar: bool = False,
    max_iterations: int = 3,
    timeout: int = 30,
) -> int:
    resolved_work_dir = os.path.abspath(str(work_dir)) if work_dir else SCRIPT_DIR
    resolved_state_file = (
        os.path.abspath(str(state_file))
        if state_file
        else os.path.join(resolved_work_dir, "orchestrator_state.json")
    )

    if failed_file is None:
        s_dir, s_base = os.path.split(resolved_state_file)
        s_name, s_ext = os.path.splitext(s_base)
        resolved_failed_file = os.path.join(s_dir, f"{s_name}.fallido{s_ext or '.json'}")
    else:
        resolved_failed_file = os.path.abspath(str(failed_file))

    resolved_notes_file = (
        os.path.abspath(str(notes_file))
        if notes_file
        else os.path.join(resolved_work_dir, "notas_revision.txt")
    )
    resolved_archived_notes_dir = (
        os.path.abspath(str(archived_notes_dir))
        if archived_notes_dir
        else os.path.join(resolved_work_dir, "archived_notes")
    )
    resolved_linter = (
        os.path.abspath(str(linter_executable))
        if linter_executable
        else DEFAULT_LINTER
    )
    resolved_agent_func = agent_func or default_mock_agent

    state_exists = os.path.exists(resolved_state_file)

    if continuar:
        if not state_exists:
            raise FileNotFoundError(f"Estado no encontrado para --continuar: {resolved_state_file}")
    else:
        if state_exists:
            print(
                f"ERROR: Estado previo existe en {resolved_state_file}. Usa --continuar para retomar o borra el archivo.",
                file=sys.stderr,
            )
            return 1

    if state_exists:
        with open(resolved_state_file, "r", encoding="utf-8") as f:
            state = json.load(f)
    else:
        state = {
            "iteration": 1,
            "code": "/* sqf code initial */",
            "findings": [],
            "context": "",
            "mode": "Micro",
        }

    iteration = state.get("iteration", 1)

    if continuar and os.path.exists(resolved_notes_file):
        with open(resolved_notes_file, "r", encoding="utf-8") as nf:
            notes_content = nf.read()
        current_context = state.get("context", "")
        if current_context:
            state["context"] = f"{current_context}\nNotas de revisión:\n{notes_content}".strip()
        else:
            state["context"] = f"Notas de revisión:\n{notes_content}".strip()
        print(f"--- LEYENDO NOTAS ---\n{notes_content}\n---------------------")

        os.makedirs(resolved_archived_notes_dir, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        archived_path = os.path.join(resolved_archived_notes_dir, f"notas_revision_{timestamp}.txt")
        shutil.move(resolved_notes_file, archived_path)
        print(f"Notas archivadas en {archived_path}.")

    print(f"--- Iniciando Iteración {iteration} (Modo: {state.get('mode', 'Micro')}) ---")

    prompt = (
        f"Iteración {iteration}.\n"
        f"Contexto acumulado:\n{state.get('context', '')}\n"
        f"Código previo:\n{state.get('code', '')}\n"
        f"Hallazgos previos:\n{json.dumps(state.get('findings', []))}"
    )
    new_code = resolved_agent_func(prompt)
    state["code"] = new_code

    current_mode = state.get("mode", "Micro")
    new_mode = check_escalation_needed(new_code, current_mode)
    escalated = (new_mode != current_mode)
    if escalated:
        print(f"Escalamiento detectado: Modo cambiado de {current_mode} a {new_mode}.")
    state["mode"] = new_mode
    state["escalated"] = escalated

    temp_filename = f"_temp_orchestrator_{os.getpid()}_{iteration}.sqf"
    temp_sqf_path = os.path.abspath(os.path.join(resolved_work_dir, temp_filename))

    try:
        with open(temp_sqf_path, "w", encoding="utf-8") as tf:
            tf.write(new_code)

        env = os.environ.copy()
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        cmd = [sys.executable, "-B", resolved_linter, temp_sqf_path]
        try:
            proc = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
                timeout=timeout,
            )
            rc = proc.returncode
            stdout = proc.stdout
        except subprocess.TimeoutExpired:
            rc = 3
            stdout = "TIMEOUT EXPIRED: El linter superó el tiempo límite."
    finally:
        if os.path.exists(temp_sqf_path):
            try:
                os.remove(temp_sqf_path)
            except OSError:
                pass

    try:
        findings_objs = parse_sqflint_output(rc, stdout)
    except ValueError as e:
        print(f"ERROR FATAL DEL LINTER: {e}", file=sys.stderr)
        return 2

    state["findings"] = [f.model_dump() for f in findings_objs]

    blockers = [f for f in findings_objs if f.severity == "BLOQUEANTE"]
    unverified = [f for f in findings_objs if f.severity == "NO_VERIFICADO"]

    if blockers:
        if iteration >= max_iterations:
            print(f"ERROR T09: Se alcanzó el límite de {max_iterations} iteraciones con hallazgos bloqueantes.")
            with open(resolved_failed_file, "w", encoding="utf-8") as ff:
                json.dump(state, ff, indent=2)
            if os.path.exists(resolved_state_file):
                try:
                    os.remove(resolved_state_file)
                except OSError:
                    pass
            return 1
        else:
            state["iteration"] = iteration + 1
            with open(resolved_state_file, "w", encoding="utf-8") as sf:
                json.dump(state, sf, indent=2)
            print(
                f"Hallazgos BLOQUEANTES encontrados ({len(blockers)}). "
                f"Estado guardado para iteración {state['iteration']}/{max_iterations}."
            )
            print(
                f"Para el intento {state['iteration']}/{max_iterations}, puedes escribir notas y ejecutar con --continuar."
            )
            return 0
    elif unverified:
        print("completado con NO VERIFICADO")
        if os.path.exists(resolved_state_file):
            try:
                os.remove(resolved_state_file)
            except OSError:
                pass
        return 10
    else:
        print("Auditoría limpia. Éxito.")
        if os.path.exists(resolved_state_file):
            try:
                os.remove(resolved_state_file)
            except OSError:
                pass
        return 0


def main():
    parser = argparse.ArgumentParser(description="Orquestador SQF Antigravity")
    parser.add_argument("--continuar", action="store_true", help="Continuar sesión previa")
    parser.add_argument("--state-file", type=str, default=None, help="Ruta al archivo de estado")
    parser.add_argument("--notes-file", type=str, default=None, help="Ruta al archivo de notas de revisión")
    parser.add_argument("--archived-notes-dir", type=str, default=None, help="Directorio para notas archivadas")
    parser.add_argument("--linter", type=str, default=None, help="Ruta al ejecutable del linter")
    parser.add_argument("--work-dir", type=str, default=None, help="Directorio de trabajo")
    parser.add_argument("--max-iterations", type=int, default=3, help="Límite máximo de iteraciones")

    args = parser.parse_args()
    try:
        code = run_orchestrator(
            state_file=args.state_file,
            notes_file=args.notes_file,
            archived_notes_dir=args.archived_notes_dir,
            linter_executable=args.linter,
            work_dir=args.work_dir,
            continuar=args.continuar,
            max_iterations=args.max_iterations,
        )
        sys.exit(code)
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
