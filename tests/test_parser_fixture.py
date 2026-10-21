from sqf_models import parse_sqflint_output


def test_scope_warning_is_bloqueante():
    """Demuestra que una advertencia de scope se clasifica como BLOQUEANTE."""
    stdout = 'scripts/fn_test.sqf:12: warning: Local variable "_x" is not from this scope (not private)'
    findings = parse_sqflint_output(rc=0, stdout=stdout)

    assert len(findings) == 1
    f = findings[0]
    assert f.severity == "BLOQUEANTE"
    assert f.line == 12
    assert "not from this scope" in f.description or "not private" in f.description


def test_rc0_keeps_warnings():
    """Demuestra que con rc == 0 las advertencias no se descartan."""
    stdout = 'scripts/fn_test.sqf:25: warning: Tab character used instead of spaces'
    findings = parse_sqflint_output(rc=0, stdout=stdout)

    assert len(findings) == 1
    f = findings[0]
    assert f.severity == "SUGERENCIA"
    assert f.line == 25
    assert "Tab character" in f.description
