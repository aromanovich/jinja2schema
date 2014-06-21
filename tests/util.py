from jinja2schema.model import Dictionary, List, Tuple


def assert_rtypes_equal(a, b):
    assert_structures_equal(a, b, check_linenos=False)


def assert_structures_equal(a, b, check_required=True, check_linenos=True):
    assert type(a) is type(b)
    assert a.constant == b.constant
    assert a.used_with_default == b.used_with_default
    assert not check_required or a.required == b.required
    assert not check_linenos or a.linenos == b.linenos

    if isinstance(a, Dictionary):
        assert set(a.keys()) == set(b.keys())
        for key in a.keys():
            assert_structures_equal(a[key], b[key],
                                    check_required=check_required,
                                    check_linenos=check_linenos)
    elif isinstance(a, List):
        assert_structures_equal(a.el_struct, b.el_struct,
                                check_required=check_required,
                                check_linenos=check_linenos)
    elif isinstance(a, Tuple):
        assert len(a.el_structs) == len(b.el_structs)
        for a_el, b_el in zip(a.el_structs, b.el_structs):
            assert_structures_equal(a_el, b_el,
                                    check_required=check_required,
                                    check_linenos=check_linenos)