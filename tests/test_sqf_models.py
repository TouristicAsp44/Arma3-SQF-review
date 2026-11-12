from dataclasses import is_dataclass
from pathlib import Path

import pytest
from sqf_models import (
    SQFFinding,
    ScopeStatus,
    check_escalation_needed,
    check_escalation_needed_for_files,
    evaluate_token_scope,
)


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


def test_sqffinding_is_dataclass_and_serializable():
    """Demuestra que SQFFinding es un dataclass puro, soporta model_dump y ScopeStatus opera según diseño."""
    finding = SQFFinding(
        severity="BLOQUEANTE",
        file="test.sqf",
        line=10,
        description="Error de prueba",
        evidence="bad code",
        discipline="Scope",
    )
    assert is_dataclass(finding)
    dumped = finding.model_dump()
    assert isinstance(dumped, dict)
    assert dumped["severity"] == "BLOQUEANTE"
    assert dumped["file"] == "test.sqf"
    assert dumped["line"] == 10
    assert dumped["discipline"] == "Scope"

    # Verificación de ScopeStatus y evaluate_token_scope
    assert ScopeStatus.MIXED.value == "MIXED"
    assert evaluate_token_scope("cmd", "") == ScopeStatus.INDETERMINATE
    assert evaluate_token_scope("cmd", "cmd [0,0,0];") == ScopeStatus.NOT_LOCAL
    assert evaluate_token_scope("_loc", "private _loc = 1; _x = _loc;") == ScopeStatus.LOCAL
    assert evaluate_token_scope("cmd", "private cmd = 1; cmd [0,0,0];") == ScopeStatus.MIXED


def test_item_9_does_not_count_local_variables_as_absent():
    """Demuestra que el Ítem 9 no contabiliza variables locales como ausentes (D1)."""
    from sqf_orchestrator import compute_item_9_report

    source_code = (
        "private _resultado = 42;\n"
        "_pos = getPos player;\n"
        'playSoundUI "test";\n'
        'simboloInexistente123 "arg";\n'
    )
    stdout = (
        'test.sqf:3: error: can\'t interpret statement (missing ;?): <Variable(playSoundUI)> <String("test")>\n'
        'test.sqf:4: error: can\'t interpret statement (missing ;?): <Variable(simboloInexistente123)> <String("arg")>\n'
    )
    f1 = SQFFinding(
        severity="SUGERENCIA",
        file="test.sqf",
        line=3,
        description="Comando oficial válido según Biki: playSoundUI",
        evidence='<Variable(playSoundUI)> <String("test")>',
        discipline="Biki",
    )
    f2 = SQFFinding(
        severity="BLOQUEANTE",
        file="test.sqf",
        line=4,
        description="error: can't interpret statement (missing ;?): <Variable(simboloInexistente123)>",
        evidence='<Variable(simboloInexistente123)> <String("arg")>',
        discipline="Sintaxis",
    )
    report = compute_item_9_report(findings=[f1, f2], rc=1, stdout=stdout, source_code=source_code)

    assert "_resultado" not in report
    assert "_pos" not in report
    assert "1 ausentes (simboloInexistente123)" in report
    assert "1 bloqueantes asociados" in report


def test_item_9_clean_file_reaches_pasa():
    """Demuestra que un archivo SQF limpio alcanza el estado PASA en el Ítem 9 (Once.3)."""
    from sqf_orchestrator import compute_item_9_report

    source_code = (
        'private _resultado = 42;\n'
        'hint "Operación completada";\n'
        'sleep 5;\n'
    )
    stdout = "test.sqf:0: info: SIN ERRORES"
    report = compute_item_9_report(findings=[], rc=0, stdout=stdout, source_code=source_code)

    assert "PASA" in report
    assert "0 ausentes" in report
    assert "0 bloqueantes asociados" in report


def test_blocker_association_short_token_no_contamination():
    """Demuestra que la asociación de bloqueantes por token corto no contamina identificadores mayores (D7)."""
    from sqf_orchestrator import compute_item_9_report

    stdout = 'test.sqf:1: error: can\'t interpret statement: <Variable(pos)> <Number(10)>\n'
    f_pos = SQFFinding(
        severity="BLOQUEANTE",
        file="test.sqf",
        line=1,
        description="error de sintaxis en comando setPos con argumento erróneo",
        evidence="player setPos [0,0,0];",
        discipline="Sintaxis",
    )
    report = compute_item_9_report(findings=[f_pos], rc=1, stdout=stdout, source_code="")

    assert "1 ausentes (pos)" in report
    assert "0 bloqueantes asociados" in report


def test_sibling_module_import_from_plugin_root():
    """Demuestra que la importación de módulos hermanos funciona con sys.path configurado (D10)."""
    import sys
    plugin_root = Path(__file__).resolve().parent.parent
    scripts_dir = plugin_root / "skills" / "arma3-sqf-review" / "scripts"
    assert str(scripts_dir) in sys.path or any(str(scripts_dir) in p for p in sys.path)
    import sqf_wiki_reader
    import sqf_models
    assert hasattr(sqf_wiki_reader, "lookup_syntax_symbol")
    assert hasattr(sqf_models, "parse_sqflint_output")

