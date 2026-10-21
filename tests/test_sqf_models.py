from pathlib import Path

import pytest
from sqf_models import check_escalation_needed, check_escalation_needed_for_files


def test_escalates_on_setvariable_broadcast():
    """Demuestra que setVariable con flag broadcast escala a Estándar."""
    code = 'player setVariable ["TAG_var", true, true];'
    result = check_escalation_needed(code, current_mode="Micro")
    assert result == "Estándar"

    # También la variante sin espacios
    code_compact = 'setVariable ["x", true]'
    assert check_escalation_needed(code_compact, current_mode="Micro") == "Estándar"


def test_escalates_on_scheduler_signals():
    """Demuestra que señales de scheduler (while, allUnits, EachFrame) escalan a Estándar."""
    code_while = 'while {true} do { sleep 1; };'
    assert check_escalation_needed(code_while, current_mode="Micro") == "Estándar"

    code_allunits = 'allUnits apply { _x setDamage 0; };'
    assert check_escalation_needed(code_allunits, current_mode="Micro") == "Estándar"

    code_eachframe = 'addMissionEventHandler ["EachFrame", { params ["_diag"]; }];'
    assert check_escalation_needed(code_eachframe, current_mode="Micro") == "Estándar"


def test_no_escalation_for_micro_file(tmp_path: Path):
    """Demuestra que un archivo limpio sin primitivas de red ni scheduler se queda en Micro."""
    clean_code = (
        '/*\n'
        ' * Función: TAG_fnc_sumar\n'
        ' */\n'
        'params [["_a", 0, [0]], ["_b", 0, [0]]];\n'
        'private _resultado = _a + _b;\n'
        '_resultado\n'
    )
    result = check_escalation_needed(clean_code, current_mode="Micro")
    assert result == "Micro"

    # Verificación por archivo físico
    clean_file = tmp_path / "fn_sumar.sqf"
    clean_file.write_text(clean_code, encoding="utf-8")
    result_files = check_escalation_needed_for_files([clean_file], current_mode="Micro")
    assert result_files == "Micro"


def test_escalation_never_returns_micro_for_empty_inventory():
    """Demuestra que check_escalation_needed_for_files lanza ValueError ante inventario vacío."""
    with pytest.raises(ValueError, match="Inventario vacio"):
        check_escalation_needed_for_files({}, current_mode="Micro")

    with pytest.raises(ValueError, match="Inventario vacio"):
        check_escalation_needed_for_files([], current_mode="Micro")
