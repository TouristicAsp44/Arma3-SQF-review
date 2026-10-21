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
from collections.abc import Callable

from sqf_models import (
    SQFFinding,
    check_escalation_needed,
    check_escalation_needed_for_files,
    determine_escalation_reason,
    format_findings_report,
    parse_sqflint_output,
    summarize_escalation,
)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Ruta relativa al propio script. Una ruta absoluta a una maquina concreta hacia que
# el plugin no arranque en ningun otro equipo, y hacia que el linter se reporte
# como "no disponible" aunque este perfectamente instalado.
DEFAULT_LINTER = os.path.normpath(
    os.path.join(SCRIPT_DIR, "..", "references", "run_sqflint.py")
)


def default_mock_agent(prompt: str) -> str:
    """Mock agent. SOLO para dry-run: NUNCA debe usarse como agente real.

    Devuelve codigo deliberadamente trivial para que el dry-run ejercite el linter
    y la maquina de estados. El dry-run SIEMPRE termina en NO VERIFICADO.
    """
    return f"/* Código simulado en respuesta a: {prompt[:30]}... */\npublicVariableServer 'P_Var';"


def read_input_code(path: str | None) -> str | None:
    if not path:
        return None
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _resolve_orchestrator_paths(
    work_dir: str | None,
    state_file: str | None,
    failed_file: str | None,
    notes_file: str | None,
    archived_notes_dir: str | None,
    linter_executable: str | None,
) -> tuple[str, str, str, str, str, str]:
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
    return (
        resolved_work_dir,
        resolved_state_file,
        resolved_failed_file,
        resolved_notes_file,
        resolved_archived_notes_dir,
        resolved_linter,
    )


def _load_or_create_state(
    resolved_state_file: str,
    continuar: bool,
    input_code: str | None,
    input_root: str | None,
    mode: str | None,
    dry_run: bool,
) -> tuple[dict | None, int | None]:
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
            return None, 1

    explicit_mode = (mode is not None)
    initial_mode = mode if explicit_mode else "Micro"

    if state_exists:
        with open(resolved_state_file, "r", encoding="utf-8") as f:
            state = json.load(f)
    else:
        initial_code = input_code if input_code is not None else "/* sqf code initial */"
        state = {
            "iteration": 1,
            "code": initial_code,
            "findings": [],
            "context": f"ARCHIVOS ANALIZADOS: {input_root}" if input_root else "",
            "mode": initial_mode,
            "explicit_mode": explicit_mode,
            "input_root": input_root,
            "dry_run": dry_run,
        }

        if not explicit_mode and input_root and os.path.isdir(input_root):
            sqf_files: dict[str, str] = {}
            for r_dir, _, f_names in os.walk(input_root):
                for f_name in sorted(f_names):
                    if f_name.lower().endswith(".sqf"):
                        full_p = os.path.join(r_dir, f_name)
                        try:
                            with open(full_p, "r", encoding="utf-8", errors="replace") as sqf_f:
                                sqf_files[full_p] = sqf_f.read()
                        except OSError:
                            pass
            if sqf_files:
                escalated_mode = check_escalation_needed_for_files(sqf_files, state["mode"])
                if escalated_mode != state["mode"]:
                    print(f"Escalamiento multi-archivo detectado: Modo cambiado de {state['mode']} a {escalated_mode}.")
                    state["mode"] = escalated_mode

    return state, None


def _archive_revision_notes(
    resolved_notes_file: str,
    resolved_archived_notes_dir: str,
    state: dict,
) -> None:
    if not os.path.exists(resolved_notes_file):
        return
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


def _run_linter_on_code(
    code: str,
    resolved_linter: str,
    resolved_work_dir: str,
    iteration: int,
    timeout: int,
) -> tuple[int, str]:
    temp_filename = f"_temp_orchestrator_{os.getpid()}_{iteration}.sqf"
    temp_sqf_path = os.path.abspath(os.path.join(resolved_work_dir, temp_filename))

    try:
        with open(temp_sqf_path, "w", encoding="utf-8") as tf:
            tf.write(code)

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
                check=False,
            )
            return proc.returncode, proc.stdout
        except subprocess.TimeoutExpired:
            return 3, "TIMEOUT EXPIRED: El linter superó el tiempo límite."
    finally:
        if os.path.exists(temp_sqf_path):
            try:
                os.remove(temp_sqf_path)
            except OSError:
                pass


def _process_iteration_results(
    findings_objs: list,
    state: dict,
    iteration: int,
    max_iterations: int,
    resolved_state_file: str,
    resolved_failed_file: str,
    dry_run: bool,
) -> int:
    state["findings"] = [f.model_dump() for f in findings_objs]
    blockers = [f for f in findings_objs if f.severity == "BLOQUEANTE"]
    unverified = [f for f in findings_objs if f.severity == "NO_VERIFICADO"]

    def _cleanup_state():
        if os.path.exists(resolved_state_file):
            try:
                os.remove(resolved_state_file)
            except OSError:
                pass

    if blockers:
        if iteration >= max_iterations:
            print(f"ERROR T09: Se alcanzó el límite de {max_iterations} iteraciones con hallazgos bloqueantes.")
            state["status"] = "FALLIDO"
            with open(resolved_failed_file, "w", encoding="utf-8") as ff:
                json.dump(state, ff, indent=2)
            _cleanup_state()
            return 1

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

    if unverified:
        print("completado con NO VERIFICADO")
        _cleanup_state()
        return 10

    if dry_run:
        print("Dry-run completado. NO VERIFICADO: no se ejecuto ningun agente real.")
        _cleanup_state()
        return 10

    print("Auditoría limpia. Éxito.")
    _cleanup_state()
    return 0


def run_orchestrator(
    state_file: str | None = None,
    failed_file: str | None = None,
    notes_file: str | None = None,
    archived_notes_dir: str | None = None,
    linter_executable: str | None = None,
    agent_func: Callable[[str], str] | None = None,
    work_dir: str | None = None,
    continuar: bool = False,
    max_iterations: int = 3,
    timeout: int = 30,
    input_code: str | None = None,
    input_root: str | None = None,
    dry_run: bool = False,
    input_file: str | None = None,
    mode: str | None = None,
) -> int:
    if input_file and not input_code:
        input_code = read_input_code(input_file)

    (
        resolved_work_dir,
        resolved_state_file,
        resolved_failed_file,
        resolved_notes_file,
        resolved_archived_notes_dir,
        resolved_linter,
    ) = _resolve_orchestrator_paths(
        work_dir,
        state_file,
        failed_file,
        notes_file,
        archived_notes_dir,
        linter_executable,
    )

    resolved_agent_func: Callable[[str], str]
    if agent_func is None:
        if not dry_run:
            raise ValueError(
                "Falta el agente real. run_orchestrator exige agent_func: sin el, el "
                "orquestador auditaria su propio mock y declararia 'Auditoria limpia' "
                "sin haber mirado codigo. Para una simulacion usa dry_run=True, cuyo "
                "resultado es siempre NO VERIFICADO."
            )
        resolved_agent_func = default_mock_agent
    else:
        resolved_agent_func = agent_func

    state, error_code = _load_or_create_state(
        resolved_state_file,
        continuar,
        input_code,
        input_root,
        mode,
        dry_run,
    )
    if error_code is not None or state is None:
        return error_code if error_code is not None else 1

    iteration = state.get("iteration", 1)

    if continuar:
        _archive_revision_notes(resolved_notes_file, resolved_archived_notes_dir, state)

    print(f"--- Iniciando Iteración {iteration} (Modo: {state.get('mode', 'Micro')}) ---")

    prompt = (
        f"Iteración {iteration}.\n"
        f"Contexto acumulado:\n{state.get('context', '')}\n"
        f"Código previo:\n{state.get('code', '')}\n"
        f"Hallazgos previos:\n{json.dumps(state.get('findings', []))}"
    )
    if dry_run:
        print(f"[ORCHESTRATOR] Prompt de iteración {iteration}:\n{prompt}")
    new_code = resolved_agent_func(prompt)
    state["code"] = new_code

    current_mode = state.get("mode", "Micro")
    if not state.get("explicit_mode", False):
        new_mode = check_escalation_needed(new_code, current_mode)
        escalated = (new_mode != current_mode)
        if escalated:
            print(f"Escalamiento detectado: Modo cambiado de {current_mode} a {new_mode}.")
        state["mode"] = new_mode
        state["escalated"] = escalated
    else:
        state["escalated"] = False

    rc, stdout = _run_linter_on_code(
        new_code,
        resolved_linter,
        resolved_work_dir,
        iteration,
        timeout,
    )

    try:
        findings_objs = parse_sqflint_output(rc, stdout)
    except ValueError as e:
        print(f"ERROR FATAL DEL LINTER: {e}", file=sys.stderr)
        return 2

    return _process_iteration_results(
        findings_objs,
        state,
        iteration,
        max_iterations,
        resolved_state_file,
        resolved_failed_file,
        dry_run,
    )


def mode_query(root: str | None = None) -> int:
    resolved_root = os.path.abspath(root) if root else os.getcwd()
    if not os.path.exists(resolved_root):
        print(f"ERROR: La ruta '{resolved_root}' no existe.", file=sys.stderr)
        return 1

    sqf_files: dict[str, str] = {}
    if os.path.isdir(resolved_root):
        for r_dir, _, f_names in os.walk(resolved_root):
            for f_name in sorted(f_names):
                if f_name.lower().endswith(".sqf"):
                    full_p = os.path.join(r_dir, f_name)
                    try:
                        with open(full_p, "r", encoding="utf-8", errors="replace") as sqf_f:
                            sqf_files[full_p] = sqf_f.read()
                    except OSError:
                        pass
    elif resolved_root.lower().endswith(".sqf"):
        try:
            with open(resolved_root, "r", encoding="utf-8", errors="replace") as sqf_f:
                sqf_files[resolved_root] = sqf_f.read()
        except OSError:
            pass

    try:
        mode = check_escalation_needed_for_files(sqf_files, "Micro")
    except ValueError as exc:
        print("ESTADO: NO VERIFICADO")
        print(str(exc))
        print("No se decide ningun modo. Revisa la ruta de --root: el modo mas permisivo")
        print("no se concede por defecto ante un inventario vacio.")
        return 10

    reason = determine_escalation_reason(sqf_files, mode)
    print(summarize_escalation(mode, reason))
    return 0


def run_lint(
    target: str | None = None,
    linter_executable: str | None = None,
    mode: str | None = None,
    timeout: int = 30,
) -> int:
    resolved_target = os.path.abspath(target) if target else os.getcwd()
    if not os.path.exists(resolved_target):
        print(f"ERROR: La ruta '{resolved_target}' no existe.", file=sys.stderr)
        return 1

    if os.path.isdir(resolved_target):
        has_sqf = False
        for _, _, f_names in os.walk(resolved_target):
            if any(f.lower().endswith(".sqf") for f in f_names):
                has_sqf = True
                break
        if not has_sqf:
            print("[NO_VERIFICADO] 0: (Sistema): no se encontraron archivos .sqf; el analisis no se ejecuto")
            print("RESUMEN: bloqueantes=0; sugerencias=0; no_verificado=1")
            print("ESTADO: NO VERIFICADO")
            return 10

    resolved_linter = (
        os.path.abspath(str(linter_executable))
        if linter_executable
        else DEFAULT_LINTER
    )
    if not os.path.exists(resolved_linter):
        finding = SQFFinding(
            severity="NO_VERIFICADO",
            file=resolved_target,
            line=0,
            description="Linter no disponible (SQFLINT_NO_DISPONIBLE)",
            evidence=f"No se encontró el ejecutable: {resolved_linter}",
            discipline="Sintaxis",
        )
        report = format_findings_report([finding])
        print(report)
        print("Estado: NO VERIFICADO (el linter no está disponible)")
        return 10

    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    cmd = [sys.executable, "-B", resolved_linter, resolved_target]
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
            check=False,
        )
        rc = proc.returncode
        stdout = proc.stdout
    except subprocess.TimeoutExpired:
        rc = 3
        stdout = "TIMEOUT EXPIRED: El linter superó el tiempo límite."
    except (subprocess.SubprocessError, OSError) as e:
        rc = 3
        stdout = f"SQFLINT_NO_DISPONIBLE: error al invocar linter ({e})"

    findings = parse_sqflint_output(rc, stdout)
    report = format_findings_report(findings)
    print(report)

    if any(f.severity == "NO_VERIFICADO" for f in findings) or rc == 3 or "SQFLINT_NO_DISPONIBLE" in stdout:
        print("Estado: NO VERIFICADO (el linter no está disponible)")
        return 10

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
    parser.add_argument("--input", dest="input_code", default=None,
                        help="Ruta a un .sqf a auditar. Si se omite, el orquestador no tiene codigo de partida.")
    parser.add_argument("--root", dest="input_root", default=None,
                        help="Carpeta del proyecto a auditar (inventario de archivos .sqf).")
    parser.add_argument("--dry-run", action="store_true",
                        help="Simulacion con el agente mock. SIEMPRE termina en NO VERIFICADO (exit 10).")
    parser.add_argument("--mode-query", action="store_true",
                        help="Consulta el modo correspondiente al proyecto según el inventario de archivos.")
    parser.add_argument("--lint", action="store_true",
                        help="Ejecuta análisis estático y produce el informe estructurado de hallazgos.")
    parser.add_argument("--mode", type=str, choices=["Micro", "Estándar", "Completo"], default=None,
                        help="Modo explícito de ejecución (evita re-escalado automático).")
    parser.add_argument("files", nargs="*", help="Archivos o rutas adicionales.")

    args = parser.parse_args()

    if args.mode_query and args.lint:
        print("ERROR: --mode-query y --lint son mutuamente excluyentes.", file=sys.stderr)
        sys.exit(1)

    if args.mode_query:
        target_root = args.input_root or (args.files[0] if args.files else ".")
        sys.exit(mode_query(root=target_root))

    if args.lint:
        target = args.input_root or args.input_code or (args.files[0] if args.files else ".")
        sys.exit(run_lint(target=target, linter_executable=args.linter, mode=args.mode))

    try:
        code = run_orchestrator(
            state_file=args.state_file,
            notes_file=args.notes_file,
            archived_notes_dir=args.archived_notes_dir,
            linter_executable=args.linter,
            work_dir=args.work_dir,
            continuar=args.continuar,
            max_iterations=args.max_iterations,
            input_code=read_input_code(args.input_code),
            input_root=args.input_root,
            dry_run=args.dry_run,
            mode=args.mode,
        )
        sys.exit(code)
    except (FileNotFoundError, ValueError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
