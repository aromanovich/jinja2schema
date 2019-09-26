# coding: utf-8
from jinja2schema.order_number import OrderNumber


def test_get_next_order_number():
    on = OrderNumber(1, enabled=True)
    assert on.get_next() == 2
    on = OrderNumber(1)
    assert on.get_next() is None
    on = OrderNumber(5, enabled=True)
    assert on.get_next() == 6


def test_sub_counter_1():
    on = OrderNumber(1, enabled=True)
    on.get_next()
    assert on.get_next() == 3
    with on.sub_counter():
        assert on.get_next() == 2
    assert on.get_next() == 4


def test_sub_counter_2():
    on = OrderNumber(12, enabled=True)
    on.get_next()
    assert on.get_next() == 14
    with on.sub_counter():
        assert on.get_next() == 13
    assert on.get_next() == 15
