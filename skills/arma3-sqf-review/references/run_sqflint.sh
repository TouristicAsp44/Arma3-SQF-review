#!/usr/bin/env bash
# ==============================================================================
# OBSOLETO: Reemplazado por 'references/run_sqflint.py' para soporte multiplataforma.
# Motivo de obsolescencia: Este script requiere un entorno bash nativo, fallando en
# entornos Windows nativos. run_sqflint.py provee compatibilidad multiplataforma
# (Windows y Linux), localización determinista de sqflint en PATH / Scripts de usuario,
# y códigos de salida estrictos (0: SIN ERRORES, 1: ERRORES, 3: NO DISPONIBLE).
# ==============================================================================
# Envoltorio de compatibilidad hacia run_sqflint.py:
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if command -v python3 >/dev/null 2>&1; then
    exec python3 "$DIR/run_sqflint.py" "$@"
elif command -v python >/dev/null 2>&1; then
    exec python "$DIR/run_sqflint.py" "$@"
else
    echo "SQFLINT_NO_DISPONIBLE (Python no encontrado para ejecutar run_sqflint.py)"
    exit 3
fi
