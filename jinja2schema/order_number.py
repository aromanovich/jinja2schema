# coding: utf-8
"""
jinja2schema.order_number
~~~~~~~~~~~~~~~~~~
"""
from contextlib import contextmanager


class OrderNumber(object):
    """A base Order Number class.

    .. attribute:: number

        Initial counter value.

    .. attribute:: enabled

        Counter enabled or return None.

    """

    def __init__(self, number=0, enabled=False, sub_counter_enabled=True):
        self.start = number
        self.number = self.start
        self.order_enabled = enabled
        self.sub_counter_enabled = sub_counter_enabled

    def get_next(self):
        if self.order_enabled:
            self.number += 1
            return self.number
        return None

    @contextmanager
    def sub_counter(self):
        if self.sub_counter_enabled:
            counter = self.number
            self.number = self.start
            yield
            self.number = counter
            return
        yield
