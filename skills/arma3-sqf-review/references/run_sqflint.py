#!/usr/bin/env python3
"""
Envoltorio multiplataforma determinista para sqflint (Windows y Linux).
Uso: python run_sqflint.py <archivo.sqf | directorio>

Códigos de salida:
  0: SIN ERRORES (análisis completado sin errores de sintaxis)
  1: ERRORES (se detectaron errores de sintaxis en uno o más archivos)
  2: Error de argumentos o ruta no encontrada
  3: SQFLINT_NO_DISPONIBLE (el linter no está instalado ni accesible)
"""
import sys
import os
import glob
import re
import shutil
import subprocess
import site


def locate_sqflint():
    """
    Localiza el ejecutable de sqflint en el sistema siguiendo una cascada multiplataforma:
    1. PATH del sistema (shutil.which).
    2. Carpetas Scripts / bin del usuario (APPDATA, site.getuserbase(), sys.prefix).
    3. Módulo python ejecutable (python -m sqflint).
    Retorna una lista con el comando base o None si no está disponible.
    """
    # 1. Búsqueda directa en PATH
    exe = shutil.which("sqflint")
    if exe:
        return [exe]
    if sys.platform == "win32":
        exe = shutil.which("sqflint.exe")
        if exe:
            return [exe]

    # 2. Búsqueda en rutas de usuario y prefijos del intérprete
    candidates = []
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA", "")
        if appdata:
            candidates.extend(glob.glob(os.path.join(appdata, "Python", "Python*", "Scripts", "sqflint.exe")))
            candidates.extend(glob.glob(os.path.join(appdata, "Python", "Python*", "Scripts", "sqflint.EXE")))
        localappdata = os.environ.get("LOCALAPPDATA", "")
        if localappdata:
            candidates.extend(glob.glob(os.path.join(localappdata, "Programs", "Python", "Python*", "Scripts", "sqflint.exe")))
            candidates.extend(glob.glob(os.path.join(localappdata, "Programs", "Python", "Python*", "Scripts", "sqflint.EXE")))
        try:
            user_base = site.getuserbase()
            if user_base:
                candidates.append(os.path.join(user_base, "Scripts", "sqflint.exe"))
                candidates.append(os.path.join(user_base, "Scripts", "sqflint.EXE"))
        except Exception:
            pass
        candidates.append(os.path.join(sys.prefix, "Scripts", "sqflint.exe"))
        candidates.append(os.path.join(sys.prefix, "Scripts", "sqflint.EXE"))
    else:
        try:
            user_base = site.getuserbase()
            if user_base:
                candidates.append(os.path.join(user_base, "bin", "sqflint"))
        except Exception:
            pass
        candidates.append(os.path.expanduser("~/.local/bin/sqflint"))
        candidates.append(os.path.join(sys.prefix, "bin", "sqflint"))
        candidates.append("/usr/local/bin/sqflint")
        candidates.append("/usr/bin/sqflint")

    for path in candidates:
        if os.path.isfile(path):
            is_executable = (sys.platform == "win32") or os.access(path, os.X_OK)
            if is_executable:
                return [path]

    # 3. Fallback a invocación por módulo: python -m sqflint
    try:
        res = subprocess.run(
            [sys.executable, "-m", "sqflint", "--help"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5
        )
        if res.returncode == 0:
            return [sys.executable, "-m", "sqflint"]
    except Exception:
        pass

    return None


def parse_error_line(file_path, line):
    """
    Parsea una línea de salida de sqflint con formato [line,col]:error:msg o [line,col]:warning:msg
    y la formatea como archivo:línea: nivel: mensaje.
    """
    m = re.match(r"^\[(\d+),\s*(\d+)\]:(?:(error|warning):)?(.*)$", line, re.IGNORECASE)
    if m:
        line_num = m.group(1)
        col_num = m.group(2)
        level = (m.group(3) or "error").lower()
        msg = m.group(4).strip()
        return f"{file_path}:{line_num}: {level}: {msg}"
    if re.match(r"^(.*?):(\d+):\s*(error|warning):\s*(.*)$", line, re.IGNORECASE):
        return line
    return f"{file_path}:{line}"


def main(argv=None):
    # Asegurar codificación UTF-8 en salida estándar
    if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    args = sys.argv[1:] if argv is None else argv
    if len(args) < 1:
        print("Uso: python run_sqflint.py <archivo.sqf | directorio>")
        return 1

    target = args[0]
    if not os.path.exists(target):
        print(f"ERROR: La ruta '{target}' no existe.")
        sys.exit(2)

    sqflint_cmd = locate_sqflint()
    if not sqflint_cmd:
        print("SQFLINT_NO_DISPONIBLE (instala con: pip install sqflint, o preinstálalo fuera del sandbox)")
        sys.exit(3)

    files = []
    if os.path.isdir(target):
        for root, _, filenames in os.walk(target):
            for f in sorted(filenames):
                if f.lower().endswith(".sqf"):
                    files.append(os.path.join(root, f))
        files.sort()
    else:
        files.append(target)

    if not files:
        # exit 0 aqui se traduciria en "PASA" en el bloque A.1 del checklist de entrega,
        # sin haber analizado una sola linea. Se usa el codigo 3 (NO DISPONIBLE) para
        # que el consumidor lo reporte como NO VERIFICADO, nunca como PASA.
        print(f"ESTADO: NO SE ENCONTRARON ARCHIVOS .sqf EN '{target}'")
        print("El analisis no se ejecuto. Reportar como NO VERIFICADO, nunca como PASA.")
        sys.exit(3)

    total_with_errors = 0
    total_files = len(files)
    detailed_results = []
    error_lines = []

    for f in files:
        # La bandera '-e e' fuerza código de salida 1 cuando sqflint encuentra errores sintácticos
        cmd = sqflint_cmd + ["-e", "e", f]
        try:
            res = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace"
            )
            output = res.stdout.strip()
            rc = res.returncode
        except Exception as ex:
            output = f"Excepción al ejecutar sqflint: {ex}"
            rc = 1

        file_lines = []
        if output:
            for line in output.splitlines():
                line = line.strip()
                if not line:
                    continue
                file_lines.append(line)
                normalized = parse_error_line(f, line)
                file_lines[-1] = normalized
                if re.search(r":\s*error:", normalized, re.IGNORECASE) or re.search(r":\s*warning:", normalized, re.IGNORECASE):
                    error_lines.append(normalized)

        has_error = (rc != 0) or any(re.search(r":\s*error:", l, re.IGNORECASE) for l in file_lines)
        if has_error:
            total_with_errors += 1
            status_tag = f"ERRORES (exit {rc})"
            if not file_lines and rc != 0:
                error_lines.append(f"{f}: Error de sintaxis desconocido (exit {rc})")
        else:
            status_tag = "OK"

        detailed_results.append((f, status_tag, file_lines))

    if total_with_errors == 0:
        print("ESTADO: SIN ERRORES")
        print(f"Total archivos analizados: {total_files}")
        for f, status_tag, lines in detailed_results:
            print(f"== {f} ({status_tag}) ==")
            for l in lines:
                print(f"  {l}")
        # Las advertencias se listan aparte para que el consumidor no las confunda con "sin problemas".
        warnings_only = [e for e in error_lines if re.search(r":\s*warning:", e, re.IGNORECASE)]
        if warnings_only:
            print(f"\n--- ADVERTENCIAS (archivo:línea) ---")
            for w in warnings_only:
                print(f"  {w}")
        print(f"ARCHIVOS_CON_PROBLEMAS=0 DE {total_files} (advertencias: {len(warnings_only)})")
        sys.exit(0)
    else:
        print("ESTADO: ERRORES")
        print(f"ARCHIVOS_CON_PROBLEMAS={total_with_errors} DE {total_files}")
        print("\n--- DETALLE DE ERRORES (archivo:línea) ---")
        for err in error_lines:
            print(f"  {err}")
        print("\n--- DESGLOSE POR ARCHIVO ---")
        for f, status_tag, lines in detailed_results:
            print(f"== {f} ({status_tag}) ==")
            for l in lines:
                print(f"  {l}")
        sys.exit(1)


if __name__ == "__main__":
    main()
