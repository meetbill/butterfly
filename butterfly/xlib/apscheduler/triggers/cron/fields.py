"""Fields represent CronTrigger options which map to :class:`~datetime.datetime` fields."""

from calendar import monthrange
import re

from xlib.util import six

from xlib.apscheduler.triggers.cron.expressions import (
    AllExpression, RangeExpression, WeekdayPositionExpression, LastDayOfMonthExpression,
    WeekdayRangeExpression, MonthRangeExpression)


__all__ = ('MIN_VALUES', 'MAX_VALUES', 'DEFAULT_VALUES', 'BaseField', 'WeekField',
           'DayOfMonthField', 'DayOfWeekField')


MIN_VALUES = {'year': 1970, 'month': 1, 'day': 1, 'week': 1, 'day_of_week': 0, 'hour': 0,
              'minute': 0, 'second': 0}
MAX_VALUES = {'year': 9999, 'month': 12, 'day': 31, 'week': 53, 'day_of_week': 6, 'hour': 23,
              'minute': 59, 'second': 59}
DEFAULT_VALUES = {'year': '*', 'month': 1, 'day': 1, 'week': '*', 'day_of_week': '*', 'hour': 0,
                  'minute': 0, 'second': 0}
SEPARATOR = re.compile(' *, *')


class BaseField(object):
    """
    Base field class
    """
    REAL = True
    COMPILERS = [AllExpression, RangeExpression]

    def __init__(self, name, exprs, is_default=False):
        self.name = name
        self.is_default = is_default
        self.compile_expressions(exprs)

    def get_min(self, dateval):
        """
        Get min
        """
        return MIN_VALUES[self.name]

    def get_max(self, dateval):
        """
        Get max
        """
        return MAX_VALUES[self.name]

    def get_value(self, dateval):
        """
        Get value
        """
        return getattr(dateval, self.name)

    def get_next_value(self, dateval):
        """
        Get next value
        """
        smallest = None
        for expr in self.expressions:
            value = expr.get_next_value(dateval, self)
            if smallest is None or (value is not None and value < smallest):
                smallest = value

        return smallest

    def compile_expressions(self, exprs):
        """
        Compile expressions
        """
        self.expressions = []

        # Split a comma-separated expression list, if any
        for expr in SEPARATOR.split(str(exprs).strip()):
            self.compile_expression(expr)

    def compile_expression(self, expr):
        """
        Compile expression
        """
        for compiler in self.COMPILERS:
            match = compiler.value_re.match(expr)
            if match:
                compiled_expr = compiler(**match.groupdict())

                try:
                    compiled_expr.validate_range(self.name)
                except ValueError as e:
                    exc = ValueError('Error validating expression {!r}: {}'.format(expr, e))
                    six.raise_from(exc, None)

                self.expressions.append(compiled_expr)
                return

        raise ValueError('Unrecognized expression "%s" for field "%s"' % (expr, self.name))

    def __eq__(self, other):
        return isinstance(self, self.__class__) and self.expressions == other.expressions

    def __str__(self):
        expr_strings = (str(e) for e in self.expressions)
        return ','.join(expr_strings)

    def __repr__(self):
        return "%s('%s', '%s')" % (self.__class__.__name__, self.name, self)


class WeekField(BaseField):
    """
    Week field
    """
    REAL = False

    def get_value(self, dateval):
        """
        Get value
        """
        return dateval.isocalendar()[1]


class DayOfMonthField(BaseField):
    """
    Month day field class
    """
    COMPILERS = BaseField.COMPILERS + [WeekdayPositionExpression, LastDayOfMonthExpression]

    def get_max(self, dateval):
        """
        Get max
        """
        return monthrange(dateval.year, dateval.month)[1]


class DayOfWeekField(BaseField):
    """
    Week day field class
    """
    REAL = False
    COMPILERS = BaseField.COMPILERS + [WeekdayRangeExpression]

    def get_value(self, dateval):
        """
        Get value
        """
        return dateval.weekday()


class MonthField(BaseField):
    """
    Month field class
    """
    COMPILERS = BaseField.COMPILERS + [MonthRangeExpression]
