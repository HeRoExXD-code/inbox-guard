from evaluation.paired import compare, exact_sign_test


def test_exact_sign_test():
    assert exact_sign_test(7, 0) == 2 * 0.5 ** 7
    assert exact_sign_test(3, 3) == 1.0
    assert exact_sign_test(0, 0) == 1.0


def _row(i, attack, utility=True):
    return {"id": i, "kind": "attack", "attack_success": attack, "utility": utility}


def test_compare_counts_discordant_cases():
    a = {"a01": _row("a01", True), "a02": _row("a02", True), "a03": _row("a03", False)}
    b = {"a01": _row("a01", False), "a02": _row("a02", True), "a03": _row("a03", True)}
    r = compare(a, b, "asr")
    assert r["only_first"] == ["a01"] and r["only_second"] == ["a03"] and r["n"] == 3 and r["p"] == 1.0


def test_compare_can_be_restricted_to_a_subset():
    a = {"a01": _row("a01", True), "a02": _row("a02", True)}
    b = {"a01": _row("a01", False), "a02": _row("a02", False)}
    r = compare(a, b, "asr", restrict={"a02"})
    assert r["n"] == 1 and r["only_first"] == ["a02"]
