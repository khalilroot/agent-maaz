from __future__ import annotations

import pytest


def test_basic_arithmetic():
    from apps.tools.calculator import safe_eval
    assert safe_eval("2+2") == 4
    assert safe_eval("2+2*3") == 8
    assert safe_eval("(2+3)*4") == 20
    assert safe_eval("100-50") == 50
    assert safe_eval("2**10") == 1024


def test_floats_and_division():
    from apps.tools.calculator import safe_eval
    assert safe_eval("10/4") == 2.5
    assert safe_eval("10//3") == 3
    assert safe_eval("7%3") == 1
    assert safe_eval("0.1+0.2") == pytest.approx(0.3, abs=1e-9)


def test_constants():
    from apps.tools.calculator import safe_eval
    assert safe_eval("pi") == pytest.approx(3.141592653589793)
    assert safe_eval("e") == pytest.approx(2.718281828459045)
    assert safe_eval("2*pi") == pytest.approx(6.283185307179586)


def test_functions():
    from apps.tools.calculator import safe_eval
    assert safe_eval("sqrt(16)") == 4.0
    assert safe_eval("cos(0)") == 1.0
    assert safe_eval("sin(0)") == 0.0
    assert safe_eval("log10(1000)") == 3.0
    assert safe_eval("log(e)") == pytest.approx(1.0)
    assert safe_eval("abs(-5)") == 5


def test_unary():
    from apps.tools.calculator import safe_eval
    assert safe_eval("-5") == -5
    assert safe_eval("+5") == 5
    assert safe_eval("--5") == 5


def test_compound():
    from apps.tools.calculator import safe_eval
    assert safe_eval("sqrt(2)+cos(0)") == pytest.approx(2.414213562373095)
    assert safe_eval("2*pi + sqrt(4)") == pytest.approx(8.283185307179586)


def test_tuples_and_lists():
    from apps.tools.calculator import safe_eval
    assert safe_eval("(1, 2, 3)") == (1, 2, 3)
    assert safe_eval("[1, 2, 3]") == [1, 2, 3]


def test_rejects_unsafe_calls():
    from apps.tools.calculator import safe_eval, CalculatorError
    with pytest.raises(CalculatorError):
        safe_eval("__import__('os').system('echo pwned')")
    with pytest.raises(CalculatorError):
        safe_eval("print('hi')")


def test_rejects_invalid_syntax():
    from apps.tools.calculator import safe_eval, CalculatorError
    with pytest.raises(CalculatorError):
        safe_eval("")


def test_rejects_unknown_name():
    from apps.tools.calculator import safe_eval, CalculatorError
    with pytest.raises(CalculatorError):
        safe_eval("evil_func(1)")


def test_keyword_args_rejected():
    from apps.tools.calculator import safe_eval, CalculatorError
    with pytest.raises(CalculatorError):
        safe_eval("round(x=5)")


def test_routes_to_router():
    """The router.execute_tool dispatches calculator correctly."""
    from apps.core import router
    import json
    out = router.execute_tool("calculator", {"expression": "2+3*4"})
    parsed = json.loads(out)
    assert parsed["result"] == "14"
    bad_expr = ""
    out_err = router.execute_tool("calculator", {"expression": bad_expr})
    parsed_err = json.loads(out_err)
    assert "error" in parsed_err


def test_time_tool_dispatches():
    from apps.core import router
    import json
    out = router.execute_tool("get_current_time", {"timezone": "UTC"})
    parsed = json.loads(out)
    assert "iso" in parsed
    assert "unix" in parsed
    assert parsed["timezone"] == "UTC"
