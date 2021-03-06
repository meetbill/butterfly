# coding=utf8
"""
# File Name: peewee.py
# Description:
    https://github.com/coleifer/peewee
    doc: http://docs.peewee-orm.com/en/latest/genindex.html

    小巧一点
    remove DatabaseProxy, Proxy
    remove Postgresql, IdentityField(仅 Postgresql 使用)
    remove ManyToManyField, ManyToManyQuery, DeferredThroughModel
    remove SubclassAwareMetadata

    +----------------------------------------------------------
    | SQL Generation
    | AST 抽象语法树（abstract syntax code，AST）
    | BASE QUERY INTERFACE.
    | QUERY IMPLEMENTATIONS.
    | DB-API 2.0 EXCEPTIONS.
    | DATABASE INTERFACE AND CONNECTION MANAGEMENT.
    | TRANSACTION CONTROL.
    | CURSOR REPRESENTATIONS.
    | FIELDS
    | MODELS
    +----------------------------------------------------------
"""
from bisect import bisect_left
from bisect import bisect_right
from contextlib import contextmanager
from copy import deepcopy
from functools import wraps
from inspect import isclass
import calendar
import collections
import datetime
import decimal
import hashlib
import itertools
import logging
import operator
import re
import socket
import struct
import sys
import threading
import time
import uuid
import warnings
try:
    from collections.abc import Mapping
except ImportError:
    from collections import Mapping

try:
    from pysqlite3 import dbapi2 as pysq3
except ImportError:
    try:
        from pysqlite2 import dbapi2 as pysq3
    except ImportError:
        pysq3 = None
try:
    import sqlite3
except ImportError:
    sqlite3 = pysq3
else:
    if pysq3 and pysq3.sqlite_version_info >= sqlite3.sqlite_version_info:
        sqlite3 = pysq3
try:
    from psycopg2cffi import compat
    compat.register()
except ImportError:
    pass
try:
    import psycopg2
    from psycopg2 import extensions as pg_extensions
    try:
        from psycopg2 import errors as pg_errors
    except ImportError:
        pg_errors = None
except ImportError:
    psycopg2 = pg_errors = None

mysql_passwd = False
try:
    import pymysql as mysql
except ImportError:
    try:
        import MySQLdb as mysql
        mysql_passwd = True
    except ImportError:
        mysql = None


__version__ = '3.9.6'
__all__ = [
    'AsIs',
    'AutoField',
    'BareField',
    'BigAutoField',
    'BigBitField',
    'BigIntegerField',
    'BinaryUUIDField',
    'BitField',
    'BlobField',
    'BooleanField',
    'Case',
    'Cast',
    'CharField',
    'Check',
    'chunked',
    'Column',
    'CompositeKey',
    'Context',
    'Database',
    'DatabaseError',
    'DataError',
    'DateField',
    'DateTimeField',
    'DecimalField',
    'DeferredForeignKey',
    'DJANGO_MAP',
    'DoesNotExist',
    'DoubleField',
    'DQ',
    'EXCLUDED',
    'Field',
    'FixedCharField',
    'FloatField',
    'fn',
    'ForeignKeyField',
    'ImproperlyConfigured',
    'Index',
    'IntegerField',
    'IntegrityError',
    'InterfaceError',
    'InternalError',
    'IPField',
    'JOIN',
    'Model',
    'ModelIndex',
    'MySQLDatabase',
    'NotSupportedError',
    'OP',
    'OperationalError',
    'PrimaryKeyField',  # XXX: Deprecated, change to AutoField.
    'prefetch',
    'ProgrammingError',
    'QualifiedNames',
    'SchemaManager',
    'SmallIntegerField',
    'Select',
    'SQL',
    'SqliteDatabase',
    'Table',
    'TextField',
    'TimeField',
    'TimestampField',
    'Tuple',
    'UUIDField',
    'Value',
    'ValuesList',
    'Window',
]


##########################################################
# 该 Handler 实例会忽略 error messages
# 通常被想使用 logging 的 library 开发者使用来避免 'No handlers could be found for logger XXX' 信息的出现
##########################################################
try:  # Python 2.7+
    from logging import NullHandler
except ImportError:
    class NullHandler(logging.Handler):
        """
        NullHandler class
        """

        def emit(self, record):
            pass

logger = logging.getLogger('peewee')
logger.addHandler(NullHandler())


if sys.version_info[0] == 2:
    text_type = unicode
    bytes_type = str
    buffer_type = buffer
    izip_longest = itertools.izip_longest
    callable_ = callable
    exec('def reraise(tp, value, tb=None): raise tp, value, tb')

    def print_(s):
        """
        输出到标准输出函数
        """
        sys.stdout.write(s)
        sys.stdout.write('\n')
else:
    import builtins
    try:
        from collections.abc import Callable
    except ImportError:
        from collections import Callable
    from functools import reduce

    def callable_(c):
        """
        bool
        callable 函数在 python2.x 版本中都可用。但是在 python3.0 版本中被移除，而在 python3.2 以后版本中被重新添加
        """
        return isinstance(c, Callable)
    text_type = str
    bytes_type = bytes
    buffer_type = memoryview
    basestring = str
    long = int
    print_ = getattr(builtins, 'print')
    izip_longest = itertools.zip_longest

    def reraise(tp, value, tb=None):
        """
        re raise
        """
        if value.__traceback__ is not tb:
            raise value.with_traceback(tb)
        raise value


if sqlite3:
    sqlite3.register_adapter(decimal.Decimal, str)
    sqlite3.register_adapter(datetime.date, str)
    sqlite3.register_adapter(datetime.time, str)
    _sqlite_version_ = sqlite3.sqlite_version_info
else:
    _sqlite_version_ = (0, 0, 0)


_date_parts_ = set(('year', 'month', 'day', 'hour', 'minute', 'second'))

# Sqlite does not support the `date_part` SQL function, so we will define an
# implementation in python.
_sqlite_datetime_formats_ = (
    '%Y-%m-%d %H:%M:%S',
    '%Y-%m-%d %H:%M:%S.%f',
    '%Y-%m-%d',
    '%H:%M:%S',
    '%H:%M:%S.%f',
    '%H:%M')

_sqlite_date_trunc_ = {
    'year': '%Y-01-01 00:00:00',
    'month': '%Y-%m-01 00:00:00',
    'day': '%Y-%m-%d 00:00:00',
    'hour': '%Y-%m-%d %H:00:00',
    'minute': '%Y-%m-%d %H:%M:00',
    'second': '%Y-%m-%d %H:%M:%S'}

_mysql_date_trunc_ = _sqlite_date_trunc_.copy()
_mysql_date_trunc_['minute'] = '%Y-%m-%d %H:%i:00'
_mysql_date_trunc_['second'] = '%Y-%m-%d %H:%i:%S'


def _sqlite_date_part(lookup_type, datetime_string):
    assert lookup_type in _date_parts_
    if not datetime_string:
        return
    dt = format_date_time(datetime_string, _sqlite_datetime_formats_)
    return getattr(dt, lookup_type)


def _sqlite_date_trunc(lookup_type, datetime_string):
    assert lookup_type in _sqlite_date_trunc_
    if not datetime_string:
        return
    dt = format_date_time(datetime_string, _sqlite_datetime_formats_)
    return dt.strftime(_sqlite_date_trunc_[lookup_type])


def _deprecated_(s):
    warnings.warn(s, DeprecationWarning)


class AttrDict(dict):
    """
    将字典像属性那样操作
    """
    def __getattr__(self, attr):
        try:
            return self[attr]
        except KeyError:
            raise AttributeError(attr)

    def __setattr__(self, attr, value):
        self[attr] = value

    def __iadd__(self, rhs):
        self.update(rhs)
        return self

    def __add__(self, rhs):
        d = AttrDict(self)
        d.update(rhs)
        return d


SENTINEL = object()

#: Operations for use in SQL expressions.
OP = AttrDict(
    AND='AND',
    OR='OR',
    ADD='+',
    SUB='-',
    MUL='*',
    DIV='/',
    BIN_AND='&',
    BIN_OR='|',
    XOR='#',
    MOD='%',
    EQ='=',
    LT='<',
    LTE='<=',
    GT='>',
    GTE='>=',
    NE='!=',
    IN='IN',
    NOT_IN='NOT IN',
    IS='IS',
    IS_NOT='IS NOT',
    LIKE='LIKE',
    ILIKE='ILIKE',
    BETWEEN='BETWEEN',
    REGEXP='REGEXP',
    IREGEXP='IREGEXP',
    CONCAT='||',
    BITWISE_NEGATION='~')

# To support "django-style" double-underscore filters, create a mapping between
# operation name and operation code, e.g. "__eq" == OP.EQ.
DJANGO_MAP = AttrDict({
    'eq': operator.eq,
    'lt': operator.lt,
    'lte': operator.le,
    'gt': operator.gt,
    'gte': operator.ge,
    'ne': operator.ne,
    'in': operator.lshift,
    'is': lambda l, r: Expression(l, OP.IS, r),
    'like': lambda l, r: Expression(l, OP.LIKE, r),
    'ilike': lambda l, r: Expression(l, OP.ILIKE, r),
    'regexp': lambda l, r: Expression(l, OP.REGEXP, r),
})

#: Mapping of field type to the data-type supported by the database. Databases
#: may override or add to this list.
FIELD = AttrDict(
    AUTO='INTEGER',
    BIGAUTO='BIGINT',
    BIGINT='BIGINT',
    BLOB='BLOB',
    BOOL='SMALLINT',
    CHAR='CHAR',
    DATE='DATE',
    DATETIME='DATETIME',
    DECIMAL='DECIMAL',
    DEFAULT='',
    DOUBLE='REAL',
    FLOAT='REAL',
    INT='INTEGER',
    SMALLINT='SMALLINT',
    TEXT='TEXT',
    TIME='TIME',
    UUID='TEXT',
    UUIDB='BLOB',
    VARCHAR='VARCHAR')

#: Join helpers (for convenience) -- all join types are supported, this object
#: is just to help avoid introducing errors by using strings everywhere.
JOIN = AttrDict(
    INNER='INNER',
    LEFT_OUTER='LEFT OUTER',
    RIGHT_OUTER='RIGHT OUTER',
    FULL='FULL',
    FULL_OUTER='FULL OUTER',
    CROSS='CROSS',
    NATURAL='NATURAL')

# Row representations.
ROW = AttrDict(
    TUPLE=1,
    DICT=2,
    NAMED_TUPLE=3,
    CONSTRUCTOR=4,
    MODEL=5)

SCOPE_NORMAL = 1
SCOPE_SOURCE = 2
SCOPE_VALUES = 4
SCOPE_CTE = 8
SCOPE_COLUMN = 16

# Rules for parentheses around subqueries in compound select.
CSQ_PARENTHESES_NEVER = 0
CSQ_PARENTHESES_ALWAYS = 1
CSQ_PARENTHESES_UNNESTED = 2

# Regular expressions used to convert class names to snake-case table names.
# First regex handles acronym followed by word or initial lower-word followed
# by a capitalized word. e.g. APIResponse -> API_Response / fooBar -> foo_Bar.
# Second regex handles the normal case of two title-cased words.
SNAKE_CASE_STEP1 = re.compile('(.)_*([A-Z][a-z]+)')
SNAKE_CASE_STEP2 = re.compile('([a-z0-9])_*([A-Z])')

# Helper functions that are used in various parts of the codebase.
MODEL_BASE = '_metaclass_helper_'


def with_metaclass(meta, base=None):
    """
    用基类 base 和 metaclass 元类创建一个新类

    Args:
        meta: 元类
        base: 基类(object)
    Returns:
        新类
    """
    if base is None:
        base = object
    return meta(MODEL_BASE, (base,), {})


def merge_dict(source, overrides):
    """
    合并字典

    Args:
        source: dict
        overrides: dict
    Returns:
        dict
    """
    merged = source.copy()
    if overrides:
        merged.update(overrides)
    return merged


def quote(path, quote_chars):
    """
    对引号的处理
    path – Components that make up the dotted-path of the entity name.
    """
    if len(path) == 1:
        return path[0].join(quote_chars)
    return '.'.join([part.join(quote_chars) for part in path])


def is_model(o):
    """
    判断对象是否是个类，同时是否是 Model 的子类

    Args:
        o: {object}
    Returns:
        bool
    """
    return isclass(o) and issubclass(o, Model)


def ensure_tuple(value):
    """
    返回元组
    """
    if value is not None:
        return value if isinstance(value, (list, tuple)) else (value,)


def ensure_entity(value):
    """
    返回 entity 对象
    """
    if value is not None:
        return value if isinstance(value, Node) else Entity(value)


def make_snake_case(s):
    """
    返回蛇形命名法(snake case)名字，即用下划线将小写单词连接
    """
    first = SNAKE_CASE_STEP1.sub(r'\1_\2', s)
    return SNAKE_CASE_STEP2.sub(r'\1_\2', first).lower()


def chunked(it, n):
    """
    分块辅助函数

    Example:
        # 一次插入 100 行.
        with db.atomic():
            for batch in chunked(data, 100):
                Person.insert_many(batch).execute()
    """
    marker = object()
    for group in (list(g) for g in izip_longest(*[iter(it)] * n,
                                                fillvalue=marker)):
        if group[-1] is marker:
            del group[group.index(marker):]
        yield group


class _CallableContextManager(object):
    def __call__(self, fn):
        @wraps(fn)
        def inner(*args, **kwargs):
            """
            inner function
            """
            with self:
                return fn(*args, **kwargs)
        return inner

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

################################################################
# SQL Generation.
################################################################

class AliasManager(object):
    """
    AliasManager
    管理 source 在 SELECT 查询中分配给对象的别名
    """
    __slots__ = ('_counter', '_current_index', '_mapping')

    def __init__(self):
        # A list of dictionaries containing mappings at various depths.
        self._counter = 0
        self._current_index = 0
        self._mapping = []
        self.push()

    @property
    def mapping(self):
        """
        mapping 属性
        """
        return self._mapping[self._current_index - 1]

    def add(self, source):
        """
        add source to self.mapping
        """
        if source not in self.mapping:
            self._counter += 1
            self[source] = 't%d' % self._counter
        return self.mapping[source]

    def get(self, source, any_depth=False):
        """
        返回别名
        """
        if any_depth:
            for idx in reversed(range(self._current_index)):
                if source in self._mapping[idx]:
                    return self._mapping[idx][source]
        return self.add(source)

    def __getitem__(self, source):
        return self.get(source)

    def __setitem__(self, source, alias):
        self.mapping[source] = alias

    def push(self):
        """
        push {} 到 _mapping 列表中
        """
        self._current_index += 1
        if self._current_index > len(self._mapping):
            self._mapping.append({})

    def pop(self):
        """
        设置 _current_index -1
        """
        if self._current_index == 1:
            raise ValueError('Cannot pop() from empty alias manager.')
        self._current_index -= 1


class State(collections.namedtuple('_State', ('scope', 'parentheses', 'settings'))):
    """
    轻量级对象
    """
    def __new__(cls, scope=SCOPE_NORMAL, parentheses=False, **kwargs):
        return super(State, cls).__new__(cls, scope, parentheses, kwargs)

    def __call__(self, scope=None, parentheses=None, **kwargs):
        # Scope and settings are "inherited" (parentheses is not, however).
        scope = self.scope if scope is None else scope

        # Try to avoid unnecessary dict copying.
        if kwargs and self.settings:
            settings = self.settings.copy()  # Copy original settings dict.
            settings.update(kwargs)  # Update copy with overrides.
        elif kwargs:
            settings = kwargs
        else:
            settings = self.settings
        return State(scope, parentheses, **settings)

    def __getattr__(self, attr_name):
        return self.settings.get(attr_name)


def _scope_context_(scope):
    @contextmanager
    def inner(self, **kwargs):
        """
        inner function
        """
        with self(scope=scope, **kwargs):
            yield self
    return inner


class Context(object):
    """
    Converts Peewee structures into parameterized SQL queries.

    Peewee 结构应全部实现 _sql_ 方法，将由 Context 在 SQL 生成期间初始化。
    """
    __slots__ = ('stack', '_sql', '_values', 'alias_manager', 'state')

    def __init__(self, **settings):
        self.stack = []
        self._sql = []
        self._values = []
        self.alias_manager = AliasManager()
        self.state = State(**settings)

    def as_new(self):
        """
        返回新的 Context 对象
        """
        return Context(**self.state.settings)

    def column_sort_key(self, item):
        """
        获取排序的 key
        """
        return item[0].get_sort_key(self)

    @property
    def scope(self):
        """
        Return the currently-active scope rules.
        返回当前活动的作用域规则。
        """
        return self.state.scope

    @property
    def parentheses(self):
        """
        Return whether the current state is wrapped in parentheses.
        返回当前状态是否用括号括起来。
        """
        return self.state.parentheses

    @property
    def subquery(self):
        """
        Return whether the current state is the child of another query.
        返回当前状态是否为其他查询的子级。
        """
        return self.state.subquery

    def __call__(self, **overrides):
        if overrides and overrides.get('scope') == self.scope:
            del overrides['scope']

        self.stack.append(self.state)
        self.state = self.state(**overrides)
        return self

    scope_normal = _scope_context_(SCOPE_NORMAL)
    scope_source = _scope_context_(SCOPE_SOURCE)
    scope_values = _scope_context_(SCOPE_VALUES)
    scope_cte = _scope_context_(SCOPE_CTE)
    scope_column = _scope_context_(SCOPE_COLUMN)

    def __enter__(self):
        if self.parentheses:
            self.literal('(')
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.parentheses:
            self.literal(')')
        self.state = self.stack.pop()

    @contextmanager
    def push_alias(self):
        """
        push alias
        """
        self.alias_manager.push()
        yield
        self.alias_manager.pop()

    def sql(self, obj):
        """
        将可组合节点对象、子上下文或其他对象追加到查询 AST
        """
        if isinstance(obj, (Node, Context)):
            return obj._sql_(self)
        elif is_model(obj):
            return obj._meta.table._sql_(self)
        else:
            return self.sql(Value(obj))

    def literal(self, keyword):
        """
        Append a string-literal to the current query AST.
        将字符串文本附加到当前查询ast。

        Returns:
            The updated Context object.
        """
        self._sql.append(keyword)
        return self

    def value(self, value, converter=None, add_param=True):
        """
        转换 value

        Args:
            value : python 值（如整数、字符串、浮点数等）被视为参数化值。
            converter : 用于将值转换为数据库能理解的类型的函数。
            add_param :
        """
        if converter:
            value = converter(value)
            if isinstance(value, Node):
                return self.sql(value)
        elif converter is None and self.state.converter:
            # Explicitly check for None so that "False" can be used to signify
            # that no conversion should be applied.
            value = self.state.converter(value)

        if isinstance(value, Node):
            with self(converter=None):
                return self.sql(value)

        self._values.append(value)
        return self.literal(self.state.param or '?') if add_param else self

    def _sql_(self, ctx):
        ctx._sql.extend(self._sql)
        ctx._values.extend(self._values)
        return ctx

    def parse(self, node):
        """
        将给定节点转换为 SQL AST 并返回由 SQL 查询和参数组成的 2 元组。

        Args:
            node (Node) – Instance of a Node subclass.
        Returns:
            a 2-tuple consisting of (sql, parameters).
        """
        return self.sql(node).query()

    def query(self):
        """
        Returns:
            a 2-tuple consisting of (sql, parameters) for the context.
        """
        return ''.join(self._sql), self._values


def query_to_string(query):
    """
    # NOTE: this function is not exported by default as it might be misused --
    # and this misuse could lead to sql injection vulnerabilities. This
    # function is intended for debugging or logging purposes ONLY.
    """
    db = getattr(query, '_database', None)
    if db is not None:
        ctx = db.get_sql_context()
    else:
        ctx = Context()

    sql, params = ctx.sql(query).query()
    if not params:
        return sql

    param = ctx.state.param or '?'
    if param == '?':
        sql = sql.replace('?', '%s')

    return sql % tuple(map(_query_val_transform, params))


def _query_val_transform(v):
    # Interpolate parameters.
    if isinstance(v, (text_type, datetime.datetime, datetime.date,
                      datetime.time)):
        v = "'%s'" % v
    elif isinstance(v, bytes_type):
        try:
            v = v.decode('utf8')
        except UnicodeDecodeError:
            v = v.decode('raw_unicode_escape')
        v = "'%s'" % v
    elif isinstance(v, int):
        v = '%s' % int(v)  # Also handles booleans -> 1 or 0.
    elif v is None:
        v = 'NULL'
    else:
        v = str(v)
    return v

################################################################
# AST.
# 抽象语法树（abstract syntax code，AST）
################################################################


class Node(object):
    """
    构成 SQL 查询的 AST 的所有组件的基类。
    """
    _coerce = True

    def clone(self):
        """
        clone
        """
        obj = self.__class__.__new__(self.__class__)
        obj.__dict__ = self.__dict__.copy()
        return obj

    def _sql_(self, ctx):
        raise NotImplementedError

    @staticmethod
    def copy(method):
        """
        修饰器，用于改变节点状态的节点方法。这允许方法链接，例如：
        +------------------------------------------------------
        | query = MyModel.select()
        | new_query = query.where(MyModel.field == 'value')
        +------------------------------------------------------
        """
        def inner(self, *args, **kwargs):
            """
            inner function
            """
            clone = self.clone()
            method(clone, *args, **kwargs)
            return clone
        return inner

    def coerce(self, _coerce=True):
        """
        暂时没有用到
        """
        if _coerce != self._coerce:
            clone = self.clone()
            clone._coerce = _coerce
            return clone
        return self

    def is_alias(self):
        """
        用于确定用户是否已显式地为节点命名的 API
        """
        return False

    def unwrap(self):
        """
        用于递归展开“已包装”节点的API
        """
        return self


class ColumnFactory(object):
    """
    ColumnFactory
    """
    __slots__ = ('node',)

    def __init__(self, node):
        self.node = node

    def __getattr__(self, attr):
        return Column(self.node, attr)


class _DynamicColumn(object):
    __slots__ = ()

    def __get__(self, instance, instance_type=None):
        if instance is not None:
            return ColumnFactory(instance)  # Implements __getattr__().
        return self


class _ExplicitColumn(object):
    __slots__ = ()

    def __get__(self, instance, instance_type=None):
        if instance is not None:
            raise AttributeError(
                '%s specifies columns explicitly, and does not support '
                'dynamic column lookups.' % instance)
        return self


class Source(Node):
    """
    行元组的源，例如表、联接或选择查询。 默认情况下，提供名为“c”的“magic”属性，该属性是列/属性查找的工厂，例如：
    +-----------------------------------------
    |User = Table('users')
    |query = (User
    |     .select(User.c.username)
    |     .where(User.c.active == True)
    |     .order_by(User.c.username))
    +-----------------------------------------
    """
    c = _DynamicColumn()

    def __init__(self, alias=None):
        super(Source, self).__init__()
        self._alias = alias

    @Node.copy
    def alias(self, name):
        """
        返回应用了给定别名的对象的副本。
        """
        self._alias = name

    def select(self, *columns):
        """
        创建一个 Select 查询表。如果表显式声明列，但未提供任何列，则默认情况下，将选择表的所有已定义列。

        Args:
            columns : Column 实例、表达式、函数、子查询或任何您想选择的内容。
        """
        if not columns:
            columns = (SQL('*'),)
        return Select((self,), columns)

    def join(self, dest, join_type='INNER', on=None):
        """
        联接类型

        Args:
            dest (Source) -- 将表与给定的目标联接。
            join_type (str) -- 连接类型。
            on -- 用作联接谓词的表达式。
        Returns:
            Join 实例。
        """
        return Join(self, dest, join_type, on)

    def left_outer_join(self, dest, on=None):
        """
        方便调用方法 join() 使用左外部联接。

        Args:
            dest (Source) -- 将表与给定的目标联接。
            on -- 用作联接谓词的表达式。
        Returns:
            Join 实例。
        """
        return Join(self, dest, JOIN.LEFT_OUTER, on)

    def cte(self, name, recursive=False, columns=None):
        """
        返回表示公用表表达式, 例如查询

        Args:
            name -- CTE 的名称。
            recursive (bool) -- CTE 是否递归。
            columns (list) -- CTE 生成的列的显式列表。
        Returns:
            CTE 对象
        """
        return CTE(name, self, recursive=recursive, columns=columns)

    def get_sort_key(self, ctx):
        """
        返回 _sort_key
        """
        if self._alias:
            return (self._alias,)
        return (ctx.alias_manager[self],)

    def apply_alias(self, ctx):
        """
        # If we are defining the source, include the "AS alias" declaration. An
        # alias is created for the source if one is not already defined.
        """
        if ctx.scope == SCOPE_SOURCE:
            if self._alias:
                ctx.alias_manager[self] = self._alias
            ctx.literal(' AS ').sql(Entity(ctx.alias_manager[self]))
        return ctx

    def apply_column(self, ctx):
        """
        更新上下文对象。
        """
        if self._alias:
            ctx.alias_manager[self] = self._alias
        return ctx.sql(Entity(ctx.alias_manager[self]))


class _HashableSource(object):
    def __init__(self, *args, **kwargs):
        super(_HashableSource, self).__init__(*args, **kwargs)
        self._update_hash()

    @Node.copy
    def alias(self, name):
        """
        更新别名
        """
        self._alias = name
        self._update_hash()

    def _update_hash(self):
        self._hash = self._get_hash()

    def _get_hash(self):
        return hash((self.__class__, self._path, self._alias))

    def __hash__(self):
        return self._hash

    def __eq__(self, other):
        return self._hash == other._hash

    def __ne__(self, other):
        return not (self == other)


def _bind_database_(meth):
    @wraps(meth)
    def inner(self, *args, **kwargs):
        """
        inner function
        """
        result = meth(self, *args, **kwargs)
        if self._database:
            return result.bind(self._database)
        return result
    return inner


def _join_(join_type='INNER', inverted=False):
    def method(self, other):
        """
        Args:
            other: 右侧(rhs)
        """
        if inverted:
            self, other = other, self
        return Join(self, other, join_type=join_type)
    return method


class BaseTable(Source):
    """
    表对象的基类，它支持通过运算符重载进行联接。
    """
    __and__ = _join_(JOIN.INNER)
    __add__ = _join_(JOIN.LEFT_OUTER)
    __sub__ = _join_(JOIN.RIGHT_OUTER)
    __or__ = _join_(JOIN.FULL_OUTER)
    __mul__ = _join_(JOIN.CROSS)
    __rand__ = _join_(JOIN.INNER, inverted=True)
    __radd__ = _join_(JOIN.LEFT_OUTER, inverted=True)
    __rsub__ = _join_(JOIN.RIGHT_OUTER, inverted=True)
    __ror__ = _join_(JOIN.FULL_OUTER, inverted=True)
    __rmul__ = _join_(JOIN.CROSS, inverted=True)


class _BoundTableContext(_CallableContextManager):
    def __init__(self, table, database):
        self.table = table
        self.database = database

    def __enter__(self):
        self._orig_database = self.table._database
        self.table.bind(self.database)
        if self.table._model is not None:
            self.table._model.bind(self.database)
        return self.table

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.table.bind(self._orig_database)
        if self.table._model is not None:
            self.table._model.bind(self._orig_database)


class Table(_HashableSource, BaseTable):
    """
    数据库中的表
    """
    def __init__(self, name, columns=None, primary_key=None, schema=None,
                 alias=None, _model=None, _database=None):
        self.__name__ = name
        self._columns = columns
        self._primary_key = primary_key
        self._schema = schema
        self._path = (schema, name) if schema else (name,)
        self._model = _model
        self._database = _database
        super(Table, self).__init__(alias=alias)

        # Allow tables to restrict what columns are available.
        if columns is not None:
            self.c = _ExplicitColumn()
            for column in columns:
                setattr(self, column, Column(self, column))

        if primary_key:
            col_src = self if self._columns else self.c
            self.primary_key = getattr(col_src, primary_key)
        else:
            self.primary_key = None

    def clone(self):
        """
        # Ensure a deep copy of the column instances.
        """
        return Table(
            self.__name__,
            columns=self._columns,
            primary_key=self._primary_key,
            schema=self._schema,
            alias=self._alias,
            _model=self._model,
            _database=self._database)

    def bind(self, database=None):
        """
        将此表绑定到给定的数据库（或保留为空取消绑定）
        Args:
            database -- Database 对象。
        """
        self._database = database
        return self

    def bind_ctx(self, database=None):
        """
        该管理器将表绑定到所包装块期间的给定数据库。

        Args:
            database -- Database 对象。
        Returns:
            返回一个上下文管理器
        """
        return _BoundTableContext(self, database)

    def _get_hash(self):
        return hash((self.__class__, self._path, self._alias, self._model))

    @_bind_database_
    def select(self, *columns):
        """
        创建一个 Select 查询表。如果表显式声明列，但未提供任何列，则默认情况下，将选择表的所有已定义列。
        Args:
            columns -- Column 实例、表达式、函数、子查询或任何您想选择的内容。
        """
        if not columns and self._columns:
            columns = [Column(self, column) for column in self._columns]
        return Select((self,), columns)

    @_bind_database_
    def insert(self, insert=None, columns=None, **kwargs):
        """
        创建一个 Insert 到表中

        Args:
            insert -- 字典将列映射到值，生成字典（即列表）的iterable，或 Select 查询。
            columns (list) -- 当要插入的数据不是字典时要插入的列的列表。
            kwargs -- 列名称到值的映射。
        Returns:
            Insert 实例
        """
        if kwargs:
            insert = {} if insert is None else insert
            src = self if self._columns else self.c
            for key, value in kwargs.items():
                insert[getattr(src, key)] = value
        return Insert(self, insert=insert, columns=columns)

    @_bind_database_
    def replace(self, insert=None, columns=None, **kwargs):
        """
        创建一个 Insert 查询要替换其冲突解决方法的表。

        Args:
            insert -- 字典将列映射到值，生成字典（即列表）的iterable，或 Select 查询。
            columns (list) -- 当要插入的数据不是字典时要插入的列的列表。
            kwargs -- 列名称到值的映射。
        """
        return (self
                .insert(insert=insert, columns=columns)
                .on_conflict('REPLACE'))

    @_bind_database_
    def update(self, update=None, **kwargs):
        """
        创建一个 Update 查询表

        Args:
            update -- 将列映射到值的字典。
            kwargs -- 列名称到值的映射。
        """
        if kwargs:
            update = {} if update is None else update
            for key, value in kwargs.items():
                src = self if self._columns else self.c
                update[getattr(src, key)] = value
        return Update(self, update=update)

    @_bind_database_
    def delete(self):
        """
        创建一个 Delete 查询表。
        """
        return Delete(self)

    def _sql_(self, ctx):
        if ctx.scope == SCOPE_VALUES:
            # Return the quoted table name.
            return ctx.sql(Entity(*self._path))

        if self._alias:
            ctx.alias_manager[self] = self._alias

        if ctx.scope == SCOPE_SOURCE:
            # Define the table and its alias.
            return self.apply_alias(ctx.sql(Entity(*self._path)))
        else:
            # Refer to the table using the alias.
            return self.apply_column(ctx)


class Join(BaseTable):
    """
    表示到表对象之间的联接。
    """
    def __init__(self, lhs, rhs, join_type=None, on=None, alias=None):
        """
        lhs -- 接头的左侧。
        rhs -- 接头的右侧。
        join_type -- 连接类型。例如，join.inner、join.left_outer等。
        on -- 描述联接谓词的表达式。
        alias (str) -- 应用于联接数据的别名。
        """
        super(Join, self).__init__(alias=alias)
        if join_type is None:
            join_type=JOIN.INNER

        self.lhs = lhs
        self.rhs = rhs
        self.join_type = join_type
        self._on = on

    def on(self, predicate):
        """
        用作联接谓词, 即 self._on

        Args:
            predicate (Expression) -- 连接谓词
        """
        self._on = predicate
        return self

    def _sql_(self, ctx):
        (ctx
         .sql(self.lhs)
         .literal(' %s JOIN ' % self.join_type)
         .sql(self.rhs))
        if self._on is not None:
            ctx.literal(' ON ').sql(self._on)
        return ctx


class ValuesList(_HashableSource, BaseTable):
    """
    表示可以像表一样使用的值列表。

    +---------------------------------------
    | data = [(1, 'first'), (2, 'second')]
    | vl = ValuesList(data, columns=('idx', 'name'))
    | query = (vl.select(vl.c.idx, vl.c.name).order_by(vl.c.idx))
    +---------------------------------------
    """
    def __init__(self, values, columns=None, alias=None):
        self._values = values
        self._columns = columns
        super(ValuesList, self).__init__(alias=alias)

    def _get_hash(self):
        return hash((self.__class__, id(self._values), self._alias))

    @Node.copy
    def columns(self, *names):
        """
        names -- 要应用于数据列的名称。
        """
        self._columns = names

    def _sql_(self, ctx):
        if self._alias:
            ctx.alias_manager[self] = self._alias

        if ctx.scope == SCOPE_SOURCE or ctx.scope == SCOPE_NORMAL:
            with ctx(parentheses=not ctx.parentheses):
                ctx = (ctx
                       .literal('VALUES ')
                       .sql(CommaNodeList([
                           EnclosedNodeList(row) for row in self._values])))

            if ctx.scope == SCOPE_SOURCE:
                ctx.literal(' AS ').sql(Entity(ctx.alias_manager[self]))
                if self._columns:
                    entities = [Entity(c) for c in self._columns]
                    ctx.sql(EnclosedNodeList(entities))
        else:
            ctx.sql(Entity(ctx.alias_manager[self]))

        return ctx


class CTE(_HashableSource, Source):
    """
    表示公用表表达式
    """
    def __init__(self, name, query, recursive=False, columns=None):
        """
        name -- CTE 的名称。
        query -- Select 描述 CTE 的查询。
        recursive (bool) -- CTE 是否递归。
        columns (list) -- CTE 生成的列的显式列表（可选）。
        """
        self._alias = name
        self._query = query
        self._recursive = recursive
        if columns is not None:
            columns = [Entity(c) if isinstance(c, basestring) else c
                       for c in columns]
        self._columns = columns
        query._cte_list = ()
        super(CTE, self).__init__(alias=name)

    def select_from(self, *columns):
        """
        创建一个选择查询，该查询使用给定的公共表表达式作为新查询的源。

        Args:
            columns -- 要从 CTE 中选择的一列或多列。
        Returns:
            Select 使用公用表表达式的查询
        """
        if not columns:
            raise ValueError('select_from() must specify one or more columns '
                             'from the CTE to select.')

        query = (Select((self,), columns)
                 .with_cte(self)
                 .bind(self._query._database))
        try:
            query = query.objects(self._query.model)
        except AttributeError:
            pass
        return query

    def _get_hash(self):
        return hash((self.__class__, self._alias, id(self._query)))

    def union_all(self, rhs):
        """
        用于构造 CTE 的递归项。

        Args:
            rhs: 递归项，通常为 Select 查询。
        Returns:
            递归的 CTE 使用给定的递归项。
        """
        clone = self._query.clone()
        return CTE(self._alias, clone + rhs, self._recursive, self._columns)
    __add__ = union_all

    def _sql_(self, ctx):
        if ctx.scope != SCOPE_CTE:
            return ctx.sql(Entity(self._alias))

        with ctx.push_alias():
            ctx.alias_manager[self] = self._alias
            ctx.sql(Entity(self._alias))

            if self._columns:
                ctx.literal(' ').sql(EnclosedNodeList(self._columns))
            ctx.literal(' AS ')
            with ctx.scope_normal(parentheses=True):
                ctx.sql(self._query)
        return ctx


class ColumnBase(Node):
    """
    列、属性或表达式的基类。
    """
    def alias(self, alias):
        """
        指示应为指定的列的对象提供的别名。

        Args:
            alias (str) -- 给定的列对象的别名。
        Returns:
            Alias 对象。
        """
        if alias:
            return Alias(self, alias)
        return self

    def unalias(self):
        """
        返回自身
        """
        return self

    def cast(self, as_type):
        """
        创建一个 CAST 表达式。

        Args:
            as_type (str) -- 要强制转换到的类型名。
        Returns:
            Cast 对象。
        """
        return Cast(self, as_type)

    def asc(self, collation=None, nulls=None):
        """
        Args:
            collation (str) -- 用于排序的排序规则名称。
            nulls (str) -- 对空值排序（第一个或最后一个）。
        Returns:
            上升的 Ordering 列的对象。
        """
        return Asc(self, collation=collation, nulls=nulls)
    __pos__ = asc

    def desc(self, collation=None, nulls=None):
        """
        Args:
            collation (str) -- 用于排序的排序规则名称。
            nulls (str) -- 对空值排序（第一个或最后一个）。
        Returns:
            降序 Ordering 列的对象。
        """
        return Desc(self, collation=collation, nulls=nulls)
    __neg__ = desc

    def __invert__(self):
        return Negated(self)

    def _e(op, inv=False):
        """
        Lightweight factory which returns a method that builds an Expression
        consisting of the left-hand and right-hand operands, using `op`.
        """

        def inner(self, rhs):
            """
            inner function
            """
            if inv:
                return Expression(rhs, op, self)
            return Expression(self, op, rhs)
        return inner

    __and__ = _e(OP.AND)
    __or__ = _e(OP.OR)

    __add__ = _e(OP.ADD)
    __sub__ = _e(OP.SUB)
    __mul__ = _e(OP.MUL)
    __div__ = __truediv__ = _e(OP.DIV)
    __xor__ = _e(OP.XOR)
    __radd__ = _e(OP.ADD, inv=True)
    __rsub__ = _e(OP.SUB, inv=True)
    __rmul__ = _e(OP.MUL, inv=True)
    __rdiv__ = __rtruediv__ = _e(OP.DIV, inv=True)
    __rand__ = _e(OP.AND, inv=True)
    __ror__ = _e(OP.OR, inv=True)
    __rxor__ = _e(OP.XOR, inv=True)

    def __eq__(self, rhs):
        op = OP.IS if rhs is None else OP.EQ
        return Expression(self, op, rhs)

    def __ne__(self, rhs):
        op = OP.IS_NOT if rhs is None else OP.NE
        return Expression(self, op, rhs)

    __lt__ = _e(OP.LT)
    __le__ = _e(OP.LTE)
    __gt__ = _e(OP.GT)
    __ge__ = _e(OP.GTE)
    __lshift__ = _e(OP.IN)
    __rshift__ = _e(OP.IS)
    __mod__ = _e(OP.LIKE)
    __pow__ = _e(OP.ILIKE)

    bin_and = _e(OP.BIN_AND)
    bin_or = _e(OP.BIN_OR)
    in_ = _e(OP.IN)
    not_in = _e(OP.NOT_IN)
    regexp = _e(OP.REGEXP)

    # Special expressions.
    def is_null(self, is_null=True):
        """
        True/False
        """
        op = OP.IS if is_null else OP.IS_NOT
        return Expression(self, op, None)

    def contains(self, rhs):
        """
        LIKE %s%
        """
        return Expression(self, OP.ILIKE, '%%%s%%' % rhs)

    def startswith(self, rhs):
        """
        LIKE s%
        """
        return Expression(self, OP.ILIKE, '%s%%' % rhs)

    def endswith(self, rhs):
        """
        LIKE %s
        """
        return Expression(self, OP.ILIKE, '%%%s' % rhs)

    def between(self, lo, hi):
        """
        BETWEEN low AND high

        Args:
            lo : low
            hi : high
        """
        return Expression(self, OP.BETWEEN, NodeList((lo, SQL('AND'), hi)))

    def concat(self, rhs):
        """
        ||
        """
        return StringExpression(self, OP.CONCAT, rhs)

    def iregexp(self, rhs):
        """
        IREGEXP
        """
        return Expression(self, OP.IREGEXP, rhs)

    def __getitem__(self, item):
        if isinstance(item, slice):
            if item.start is None or item.stop is None:
                raise ValueError('BETWEEN range must have both a start- and '
                                 'end-point.')
            return self.between(item.start, item.stop)
        return self == item

    def distinct(self):
        """
        DISTINCT 一般是用来去除查询结果中的重复记录的
        """
        return NodeList((SQL('DISTINCT'), self))

    def collate(self, collation):
        """
        COLLATE 会影响到 ORDER BY 语句的顺序
        """
        return NodeList((self, SQL('COLLATE %s' % collation)))

    def get_sort_key(self, ctx):
        """
        返回 _sort_key
        """
        return ()


class Column(ColumnBase):
    """
    表中的列或子查询返回的列。
    """
    def __init__(self, source, name):
        """
        source (Source) -- 列的源。
        name (str) -- 列名。
        """
        self.source = source
        self.name = name

    def get_sort_key(self, ctx):
        """
        返回 _sort_key
        """
        if ctx.scope == SCOPE_VALUES:
            return (self.name,)
        else:
            return self.source.get_sort_key(ctx) + (self.name,)

    def __hash__(self):
        return hash((self.source, self.name))

    def _sql_(self, ctx):
        if ctx.scope == SCOPE_VALUES:
            return ctx.sql(Entity(self.name))
        else:
            with ctx.scope_column():
                return ctx.sql(self.source).literal('.').sql(Entity(self.name))


class WrappedNode(ColumnBase):
    """
    封装 Node
    """
    def __init__(self, node):
        self.node = node
        self._coerce = getattr(node, '_coerce', True)

    def is_alias(self):
        """
        返回 True/False
        """
        return self.node.is_alias()

    def unwrap(self):
        """
        用于递归展开“已包装”节点的 API。基本情况返回自我。
        """
        return self.node.unwrap()


class EntityFactory(object):
    """
    Entity Factory
    """
    __slots__ = ('node',)

    def __init__(self, node):
        self.node = node

    def __getattr__(self, attr):
        return Entity(self.node, attr)


class _DynamicEntity(object):
    __slots__ = ()

    def __get__(self, instance, instance_type=None):
        if instance is not None:
            return EntityFactory(instance._alias)  # Implements __getattr__().
        return self


class Alias(WrappedNode):
    """
    为给定的列对象创建一个命名别名。
    """
    c = _DynamicEntity()

    def __init__(self, node, alias):
        super(Alias, self).__init__(node)
        self._alias = alias

    def alias(self, alias=None):
        """
        返回别名
        """
        if alias is None:
            return self.node
        else:
            return Alias(self.node, alias)

    def unalias(self):
        """
        返回自己
        """
        return self.node

    def is_alias(self):
        """
        用于确定用户是否已显式地为节点命名的 API。
        """
        return True

    def _sql_(self, ctx):
        if ctx.scope == SCOPE_SOURCE:
            return (ctx
                    .sql(self.node)
                    .literal(' AS ')
                    .sql(Entity(self._alias)))
        else:
            return ctx.sql(Entity(self._alias))


class Negated(WrappedNode):
    """
    Represents a negated column-like object.
    """
    def __invert__(self):
        return self.node

    def _sql_(self, ctx):
        return ctx.literal('NOT ').sql(self.node)


class BitwiseMixin(object):
    """
    位运算
    """
    def __and__(self, other):
        return self.bin_and(other)

    def __or__(self, other):
        return self.bin_or(other)

    def __sub__(self, other):
        return self.bin_and(other.bin_negated())

    def __invert__(self):
        return BitwiseNegated(self)


class BitwiseNegated(BitwiseMixin, WrappedNode):
    """
    位运算
    """
    def __invert__(self):
        return self.node

    def _sql_(self, ctx):
        if ctx.state.operations:
            op_sql = ctx.state.operations.get(self.op, self.op)
        else:
            op_sql = self.op
        return ctx.literal(op_sql).sql(self.node)


class Value(ColumnBase):
    """
    要在参数化查询中使用的值。
    """
    _multi_types = (list, tuple, frozenset, set)

    def __init__(self, value, converter=None, unpack=True):
        """
        value -- python 对象或标量值。
        converter -- 用于将值转换为数据库能理解的类型的函数。
        unpack (bool) -- 列表或元组是应解包到值列表中还是按原样处理。
        """
        self.value = value
        self.converter = converter
        self.multi = isinstance(self.value, self._multi_types) and unpack
        if self.multi:
            self.values = []
            for item in self.value:
                if isinstance(item, Node):
                    self.values.append(item)
                else:
                    self.values.append(Value(item, self.converter))

    def _sql_(self, ctx):
        if self.multi:
            # For multi-part values (e.g. lists of IDs).
            return ctx.sql(EnclosedNodeList(self.values))

        return ctx.value(self.value, self.converter)


def AsIs(value):
    """
    表示 Value 按原样处理，并直接传递回数据库驱动程序。
    """
    return Value(value, unpack=False)


class Cast(WrappedNode):
    """
    表示 CAST(<node> AS <cast>) 表达式
    """
    def __init__(self, node, cast):
        super(Cast, self).__init__(node)
        self._cast = cast
        self._coerce = False

    def _sql_(self, ctx):
        return (ctx
                .literal('CAST(')
                .sql(self.node)
                .literal(' AS %s)' % self._cast))


class Ordering(WrappedNode):
    """
    表示按列的对象排序。
    """
    def __init__(self, node, direction, collation=None, nulls=None):
        super(Ordering, self).__init__(node)
        self.direction = direction
        self.collation = collation
        self.nulls = nulls
        if nulls and nulls.lower() not in ('first', 'last'):
            raise ValueError('Ordering nulls= parameter must be "first" or '
                             '"last", got: %s' % nulls)

    def collate(self, collation=None):
        """
        collation (str) -- 用于排序的排序规则名称。
        """
        return Ordering(self.node, self.direction, collation)

    def _null_ordering_case(self, nulls):
        if nulls.lower() == 'last':
            ifnull, notnull = 1, 0
        elif nulls.lower() == 'first':
            ifnull, notnull = 0, 1
        else:
            raise ValueError('unsupported value for nulls= ordering.')
        return Case(None, ((self.node.is_null(), ifnull),), notnull)

    def _sql_(self, ctx):
        if self.nulls and not ctx.state.nulls_ordering:
            ctx.sql(self._null_ordering_case(self.nulls)).literal(', ')

        ctx.sql(self.node).literal(' %s' % self.direction)
        if self.collation:
            ctx.literal(' COLLATE %s' % self.collation)
        if self.nulls and ctx.state.nulls_ordering:
            ctx.literal(' NULLS %s' % self.nulls)
        return ctx


def Asc(node, collation=None, nulls=None):
    """
    升序
    """
    return Ordering(node, 'ASC', collation, nulls)


def Desc(node, collation=None, nulls=None):
    """
    降序
    """
    return Ordering(node, 'DESC', collation, nulls)


class Expression(ColumnBase):
    """
    表示二进制表达式（lhs op rhs），例如（foo+1）
    """
    def __init__(self, lhs, op, rhs, flat=False):
        """
        lhs -- 左侧。
        op -- 操作。
        rhs -- 右侧。
        flat (bool) -- 是否将表达式括在括号中。
        """
        self.lhs = lhs
        self.op = op
        self.rhs = rhs
        self.flat = flat

    def _sql_(self, ctx):
        overrides = {'parentheses': not self.flat, 'in_expr': True}

        # First attempt to unwrap the node on the left-hand-side, so that we
        # can get at the underlying Field if one is present.
        node = self.lhs
        if isinstance(node, WrappedNode):
            node = node.unwrap()

        # Set up the appropriate converter if we have a field on the left side.
        if isinstance(node, Field):
            overrides['converter'] = node.db_value
        else:
            overrides['converter'] = None

        if ctx.state.operations:
            op_sql = ctx.state.operations.get(self.op, self.op)
        else:
            op_sql = self.op

        with ctx(**overrides):
            # Postgresql reports an error for IN/NOT IN (), so convert to
            # the equivalent boolean expression.
            op_in = self.op == OP.IN or self.op == OP.NOT_IN
            if op_in and ctx.as_new().parse(self.rhs)[0] == '()':
                return ctx.literal('0 = 1' if self.op == OP.IN else '1 = 1')

            return (ctx
                    .sql(self.lhs)
                    .literal(' %s ' % op_sql)
                    .sql(self.rhs))


class StringExpression(Expression):
    """
    字符串表达式
    """
    def __add__(self, rhs):
        return self.concat(rhs)

    def __radd__(self, lhs):
        return StringExpression(lhs, OP.CONCAT, self)


class Entity(ColumnBase):
    """
    表示查询中引用的实体，如表、列、别名。名称可以由多个组件组成

    例如 "a_table"."column_name"
    """
    def __init__(self, *path):
        self._path = [part.replace('"', '""') for part in path if part]

    def __getattr__(self, attr):
        return Entity(*self._path + [attr])

    def get_sort_key(self, ctx):
        """
        返回 _sort_key
        """
        return tuple(self._path)

    def __hash__(self):
        return hash((self.__class__.__name__, tuple(self._path)))

    def _sql_(self, ctx):
        return ctx.literal(quote(self._path, ctx.state.quote or '""'))


class SQL(ColumnBase):
    """
    表示参数化的 SQL 查询或查询片段。
    """
    def __init__(self, sql, params=None):
        self.sql = sql
        self.params = params

    def _sql_(self, ctx):
        ctx.literal(self.sql)
        if self.params:
            for param in self.params:
                ctx.value(param, False, add_param=False)
        return ctx


def Check(constraint):
    """
    表示检查约束

    Args:
        constraint (str) -- 约束 SQL。
    """
    return SQL('CHECK (%s)' % constraint)


class Function(ColumnBase):
    """
    表示 SQL 函数调用。
    """
    def __init__(self, name, arguments, coerce=True, python_value=None):
        """
        name (str) -- 函数名。
        arguments (tuple) -- 函数的参数。
        coerce (bool) -- 从光标读取函数返回值时，是否将函数结果强制为特定的数据类型。
        python_value (callable) -- 用于转换光标返回值的函数。
        """
        self.name = name
        self.arguments = arguments
        self._filter = None
        self._python_value = python_value
        if name and name.lower() in ('sum', 'count', 'cast'):
            self._coerce = False
        else:
            self._coerce = coerce

    def __getattr__(self, attr):
        def decorator(*args, **kwargs):
            """
            decorator
            """
            return Function(attr, args, **kwargs)
        return decorator

    @Node.copy
    def filter(self, where=None):
        """
        where -- 用于筛选聚合的表达式。
        添加 FILTER (WHERE...) 子句转换为聚合函数。计算 where 表达式以确定哪些行被送入聚合函数。
        """
        self._filter = where

    @Node.copy
    def python_value(self, func=None):
        """
        用于转换光标返回值的函数。
        指定在转换数据库光标返回的值时要使用的特定函数。例如:
        +-----------------------------------------
        | tweet_ids = (fn.GROUP_CONCAT(Tweet.id).python_value(lambda idlist: [int(i) for i in idlist]))
        +-----------------------------------------
        """
        self._python_value = func

    def over(self, partition_by=None, order_by=None, start=None, end=None,
             frame_type=None, window=None, exclude=None):
        """
        partition_by (list) -- 要分区的列列表。
        order_by (list) -- 按顺序排列窗口的列/表达式列表。
        start -- A SQL 表示窗口范围开始的实例或字符串。
        end -- A SQL 表示窗口范围结束的实例或字符串。
        frame_type (str) -- Window.RANGE ， Window.ROWS 或 Window.GROUPS .
        window (Window) -- A Window 实例。
        exclude -- 帧排除，其中一个 Window.CURRENT_ROW ， Window.GROUP ， Window.TIES 或 Window.NO_OTHERS .
        """
        if isinstance(partition_by, Window) and window is None:
            window = partition_by

        if window is not None:
            node = WindowAlias(window)
        else:
            node = Window(partition_by=partition_by, order_by=order_by,
                          start=start, end=end, frame_type=frame_type,
                          exclude=exclude, _inline=True)
        return NodeList((self, SQL('OVER'), node))

    def _sql_(self, ctx):
        ctx.literal(self.name)
        if not len(self.arguments):
            ctx.literal('()')
        else:
            with ctx(in_function=True, function_arg_count=len(self.arguments)):
                nodes = [(arg if isinstance(arg, Node) else Value(arg, False)) for arg in self.arguments]
                ctx.sql(EnclosedNodeList(nodes))

        if self._filter:
            ctx.literal(' FILTER (WHERE ').sql(self._filter).literal(')')
        return ctx


fn = Function(None, None)


class Window(Node):
    """
    表示 window 子句
    """
    # Frame start/end and frame exclusion.
    CURRENT_ROW = SQL('CURRENT ROW')
    GROUP = SQL('GROUP')
    TIES = SQL('TIES')
    NO_OTHERS = SQL('NO OTHERS')

    # Frame types.
    GROUPS = 'GROUPS'
    RANGE = 'RANGE'
    ROWS = 'ROWS'

    def __init__(self, partition_by=None, order_by=None, start=None, end=None,
                 frame_type=None, extends=None, exclude=None, alias=None,
                 _inline=False):
        super(Window, self).__init__()
        if start is not None and not isinstance(start, SQL):
            start = SQL(start)
        if end is not None and not isinstance(end, SQL):
            end = SQL(end)

        self.partition_by = ensure_tuple(partition_by)
        self.order_by = ensure_tuple(order_by)
        self.start = start
        self.end = end
        if self.start is None and self.end is not None:
            raise ValueError('Cannot specify WINDOW end without start.')
        self._alias = alias or 'w'
        self._inline = _inline
        self.frame_type = frame_type
        self._extends = extends
        self._exclude = exclude

    def alias(self, alias=None):
        """
        别名
        """
        self._alias = alias or 'w'
        return self

    @Node.copy
    def as_range(self):
        """
        Window.RANGE
        """
        self.frame_type = Window.RANGE

    @Node.copy
    def as_rows(self):
        """
        Window.ROWS
        """
        self.frame_type = Window.ROWS

    @Node.copy
    def as_groups(self):
        """
        Window.GROUPS
        """
        self.frame_type = Window.GROUPS

    @Node.copy
    def extends(self, window=None):
        """
        Args:
            window (Window) -- A Window 要扩展的定义。或者，您可以指定窗口的别名。
        """
        self._extends = window

    @Node.copy
    def exclude(self, frame_exclusion=None):
        """
        Args:
            frame_exclusion -- 帧排除，其中一个 Window.CURRENT_ROW ， Window.GROUP ， Window.TIES 或 Window.NO_OTHERS .
        """
        if isinstance(frame_exclusion, basestring):
            frame_exclusion = SQL(frame_exclusion)
        self._exclude = frame_exclusion

    @staticmethod
    def following(value=None):
        """
        生成适合作为 end 窗口范围的参数。

        Args:
            value -- 后面的行数。如果 None 是无界的。
        """
        if value is None:
            return SQL('UNBOUNDED FOLLOWING')
        return SQL('%d FOLLOWING' % value)

    @staticmethod
    def preceding(value=None):
        """
        生成适合作为 start 窗口范围的参数。

        Args:
            value -- 前面的行数。如果 None 是无界的。
        """
        if value is None:
            return SQL('UNBOUNDED PRECEDING')
        return SQL('%d PRECEDING' % value)

    def _sql_(self, ctx):
        if ctx.scope != SCOPE_SOURCE and not self._inline:
            ctx.literal(self._alias)
            ctx.literal(' AS ')

        with ctx(parentheses=True):
            parts = []
            if self._extends is not None:
                ext = self._extends
                if isinstance(ext, Window):
                    ext = SQL(ext._alias)
                elif isinstance(ext, basestring):
                    ext = SQL(ext)
                parts.append(ext)
            if self.partition_by:
                parts.extend((
                    SQL('PARTITION BY'),
                    CommaNodeList(self.partition_by)))
            if self.order_by:
                parts.extend((
                    SQL('ORDER BY'),
                    CommaNodeList(self.order_by)))
            if self.start is not None and self.end is not None:
                frame = self.frame_type or 'ROWS'
                parts.extend((
                    SQL('%s BETWEEN' % frame),
                    self.start,
                    SQL('AND'),
                    self.end))
            elif self.start is not None:
                parts.extend((SQL(self.frame_type or 'ROWS'), self.start))
            elif self.frame_type is not None:
                parts.append(SQL('%s UNBOUNDED PRECEDING' % self.frame_type))
            if self._exclude is not None:
                parts.extend((SQL('EXCLUDE'), self._exclude))
            ctx.sql(NodeList(parts))
        return ctx


class WindowAlias(Node):
    """
    Window 别名的类
    """
    def __init__(self, window):
        self.window = window

    def alias(self, window_alias):
        """
        设置别名
        """
        self.window._alias = window_alias
        return self

    def _sql_(self, ctx):
        return ctx.literal(self.window._alias or 'w')


def Case(predicate, expression_tuples, default=None):
    """
    Args:
        predicate -- 用于事例查询的谓词（可选）。
        expression_tuples -- 要评估的一个或多个案例。
        default -- 默认值（可选）。
    """
    clauses = [SQL('CASE')]
    if predicate is not None:
        clauses.append(predicate)
    for expr, value in expression_tuples:
        clauses.extend((SQL('WHEN'), expr, SQL('THEN'), value))
    if default is not None:
        clauses.extend((SQL('ELSE'), default))
    clauses.append(SQL('END'))
    return NodeList(clauses)


class NodeList(ColumnBase):
    """
    表示节点列表、多部分子句、参数列表等。
    """
    def __init__(self, nodes, glue=' ', parens=False):
        """
        nodes (list) -- 零个或多个节点。
        glue (str) -- 如何在转换为SQL时联接节点。
        parens (bool) -- 是否将结果SQL括在括号中。
        """
        self.nodes = nodes
        self.glue = glue
        self.parens = parens
        if parens and len(self.nodes) == 1:
            if isinstance(self.nodes[0], Expression):
                # Hack to avoid double-parentheses.
                self.nodes[0].flat = True

    def _sql_(self, ctx):
        n_nodes = len(self.nodes)
        if n_nodes == 0:
            return ctx.literal('()') if self.parens else ctx
        with ctx(parentheses=self.parens):
            for i in range(n_nodes - 1):
                ctx.sql(self.nodes[i])
                ctx.literal(self.glue)
            ctx.sql(self.nodes[n_nodes - 1])
        return ctx


def CommaNodeList(nodes):
    """
    表示由逗号连接的节点列表。
    """
    return NodeList(nodes, ', ')


def EnclosedNodeList(nodes):
    """
    表示用逗号连接并用括号括起来的节点列表。
    """
    return NodeList(nodes, ', ', True)


class _Namespace(Node):
    __slots__ = ('_name',)

    def __init__(self, name):
        self._name = name

    def __getattr__(self, attr):
        return NamespaceAttribute(self, attr)
    __getitem__ = __getattr__


class NamespaceAttribute(ColumnBase):
    """
    命名空间属性
    """
    def __init__(self, namespace, attribute):
        self._namespace = namespace
        self._attribute = attribute

    def _sql_(self, ctx):
        return (ctx
                .literal(self._namespace._name + '.')
                .sql(Entity(self._attribute)))


EXCLUDED = _Namespace('EXCLUDED')


class DQ(ColumnBase):
    """
    表示适用于 Model.filter() 或 ModelSelect.filter() 方法。
    """
    def __init__(self, **query):
        """
        query -- 使用 django 样式查找的任意筛选表达式。
        """
        super(DQ, self).__init__()
        self.query = query
        self._negated = False

    @Node.copy
    def __invert__(self):
        self._negated = not self._negated

    def clone(self):
        """
        clone 自身
        """
        node = DQ(**self.query)
        node._negated = self._negated
        return node


#: Represent a row tuple.
Tuple = lambda *a: EnclosedNodeList(a)


class QualifiedNames(WrappedNode):
    """
    限定名称
    """
    def _sql_(self, ctx):
        with ctx.scope_column():
            return ctx.sql(self.node)


def qualify_names(node):
    """
    # Search a node heirarchy to ensure that any column-like objects are
    # referenced using fully-qualified names.
    """
    if isinstance(node, Expression):
        return node.__class__(qualify_names(node.lhs), node.op,
                              qualify_names(node.rhs), node.flat)
    elif isinstance(node, ColumnBase):
        return QualifiedNames(node)
    return node


class OnConflict(Node):
    """
    表示数据修改查询的冲突解决子句。
    """
    def __init__(self, action=None, update=None, preserve=None, where=None,
                 conflict_target=None, conflict_where=None,
                 conflict_constraint=None):
        """
        action (str) -- 解决冲突时要采取的操作。
        update -- 将列映射到新值的字典。
        preserve -- 一个列的列表，其值应从原始插入中保留。也见 EXCLUDED .
        where -- 用于限制冲突解决的表达式。
        conflict_target -- 构成约束的列。
        conflict_where -- 如果约束目标是部分索引（带WHERE子句的索引），则需要匹配该约束目标的表达式。
        conflict_constraint (str) -- 用于冲突解决的约束的名称。目前只有Postgres支持。
        """
        self._action = action
        self._update = update
        self._preserve = ensure_tuple(preserve)
        self._where = where
        if conflict_target is not None and conflict_constraint is not None:
            raise ValueError('only one of "conflict_target" and '
                             '"conflict_constraint" may be specified.')
        self._conflict_target = ensure_tuple(conflict_target)
        self._conflict_where = conflict_where
        self._conflict_constraint = conflict_constraint

    def get_conflict_statement(self, ctx, query):
        """
        进行冲突处理
        """
        return ctx.state.conflict_statement(self, query)

    def get_conflict_update(self, ctx, query):
        """
        conflict_update
        """
        return ctx.state.conflict_update(self, query)

    @Node.copy
    def preserve(self, *columns):
        """
        Args:
            columns -- 应保留其值的列。
        """
        self._preserve = columns

    @Node.copy
    def update(self, _data=None, **kwargs):
        """
        Args:
            _data (dict) -- 字典将列映射到新值。
            kwargs -- 将列名映射到新值的字典。
        """
        if _data and kwargs and not isinstance(_data, dict):
            raise ValueError('Cannot mix data with keyword arguments in the '
                             'OnConflict update method.')
        _data = _data or {}
        if kwargs:
            _data.update(kwargs)
        self._update = _data

    @Node.copy
    def where(self, *expressions):
        """
        Args:
            expressions -- 限制冲突解决子句操作的表达式。
        """
        if self._where is not None:
            expressions = (self._where,) + expressions
        self._where = reduce(operator.and_, expressions)

    @Node.copy
    def conflict_target(self, *constraints):
        """
        Args:
            constraints -- 要用作冲突解决目标的列。
        """
        self._conflict_constraint = None
        self._conflict_target = constraints

    @Node.copy
    def conflict_where(self, *expressions):
        """
        Args:
            expressions -- 如果冲突目标是部分索引，则为与冲突目标索引匹配的表达式。
        """
        if self._conflict_where is not None:
            expressions = (self._conflict_where,) + expressions
        self._conflict_where = reduce(operator.and_, expressions)

    @Node.copy
    def conflict_constraint(self, constraint):
        """
        Args:
            constraint (str) -- 用作冲突解决目标的约束的名称。目前只有 Postgres 支持。
        """
        self._conflict_constraint = constraint
        self._conflict_target = None


def database_required(method):
    """
    装饰器
    """
    @wraps(method)
    def inner(self, database=None, *args, **kwargs):
        """
        inner function
        """
        database = self._database if database is None else database
        if not database:
            raise InterfaceError('Query must be bound to a database in order '
                                 'to call "%s".' % method.__name__)
        return method(self, database, *args, **kwargs)
    return inner

# BASE QUERY INTERFACE.


class BaseQuery(Node):
    """
    查询类的父类。不会直接使用 BaseQuery ，它实现了一些在所有查询类型中都很常见的方法。
    """
    default_row_type = ROW.DICT

    def __init__(self, _database=None, **kwargs):
        self._database = _database
        self._cursor_wrapper = None
        self._row_type = None
        self._constructor = None
        super(BaseQuery, self).__init__(**kwargs)

    def bind(self, database=None):
        """
        将查询绑定到给定的数据库以执行。
        """
        self._database = database
        return self

    def clone(self):
        """
        clone
        """
        query = super(BaseQuery, self).clone()
        query._cursor_wrapper = None
        return query

    @Node.copy
    def dicts(self, as_dict=True):
        """
        将行作为字典返回。
        """
        self._row_type = ROW.DICT if as_dict else None
        return self

    @Node.copy
    def tuples(self, as_tuple=True):
        """
        以元组形式返回行。
        """
        self._row_type = ROW.TUPLE if as_tuple else None
        return self

    @Node.copy
    def namedtuples(self, as_namedtuple=True):
        """
        以命名元组的形式返回行。
        """
        self._row_type = ROW.NAMED_TUPLE if as_namedtuple else None
        return self

    @Node.copy
    def objects(self, constructor=None):
        """
        使用给定的构造函数将行作为任意对象返回。
        Args:
            constructor -- 接受行dict并返回任意对象的函数。
        """
        self._row_type = ROW.CONSTRUCTOR if constructor else None
        self._constructor = constructor
        return self

    def _get_cursor_wrapper(self, cursor):
        row_type = self._row_type or self.default_row_type

        if row_type == ROW.DICT:
            return DictCursorWrapper(cursor)
        elif row_type == ROW.TUPLE:
            return CursorWrapper(cursor)
        elif row_type == ROW.NAMED_TUPLE:
            return NamedTupleCursorWrapper(cursor)
        elif row_type == ROW.CONSTRUCTOR:
            return ObjectCursorWrapper(cursor, self._constructor)
        else:
            raise ValueError('Unrecognized row type: "%s".' % row_type)

    def _sql_(self, ctx):
        raise NotImplementedError

    def sql(self):
        """
        由查询的 SQL 和参数组成的 2 元组。
        """
        if self._database:
            context = self._database.get_sql_context()
        else:
            context = Context()
        return context.parse(self)

    @database_required
    def execute(self, database=None):
        """
        执行查询并返回结果

        Args:
            database (Database) -- 要对其执行查询的数据库。如果查询以前绑定到数据库，则不需要。
                                   此参数会通过 database_required 装饰器进行传进来
        """
        return self._execute(database)

    def _execute(self, database):
        raise NotImplementedError

    def iterator(self, database=None):
        """
        执行查询并返回结果集的迭代器。对于大型结果集，该方法更可取，因为在迭代期间行不会缓存在内存中。
        """
        return iter(self.execute(database).iterator())

    def _ensure_execution(self):
        if not self._cursor_wrapper:
            if not self._database:
                raise ValueError('Query has not been executed.')
            self.execute()

    def __iter__(self):
        self._ensure_execution()
        return iter(self._cursor_wrapper)

    def __getitem__(self, value):
        self._ensure_execution()
        if isinstance(value, slice):
            index = value.stop
        else:
            index = value
        if index is not None:
            index = index + 1 if index >= 0 else 0
        self._cursor_wrapper.fill_cache(index)
        return self._cursor_wrapper.row_cache[value]

    def __len__(self):
        """
        返回结果集中的行数。
        这不会发出 COUNT() 查询
        """
        self._ensure_execution()
        return len(self._cursor_wrapper)

    def __str__(self):
        return query_to_string(self)


class RawQuery(BaseQuery):
    """
    通过直接指定要执行的SQL来创建查询。
    """
    def __init__(self, sql=None, params=None, **kwargs):
        super(RawQuery, self).__init__(**kwargs)
        self._sql = sql
        self._params = params

    def _sql_(self, ctx):
        ctx.literal(self._sql)
        if self._params:
            for param in self._params:
                ctx.value(param, add_param=False)
        return ctx

    def _execute(self, database):
        if self._cursor_wrapper is None:
            cursor = database.execute(self)
            self._cursor_wrapper = self._get_cursor_wrapper(cursor)
        return self._cursor_wrapper


class Query(BaseQuery):
    """
    支持方法链接 API 的查询的基类。
    """
    def __init__(self, where=None, order_by=None, limit=None, offset=None,
                 **kwargs):
        super(Query, self).__init__(**kwargs)
        self._where = where
        self._order_by = order_by
        self._limit = limit
        self._offset = offset

        self._cte_list = None

    @Node.copy
    def with_cte(self, *cte_list):
        """
        在查询中包含给定的公用表表达式
        """
        self._cte_list = cte_list

    @Node.copy
    def where(self, *expressions):
        """
        在查询的 WHERE 子句中包含给定表达式。
        """
        if self._where is not None:
            expressions = (self._where,) + expressions
        self._where = reduce(operator.and_, expressions)

    @Node.copy
    def orwhere(self, *expressions):
        """
        在查询的 WHERE 子句中包含给定表达式
        """
        if self._where is not None:
            expressions = (self._where,) + expressions
        self._where = reduce(operator.or_, expressions)

    @Node.copy
    def order_by(self, *values):
        """
        定义 ORDER BY 子句
        """
        self._order_by = values

    @Node.copy
    def order_by_extend(self, *values):
        """
        用给定的值扩展先前指定的 ORDER BY 子句。
        """
        self._order_by = ((self._order_by or ()) + values) or None

    @Node.copy
    def limit(self, value=None):
        """
        value (int) -- 为 LIMIT 子句指定值。
        """
        self._limit = value

    @Node.copy
    def offset(self, value=None):
        """
        value (int) -- 指定 offset 子句的值。
        """
        self._offset = value

    @Node.copy
    def paginate(self, page, paginate_by=20):
        """
        page (int) -- 结果的页数（从1开始）。
        paginate_by (int) -- 每页行数。
        """
        if page > 0:
            page -= 1
        self._limit = paginate_by
        self._offset = page * paginate_by

    def _apply_ordering(self, ctx):
        if self._order_by:
            (ctx
             .literal(' ORDER BY ')
             .sql(CommaNodeList(self._order_by)))
        if self._limit is not None or (self._offset is not None and
                                       ctx.state.limit_max):
            ctx.literal(' LIMIT ').sql(self._limit or ctx.state.limit_max)
        if self._offset is not None:
            ctx.literal(' OFFSET ').sql(self._offset)
        return ctx

    def _sql_(self, ctx):
        if self._cte_list:
            # The CTE scope is only used at the very beginning of the query,
            # when we are describing the various CTEs we will be using.
            recursive = any(cte._recursive for cte in self._cte_list)

            # Explicitly disable the "subquery" flag here, so as to avoid
            # unnecessary parentheses around subsequent selects.
            with ctx.scope_cte(subquery=False):
                (ctx
                 .literal('WITH RECURSIVE ' if recursive else 'WITH ')
                 .sql(CommaNodeList(self._cte_list))
                 .literal(' '))
        return ctx


def _compound_select_(operation, inverted=False):
    def method(self, other):
        """
        inner function
        """
        if inverted:
            self, other = other, self
        return CompoundSelectQuery(self, operation, other)
    return method


class SelectQuery(Query):
    """
    选择实现用于创建复合查询的运算符重载的查询帮助器类。
    """
    union_all = __add__ = _compound_select_('UNION ALL')
    union = __or__ = _compound_select_('UNION')
    intersect = __and__ = _compound_select_('INTERSECT')
    except_ = __sub__ = _compound_select_('EXCEPT')
    __radd__ = _compound_select_('UNION ALL', inverted=True)
    __ror__ = _compound_select_('UNION', inverted=True)
    __rand__ = _compound_select_('INTERSECT', inverted=True)
    __rsub__ = _compound_select_('EXCEPT', inverted=True)

    def select_from(self, *columns):
        """
        创建包装当前（调用）查询的新查询

        Args:
            columns -- 要从内部查询中选择的一列或多列。
        Returns:
            包装调用查询的新查询。
        """
        if not columns:
            raise ValueError('select_from() must specify one or more columns.')

        query = (Select((self,), columns)
                 .bind(self._database))
        if getattr(self, 'model', None) is not None:
            # Bind to the sub-select's model type, if defined.
            query = query.objects(self.model)
        return query


class SelectBase(_HashableSource, Source, SelectQuery):
    """
    查询基类
    """
    def _get_hash(self):
        return hash((self.__class__, self._alias or id(self)))

    def _execute(self, database):
        if self._cursor_wrapper is None:
            cursor = database.execute(self)
            self._cursor_wrapper = self._get_cursor_wrapper(cursor)
        return self._cursor_wrapper

    @database_required
    def peek(self, database, n=1):
        """
        执行查询并从光标开始返回给定的行数。可以安全地多次调用此函数，并始终返回前n行结果。

        Args:
            database (Database) -- 要对其执行查询的数据库。
            n (int) -- 要返回的行数。
        Returns:
            如果 n=1，则为一行，否则为一列行。
        """
        rows = self.execute(database)[:n]
        if rows:
            return rows[0] if n == 1 else rows

    @database_required
    def first(self, database, n=1):
        """
        像 peek() 方法，除了 LIMIT 应用于查询以确保 n 返回行。多个相同值的调用 n 不会导致多次执行

        Args:
            database (Database) -- 要对其执行查询的数据库。
            n (int) -- 要返回的行数。
        Returns:
            如果 n=1，则为一行，否则为一列行
        """
        if self._limit != n:
            self._limit = n
            self._cursor_wrapper = None
        return self.peek(database, n=n)

    @database_required
    def scalar(self, database, as_tuple=False):
        """
        从结果的第一行返回一个标量值。
        如果预期有多个标量值（例如单个查询中的多个聚合），则可以指定 as_tuple=True 得到行元组。
        """
        row = self.tuples().peek(database)
        return row[0] if row and not as_tuple else row

    @database_required
    def count(self, database, clear_limit=False):
        """
        查询结果集中的行数。通过运行 select count（1）from（<current query>）实现。

        Args:
            database (Database) -- 要对其执行查询的数据库。
            clear_limit (bool) -- 计数时清除任何限制子句。
        """
        clone = self.order_by().alias('_wrapped')
        if clear_limit:
            clone._limit = clone._offset = None
        try:
            if clone._having is None and clone._group_by is None and \
               clone._windows is None and clone._distinct is None and \
               clone._simple_distinct is not True:
                clone = clone.select(SQL('1'))
        except AttributeError:
            pass
        return Select([clone], [fn.COUNT(SQL('1'))]).scalar(database)

    @database_required
    def exists(self, database):
        """
        返回一个布尔值，指示当前查询是否有任何结果。

        Args:
            database (Database) -- 要对其执行查询的数据库。
        Returns:
            当前查询是否存在任何结果。
        """
        clone = self.columns(SQL('1'))
        clone._limit = 1
        clone._offset = None
        return bool(clone.scalar())

    @database_required
    def get(self, database):
        """
        执行查询并返回第一行（如果存在）。多个调用将导致执行多个查询。

        Args:
            database (Database) -- 要对其执行查询的数据库。
        Returns:
            数据库中的单行或 None
        """
        self._cursor_wrapper = None
        try:
            return self.execute(database)[0]
        except IndexError:
            pass


# QUERY IMPLEMENTATIONS.


class CompoundSelectQuery(SelectBase):
    """
    表示复合 select 查询的类。
    """
    def __init__(self, lhs, op, rhs):
        """
        lhs (SelectBase) -- 选择或复合选择查询。
        op (str) -- 操作（例如联合、交叉、除外）。
        rhs (SelectBase) -- 选择或复合选择查询。
        """
        super(CompoundSelectQuery, self).__init__()
        self.lhs = lhs
        self.op = op
        self.rhs = rhs

    @property
    def _returning(self):
        return self.lhs._returning

    @database_required
    def exists(self, database):
        """
        返回 False/True
        """
        query = Select((self.limit(1),), (SQL('1'),)).bind(database)
        return bool(query.scalar(database))

    def _get_query_key(self):
        return (self.lhs.get_query_key(), self.rhs.get_query_key())

    def _wrap_parens(self, ctx, subq):
        csq_setting = ctx.state.compound_select_parentheses

        if not csq_setting or csq_setting == CSQ_PARENTHESES_NEVER:
            return False
        elif csq_setting == CSQ_PARENTHESES_ALWAYS:
            return True
        elif csq_setting == CSQ_PARENTHESES_UNNESTED:
            return not isinstance(subq, CompoundSelectQuery)

    def _sql_(self, ctx):
        if ctx.scope == SCOPE_COLUMN:
            return self.apply_column(ctx)

        outer_parens = ctx.subquery or (ctx.scope == SCOPE_SOURCE)
        with ctx(parentheses=outer_parens):
            # Should the left-hand query be wrapped in parentheses?
            lhs_parens = self._wrap_parens(ctx, self.lhs)
            with ctx.scope_normal(parentheses=lhs_parens, subquery=False):
                ctx.sql(self.lhs)
            ctx.literal(' %s ' % self.op)
            with ctx.push_alias():
                # Should the right-hand query be wrapped in parentheses?
                rhs_parens = self._wrap_parens(ctx, self.rhs)
                with ctx.scope_normal(parentheses=rhs_parens, subquery=False):
                    ctx.sql(self.rhs)

            # Apply ORDER BY, LIMIT, OFFSET. We use the "values" scope so that
            # entity names are not fully-qualified. This is a bit of a hack, as
            # we're relying on the logic in Column._sql_() to not fully
            # qualify column names.
            with ctx.scope_values():
                self._apply_ordering(ctx)

        return self.apply_alias(ctx)


class Select(SelectBase):
    """
    表示 select 查询的类
    """
    def __init__(self, from_list=None, columns=None, group_by=None,
                 having=None, distinct=None, windows=None, for_update=None,
                 **kwargs):
        super(Select, self).__init__(**kwargs)
        self._from_list = (list(from_list) if isinstance(from_list, tuple)
                           else from_list) or []
        self._returning = columns
        self._group_by = group_by
        self._having = having
        self._windows = None
        self._for_update = 'FOR UPDATE' if for_update is True else for_update

        self._distinct = self._simple_distinct = None
        if distinct:
            if isinstance(distinct, bool):
                self._simple_distinct = distinct
            else:
                self._distinct = distinct

        self._cursor_wrapper = None

    def clone(self):
        """
        clone
        """
        clone = super(Select, self).clone()
        if clone._from_list:
            clone._from_list = list(clone._from_list)
        return clone

    @Node.copy
    def columns(self, *columns, **kwargs):
        """
        指定要选择的列或类似列的值。
        """
        self._returning = columns
    select = columns

    @Node.copy
    def select_extend(self, *columns):
        """
        用给定的列扩展当前所选内容。
        +-------------------------------
        | def get_users(with_count=False):
        |    query = User.select()
        |    if with_count:
        |        query = (query
        |                 .select_extend(fn.COUNT(Tweet.id).alias('count'))
        |                 .join(Tweet, JOIN.LEFT_OUTER)
        |                 .group_by(User))
        |    return query
        +-------------------------------
        """
        self._returning = tuple(self._returning) + columns

    @Node.copy
    def from_(self, *sources):
        """
        指定在 FROM 子句中应使用哪些与表类似的对象。
        """
        self._from_list = list(sources)

    @Node.copy
    def join(self, dest, join_type='INNER', on=None):
        """
        联接类型
        """
        if not self._from_list:
            raise ValueError('No sources to join on.')
        item = self._from_list.pop()
        self._from_list.append(Join(item, dest, join_type, on))

    @Node.copy
    def group_by(self, *columns):
        """
        定义 group by 子句
        """
        grouping = []
        for column in columns:
            if isinstance(column, Table):
                if not column._columns:
                    raise ValueError('Cannot pass a table to group_by() that '
                                     'does not have columns explicitly '
                                     'declared.')
                grouping.extend([getattr(column, col_name)
                                 for col_name in column._columns])
            else:
                grouping.append(column)
        self._group_by = grouping

    def group_by_extend(self, *values):
        """@Node.copy used from group_by() call"""
        group_by = tuple(self._group_by or ()) + values
        return self.group_by(*group_by)

    @Node.copy
    def having(self, *expressions):
        """
        在查询的 HAVING 子句中包含给定表达式。
        expressions -- 要包含在HAVING子句中的零个或多个表达式
        """
        if self._having is not None:
            expressions = (self._having,) + expressions
        self._having = reduce(operator.and_, expressions)

    @Node.copy
    def distinct(self, *columns):
        """
        指示此查询是否应使用 distinct 子句
        """
        if len(columns) == 1 and (columns[0] is True or columns[0] is False):
            self._simple_distinct = columns[0]
        else:
            self._simple_distinct = False
            self._distinct = columns

    @Node.copy
    def window(self, *windows):
        """
        定义 window 子句。任何先前指定的值都将被覆盖。
        """
        self._windows = windows if windows else None

    @Node.copy
    def for_update(self, for_update=True):
        """
        for_update -- 指示所需表达式的布尔值或字符串，例如“for update nowait”。
        """
        self._for_update = 'FOR UPDATE' if for_update is True else for_update

    def _get_query_key(self):
        return self._alias

    def _sql_selection_(self, ctx, is_subquery=False):
        return ctx.sql(CommaNodeList(self._returning))

    def _sql_(self, ctx):
        if ctx.scope == SCOPE_COLUMN:
            return self.apply_column(ctx)

        is_subquery = ctx.subquery
        state = {
            'converter': None,
            'in_function': False,
            'parentheses': is_subquery or (ctx.scope == SCOPE_SOURCE),
            'subquery': True,
        }
        if ctx.state.in_function and ctx.state.function_arg_count == 1:
            state['parentheses'] = False

        with ctx.scope_normal(**state):
            # Defer calling parent SQL until here. This ensures that any CTEs
            # for this query will be properly nested if this query is a
            # sub-select or is used in an expression. See GH#1809 for example.
            super(Select, self)._sql_(ctx)

            ctx.literal('SELECT ')
            if self._simple_distinct or self._distinct is not None:
                ctx.literal('DISTINCT ')
                if self._distinct:
                    (ctx
                     .literal('ON ')
                     .sql(EnclosedNodeList(self._distinct))
                     .literal(' '))

            with ctx.scope_source():
                ctx = self._sql_selection_(ctx, is_subquery)

            if self._from_list:
                with ctx.scope_source(parentheses=False):
                    ctx.literal(' FROM ').sql(CommaNodeList(self._from_list))

            if self._where is not None:
                ctx.literal(' WHERE ').sql(self._where)

            if self._group_by:
                ctx.literal(' GROUP BY ').sql(CommaNodeList(self._group_by))

            if self._having is not None:
                ctx.literal(' HAVING ').sql(self._having)

            if self._windows is not None:
                ctx.literal(' WINDOW ')
                ctx.sql(CommaNodeList(self._windows))

            # Apply ORDER BY, LIMIT, OFFSET.
            self._apply_ordering(ctx)

            if self._for_update:
                if not ctx.state.for_update:
                    raise ValueError('FOR UPDATE specified but not supported '
                                     'by database.')
                ctx.literal(' ')
                ctx.sql(SQL(self._for_update))

        # If the subquery is inside a function -or- we are evaluating a
        # subquery on either side of an expression w/o an explicit alias, do
        # not generate an alias + AS clause.
        if ctx.state.in_function or (ctx.state.in_expr and
                                     self._alias is None):
            return ctx

        return self.apply_alias(ctx)


class _WriteQuery(Query):
    """
    用于写入查询的基类。
    """
    def __init__(self, table, returning=None, **kwargs):
        self.table = table
        self._returning = returning
        self._return_cursor = True if returning else False
        super(_WriteQuery, self).__init__(**kwargs)

    @Node.copy
    def returning(self, *returning):
        """
        指定查询的返回子句
        Args:
            returning -- 用于返回子句的零个或多个类似于列的对象
        """
        self._returning = returning
        self._return_cursor = True if returning else False

    def apply_returning(self, ctx):
        """
        返回 ctx
        """
        if self._returning:
            with ctx.scope_normal():
                ctx.literal(' RETURNING ').sql(CommaNodeList(self._returning))
        return ctx

    def _execute(self, database):
        if self._returning:
            cursor = self.execute_returning(database)
        else:
            cursor = database.execute(self)
        return self.handle_result(database, cursor)

    def execute_returning(self, database):
        """
        执行操作
        """
        if self._cursor_wrapper is None:
            cursor = database.execute(self)
            self._cursor_wrapper = self._get_cursor_wrapper(cursor)
        return self._cursor_wrapper

    def handle_result(self, database, cursor):
        """
        返回 cursor
        """
        if self._return_cursor:
            return cursor
        return database.rows_affected(cursor)

    def _set_table_alias(self, ctx):
        ctx.alias_manager[self.table] = self.table.__name__

    def _sql_(self, ctx):
        super(_WriteQuery, self)._sql_(ctx)
        # We explicitly set the table alias to the table's name, which ensures
        # that if a sub-select references a column on the outer table, we won't
        # assign it a new alias (e.g. t2) but will refer to it as table.column.
        self._set_table_alias(ctx)
        return ctx


class Update(_WriteQuery):
    """
    表示更新的类。
    """
    def __init__(self, table, update=None, **kwargs):
        super(Update, self).__init__(table, **kwargs)
        self._update = update
        self._from = None

    @Node.copy
    def from_(self, *sources):
        """
        sources -- FROM子句的源为零或多个。
        """
        self._from = sources

    def _sql_(self, ctx):
        super(Update, self)._sql_(ctx)

        with ctx.scope_values(subquery=True):
            ctx.literal('UPDATE ')

            expressions = []
            for k, v in sorted(self._update.items(), key=ctx.column_sort_key):
                if not isinstance(v, Node):
                    converter = k.db_value if isinstance(k, Field) else None
                    v = Value(v, converter=converter, unpack=False)
                if not isinstance(v, Value):
                    v = qualify_names(v)
                expressions.append(NodeList((k, SQL('='), v)))

            (ctx
             .sql(self.table)
             .literal(' SET ')
             .sql(CommaNodeList(expressions)))

            if self._from:
                with ctx.scope_source(parentheses=False):
                    ctx.literal(' FROM ').sql(CommaNodeList(self._from))

            if self._where:
                with ctx.scope_normal():
                    ctx.literal(' WHERE ').sql(self._where)
            self._apply_ordering(ctx)
            return self.apply_returning(ctx)


class Insert(_WriteQuery):
    """
    表示插入的类。
    """
    SIMPLE = 0
    QUERY = 1
    MULTI = 2

    class DefaultValuesException(Exception):
        """
        默认值异常
        """
        pass

    def __init__(self, table, insert=None, columns=None, on_conflict=None,
                 **kwargs):
        super(Insert, self).__init__(table, **kwargs)
        self._insert = insert
        self._columns = columns
        self._on_conflict = on_conflict
        self._query_type = None

    def where(self, *expressions):
        """
        Args:
            expressions -- 要包含在WHERE子句中的零个或多个表达式。
        """
        raise NotImplementedError('INSERT queries cannot have a WHERE clause.')

    @Node.copy
    def on_conflict_ignore(self, ignore=True):
        """
        指定忽略冲突解决策略。
        Args:
            ignore (bool) -- 是否添加冲突忽略子句。
        """
        self._on_conflict = OnConflict('IGNORE') if ignore else None

    @Node.copy
    def on_conflict_replace(self, replace=True):
        """
        指定替换冲突解决策略。
        Args:
            ignore (bool) -- 是否添加冲突替换子句。
        """
        self._on_conflict = OnConflict('REPLACE') if replace else None

    @Node.copy
    def on_conflict(self, *args, **kwargs):
        """
        指定的参数 OnConflict 用于冲突解决的子句。
        """
        self._on_conflict = (OnConflict(*args, **kwargs) if (args or kwargs)
                             else None)

    def _simple_insert(self, ctx):
        if not self._insert:
            raise self.DefaultValuesException('Error: no data to insert.')
        return self._generate_insert((self._insert,), ctx)

    def get_default_data(self):
        """
        返回默认值
        """
        return {}

    def get_default_columns(self):
        """
        返回默认列
        """
        if self.table._columns:
            return [getattr(self.table, col) for col in self.table._columns if col != self.table._primary_key]

    def _generate_insert(self, insert, ctx):
        rows_iter = iter(insert)
        columns = self._columns

        # Load and organize column defaults (if provided).
        defaults = self.get_default_data()
        value_lookups = {}

        # First figure out what columns are being inserted (if they weren't
        # specified explicitly). Resulting columns are normalized and ordered.
        if not columns:
            try:
                row = next(rows_iter)
            except StopIteration:
                raise self.DefaultValuesException('Error: no rows to insert.')

            if not isinstance(row, dict):
                columns = self.get_default_columns()
                if columns is None:
                    raise ValueError('Bulk insert must specify columns.')
            else:
                # Infer column names from the dict of data being inserted.
                accum = []
                uses_strings = False  # Are the dict keys strings or columns?
                for key in row:
                    if isinstance(key, basestring):
                        column = getattr(self.table, key)
                        uses_strings = True
                    else:
                        column = key
                    accum.append(column)
                    value_lookups[column] = key

                # Add any columns present in the default data that are not
                # accounted for by the dictionary of row data.
                column_set = set(accum)
                for col in (set(defaults) - column_set):
                    accum.append(col)
                    value_lookups[col] = col.name if uses_strings else col

                columns = sorted(accum, key=lambda obj: obj.get_sort_key(ctx))
            rows_iter = itertools.chain(iter((row,)), rows_iter)
        else:
            clean_columns = []
            for column in columns:
                if isinstance(column, basestring):
                    column_obj = getattr(self.table, column)
                else:
                    column_obj = column
                value_lookups[column_obj] = column
                clean_columns.append(column_obj)

            columns = clean_columns
            for col in sorted(defaults, key=lambda obj: obj.get_sort_key(ctx)):
                if col not in value_lookups:
                    columns.append(col)
                    value_lookups[col] = col

        ctx.sql(EnclosedNodeList(columns)).literal(' VALUES ')
        columns_converters = [
            (column, column.db_value if isinstance(column, Field) else None)
            for column in columns]

        all_values = []
        for row in rows_iter:
            values = []
            is_dict = isinstance(row, Mapping)
            for i, (column, converter) in enumerate(columns_converters):
                try:
                    if is_dict:
                        val = row[value_lookups[column]]
                    else:
                        val = row[i]
                except (KeyError, IndexError):
                    if column in defaults:
                        val = defaults[column]
                        if callable_(val):
                            val = val()
                    else:
                        raise ValueError('Missing value for %s.' % column.name)

                if not isinstance(val, Node):
                    val = Value(val, converter=converter, unpack=False)
                values.append(val)

            all_values.append(EnclosedNodeList(values))

        if not all_values:
            raise self.DefaultValuesException('Error: no data to insert.')

        with ctx.scope_values(subquery=True):
            return ctx.sql(CommaNodeList(all_values))

    def _query_insert(self, ctx):
        return (ctx
                .sql(EnclosedNodeList(self._columns))
                .literal(' ')
                .sql(self._insert))

    def _default_values(self, ctx):
        if not self._database:
            return ctx.literal('DEFAULT VALUES')
        return self._database.default_values_insert(ctx)

    def _sql_(self, ctx):
        super(Insert, self)._sql_(ctx)
        with ctx.scope_values():
            stmt = None
            if self._on_conflict is not None:
                stmt = self._on_conflict.get_conflict_statement(ctx, self)

            (ctx
             .sql(stmt or SQL('INSERT'))
             .literal(' INTO ')
             .sql(self.table)
             .literal(' '))

            if isinstance(self._insert, dict) and not self._columns:
                try:
                    self._simple_insert(ctx)
                except self.DefaultValuesException:
                    self._default_values(ctx)
                self._query_type = Insert.SIMPLE
            elif isinstance(self._insert, (SelectQuery, SQL)):
                self._query_insert(ctx)
                self._query_type = Insert.QUERY
            else:
                self._generate_insert(self._insert, ctx)
                self._query_type = Insert.MULTI

            if self._on_conflict is not None:
                update = self._on_conflict.get_conflict_update(ctx, self)
                if update is not None:
                    ctx.literal(' ').sql(update)

            return self.apply_returning(ctx)

    def _execute(self, database):
        if self._returning is None and database.returning_clause \
           and self.table._primary_key:
            self._returning = (self.table._primary_key,)
        try:
            return super(Insert, self)._execute(database)
        except self.DefaultValuesException:
            pass

    def handle_result(self, database, cursor):
        """
        返回 cursor
        """
        if self._return_cursor:
            return cursor
        return database.last_insert_id(cursor, self._query_type)


class Delete(_WriteQuery):
    """
    表示删除的类。
    """
    def _sql_(self, ctx):
        super(Delete, self)._sql_(ctx)

        with ctx.scope_values(subquery=True):
            ctx.literal('DELETE FROM ').sql(self.table)
            if self._where is not None:
                with ctx.scope_normal():
                    ctx.literal(' WHERE ').sql(self._where)

            self._apply_ordering(ctx)
            return self.apply_returning(ctx)


class Index(Node):
    """
    在模型上声明索引的表示方法
    """
    def __init__(self, name, table, expressions, unique=False, safe=False,
                 where=None, using=None):
        """
        name (str) -- 索引名称。
        table (Table) -- 要在其上创建索引的表。
        expressions -- 要索引的列列表（或表达式）。
        unique (bool) -- 索引是否唯一。
        safe (bool) -- 是否添加if not exists子句。
        where (Expression) -- 索引的可选WHERE子句。
        using (str) -- 索引算法。
        """
        self._name = name
        self._table = Entity(table) if not isinstance(table, Table) else table
        self._expressions = expressions
        self._where = where
        self._unique = unique
        self._safe = safe
        self._using = using

    @Node.copy
    def safe(self, _safe=True):
        """
        是否添加 if not exists 子句。
        """
        self._safe = _safe

    @Node.copy
    def where(self, *expressions):
        """
        在索引的 WHERE 子句中包含给定表达式。表达式将与以前指定的任何 where 表达式一起进行和运算。
        """
        if self._where is not None:
            expressions = (self._where,) + expressions
        self._where = reduce(operator.and_, expressions)

    @Node.copy
    def using(self, _using=None):
        """
        为 using 子句指定索引算法。
        """
        self._using = _using

    def _sql_(self, ctx):
        statement = 'CREATE UNIQUE INDEX ' if self._unique else 'CREATE INDEX '
        with ctx.scope_values(subquery=True):
            ctx.literal(statement)
            if self._safe:
                ctx.literal('IF NOT EXISTS ')

            # Sqlite uses CREATE INDEX <schema>.<name> ON <table>, whereas most
            # others use: CREATE INDEX <name> ON <schema>.<table>.
            if ctx.state.index_schema_prefix and \
               isinstance(self._table, Table) and self._table._schema:
                index_name = Entity(self._table._schema, self._name)
                table_name = Entity(self._table.__name__)
            else:
                index_name = Entity(self._name)
                table_name = self._table

            (ctx
             .sql(index_name)
             .literal(' ON ')
             .sql(table_name)
             .literal(' '))
            if self._using is not None:
                ctx.literal('USING %s ' % self._using)

            ctx.sql(EnclosedNodeList([
                SQL(expr) if isinstance(expr, basestring) else expr
                for expr in self._expressions]))
            if self._where is not None:
                ctx.literal(' WHERE ').sql(self._where)

        return ctx


class ModelIndex(Index):
    """
    在模型上声明索引的表示方法。
    """
    def __init__(self, model, fields, unique=False, safe=True, where=None,
                 using=None, name=None):
        self._model = model
        if name is None:
            name = self._generate_name_from_fields(model, fields)
        if using is None:
            for field in fields:
                if isinstance(field, Field) and hasattr(field, 'index_type'):
                    using = field.index_type
        super(ModelIndex, self).__init__(
            name=name,
            table=model._meta.table,
            expressions=fields,
            unique=unique,
            safe=safe,
            where=where,
            using=using)

    def _generate_name_from_fields(self, model, fields):
        accum = []
        for field in fields:
            if isinstance(field, basestring):
                accum.append(field.split()[0])
            else:
                if isinstance(field, Node) and not isinstance(field, Field):
                    field = field.unwrap()
                if isinstance(field, Field):
                    accum.append(field.column_name)

        if not accum:
            raise ValueError('Unable to generate a name for the index, please '
                             'explicitly specify a name.')

        clean_field_names = re.sub(r'[^\w]+', '', '_'.join(accum))
        meta = model._meta
        prefix = meta.name if meta.legacy_table_names else meta.table_name
        return _truncate_constraint_name('_'.join((prefix, clean_field_names)))


def _truncate_constraint_name(constraint, maxlen=64):
    if len(constraint) > maxlen:
        name_hash = hashlib.md5(constraint.encode('utf-8')).hexdigest()
        constraint = '%s_%s' % (constraint[:(maxlen - 8)], name_hash[:7])
    return constraint


# DB-API 2.0 EXCEPTIONS.


class PeeweeException(Exception):
    """
    Peewee Exception 基类
    """
    pass


class ImproperlyConfigured(PeeweeException):
    """
    不正确的配置，比如一些强依赖的库没有引用
    """
    pass


class DatabaseError(PeeweeException):
    """
    数据库异常
    """
    pass


class DataError(DatabaseError):
    """
    数据异常
    """
    pass


class IntegrityError(DatabaseError):
    """
    数据完整性异常
    """
    pass


class InterfaceError(PeeweeException):
    """
    接口异常
    """
    pass


class InternalError(DatabaseError):
    """
    网络异常
    """
    pass


class NotSupportedError(DatabaseError):
    """
    不支持
    """
    pass


class OperationalError(DatabaseError):
    """
    操作异常
    """
    pass


class ProgrammingError(DatabaseError):
    """
    程序异常
    """
    pass


class ExceptionWrapper(object):
    """
    封装异常
    """
    __slots__ = ('exceptions',)

    def __init__(self, exceptions):
        self.exceptions = exceptions

    def __enter__(self): pass

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            return
        # psycopg2.8 shits out a million cute error types. Try to catch em all.
        if pg_errors is not None and exc_type.__name__ not in self.exceptions \
           and issubclass(exc_type, pg_errors.Error):
            exc_type = exc_type.__bases__[0]
        if exc_type.__name__ in self.exceptions:
            new_type = self.exceptions[exc_type.__name__]
            exc_args = exc_value.args
            reraise(new_type, new_type(*exc_args), traceback)


EXCEPTIONS = {
    'ConstraintError': IntegrityError,
    'DatabaseError': DatabaseError,
    'DataError': DataError,
    'IntegrityError': IntegrityError,
    'InterfaceError': InterfaceError,
    'InternalError': InternalError,
    'NotSupportedError': NotSupportedError,
    'OperationalError': OperationalError,
    'ProgrammingError': ProgrammingError}

_exception_wrapper_ = ExceptionWrapper(EXCEPTIONS)


# DATABASE INTERFACE AND CONNECTION MANAGEMENT.


IndexMetadata = collections.namedtuple(
    'IndexMetadata',
    ('name', 'sql', 'columns', 'unique', 'table'))
ColumnMetadata = collections.namedtuple(
    'ColumnMetadata',
    ('name', 'data_type', 'null', 'primary_key', 'table', 'default'))
ForeignKeyMetadata = collections.namedtuple(
    'ForeignKeyMetadata',
    ('column', 'dest_table', 'dest_column', 'table'))
ViewMetadata = collections.namedtuple('ViewMetadata', ('name', 'sql'))


class _ConnectionState(object):
    """
    管理连接状态
    """
    def __init__(self, **kwargs):
        super(_ConnectionState, self).__init__(**kwargs)
        self.reset()

    def reset(self):
        """
        重置连接
        """
        self.closed = True
        self.conn = None
        self.ctx = []
        self.transactions = []

    def set_connection(self, conn):
        """
        设置连接
        """
        self.conn = conn
        self.closed = False
        self.ctx = []
        self.transactions = []


class _ConnectionLocal(_ConnectionState, threading.local):
    """
    在本地线程中存储连接状态时使用，Database 默认行为
    """
    pass


class _NoopLock(object):
    """
    NoopLock
    """
    __slots__ = ()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class ConnectionContext(_CallableContextManager):
    """
    上下文管理器
    """
    __slots__ = ('db',)

    def __init__(self, db):
        self.db = db

    def __enter__(self):
        if self.db.is_closed():
            self.db.connect()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.db.close()


class Database(_CallableContextManager):
    """
    Database 基类
    """
    context_class = Context
    field_types = {}
    operations = {}
    param = '?'
    quote = '""'
    server_version = None

    # Feature toggles.
    commit_select = False
    compound_select_parentheses = CSQ_PARENTHESES_NEVER
    for_update = False
    index_schema_prefix = False
    limit_max = None
    nulls_ordering = False
    returning_clause = False
    safe_create_index = True
    safe_drop_index = True
    sequences = False
    truncate_table = True

    def __init__(self, database, thread_safe=True, autorollback=False,
                 field_types=None, operations=None, autocommit=None,
                 autoconnect=True, **kwargs):
        """
        database (str) -- 数据库名称或文件名
        thread_safe (bool) -- 是否在本地线程中存储连接状态。
        autorollback (bool) -- 在以下情况下自动回滚失败的查询： not 在显式事务中。
        field_types (dict) -- 要支持的其他字段类型的映射。
        operations (dict) -- 要支持的附加操作的映射。
        autoconnect (bool) -- 如果试图对关闭的数据库执行查询，则自动连接到数据库。
        kwargs -- 例如，创建连接时将传递给数据库驱动程序的任意关键字参数 password ， host 等。
        """
        self._field_types = merge_dict(FIELD, self.field_types)
        self._operations = merge_dict(OP, self.operations)
        if field_types:
            self._field_types.update(field_types)
        if operations:
            self._operations.update(operations)

        self.autoconnect = autoconnect
        self.autorollback = autorollback
        self.thread_safe = thread_safe
        if thread_safe:
            self._state = _ConnectionLocal()
            self._lock = threading.Lock()
        else:
            self._state = _ConnectionState()
            self._lock = _NoopLock()

        if autocommit is not None:
            _deprecated_('Peewee no longer uses the "autocommit" option, as '
                           'the semantics now require it to always be True. '
                           'Because some database-drivers also use the '
                           '"autocommit" parameter, you are receiving a '
                           'warning so you may update your code and remove '
                           'the parameter, as in the future, specifying '
                           'autocommit could impact the behavior of the '
                           'database driver you are using.')

        self.connect_params = {}
        self.init(database, **kwargs)

    def init(self, database, **kwargs):
        """
        初始化数据库

        Args:
            database (str) -- 数据库名称或文件名。
            kwargs -- 例如，创建连接时将传递给数据库驱动程序的任意关键字参数 password ， host 等。
        """
        if not self.is_closed():
            self.close()
        self.database = database
        self.connect_params.update(kwargs)
        self.deferred = not bool(database)

    def __enter__(self):
        """
        这个 Database 实例可以用作上下文管理器，在这种情况下，连接将在包装块期间保持打开状态。
        """
        if self.is_closed():
            self.connect()
        ctx = self.atomic()
        self._state.ctx.append(ctx)
        ctx.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        ctx = self._state.ctx.pop()
        try:
            ctx.__exit__(exc_type, exc_val, exc_tb)
        finally:
            if not self._state.ctx:
                self.close()

    def connection_context(self):
        """
        创建一个上下文管理器，该管理器将在包装块期间保持打开连接。
        """
        return ConnectionContext(self)

    def _connect(self):
        raise NotImplementedError

    def connect(self, reuse_if_open=False):
        """
        打开与数据库的连接。

        Args:
            reuse_if_open (bool) -- 如果连接已打开，则不要引发异常。
        Returns:
            是否打开了新连接。
        """
        with self._lock:
            if self.deferred:
                raise InterfaceError('Error, database must be initialized '
                                     'before opening a connection.')
            if not self._state.closed:
                if reuse_if_open:
                    return False
                raise OperationalError('Connection already opened.')

            self._state.reset()
            with _exception_wrapper_:
                self._state.set_connection(self._connect())
                if self.server_version is None:
                    self._set_server_version(self._state.conn)
                self._initialize_connection(self._state.conn)
        return True

    def _initialize_connection(self, conn):
        pass

    def _set_server_version(self, conn):
        self.server_version = 0

    def close(self):
        """
        关闭与数据库的连接。连接是否已关闭。如果数据库已关闭，则返回 False
        """
        with self._lock:
            if self.deferred:
                raise InterfaceError('Error, database must be initialized '
                                     'before opening a connection.')
            if self.in_transaction():
                raise OperationalError('Attempting to close database while '
                                       'transaction is open.')
            is_open = not self._state.closed
            try:
                if is_open:
                    with _exception_wrapper_:
                        self._close(self._state.conn)
            finally:
                self._state.reset()
            return is_open

    def _close(self, conn):
        conn.close()

    def is_closed(self):
        """
        返回数据库连接是否关闭
        """
        return self._state.closed

    def connection(self):
        """
        返回打开的连接。如果连接未打开，将打开一个连接。连接将是基础数据库驱动程序用来封装数据库连接的任何内容。
        """
        if self.is_closed():
            self.connect()
        return self._state.conn

    def cursor(self, commit=None):
        """
        返回 cursor 当前连接上的对象。
        如果连接未打开，将打开一个连接。

        光标将是基础数据库驱动程序用来封装数据库光标的任何对象。

        Args:
            commit -- 供内部使用。
        """
        if self.is_closed():
            if self.autoconnect:
                self.connect()
            else:
                raise InterfaceError('Error, database connection not opened.')
        return self._state.conn.cursor()

    def execute_sql(self, sql, params=None, commit=None):
        """
        执行一个 SQL 查询并在结果上返回一个光标。

        Args;
            sql (str) -- 要执行的SQL字符串。
            params (tuple) -- 用于查询的参数。
            commit -- 用于重写默认提交逻辑的布尔标志。
        Returns:
            游标对象。
        """
        logger.debug((sql, params))
        if commit is None:
            commit = SENTINEL

        if commit is SENTINEL:
            if self.in_transaction():
                commit = False
            elif self.commit_select:
                commit = True
            else:
                commit = not sql[:6].lower().startswith('select')

        with _exception_wrapper_:
            cursor = self.cursor(commit)
            try:
                cursor.execute(sql, params or ())
            except Exception:
                if self.autorollback and not self.in_transaction():
                    self.rollback()
                raise
            else:
                if commit and not self.in_transaction():
                    self.commit()
        return cursor

    def execute(self, query, commit=None, **context_options):
        """
        通过编译 Query 实例并执行生成的SQL。

        Args:
            query -- A Query 实例。
            commit -- 用于重写默认提交逻辑的布尔标志。
            context_options -- 传递给SQL生成器的任意选项。
        Returns:
            游标对象。
        """
        if commit is None:
            commit = SENTINEL

        ctx = self.get_sql_context(**context_options)
        sql, params = ctx.sql(query).query()
        return self.execute_sql(sql, params, commit=commit)

    def get_context_options(self):
        """
        获取 context 参数
        """
        return {
            'field_types': self._field_types,
            'operations': self._operations,
            'param': self.param,
            'quote': self.quote,
            'compound_select_parentheses': self.compound_select_parentheses,
            'conflict_statement': self.conflict_statement,
            'conflict_update': self.conflict_update,
            'for_update': self.for_update,
            'index_schema_prefix': self.index_schema_prefix,
            'limit_max': self.limit_max,
            'nulls_ordering': self.nulls_ordering,
        }

    def get_sql_context(self, **context_options):
        """
        获取 sql context
        """
        context = self.get_context_options()
        if context_options:
            context.update(context_options)
        return self.context_class(**context)

    def conflict_statement(self, on_conflict, query):
        """
        未实现
        """
        raise NotImplementedError

    def conflict_update(self, on_conflict, query):
        """
        未实现
        """
        raise NotImplementedError

    def _build_on_conflict_update(self, on_conflict, query):
        if on_conflict._conflict_target:
            stmt = SQL('ON CONFLICT')
            target = EnclosedNodeList([
                Entity(col) if isinstance(col, basestring) else col
                for col in on_conflict._conflict_target])
            if on_conflict._conflict_where is not None:
                target = NodeList([target, SQL('WHERE'),
                                   on_conflict._conflict_where])
        else:
            stmt = SQL('ON CONFLICT ON CONSTRAINT')
            target = on_conflict._conflict_constraint
            if isinstance(target, basestring):
                target = Entity(target)

        updates = []
        if on_conflict._preserve:
            for column in on_conflict._preserve:
                excluded = NodeList((SQL('EXCLUDED'), ensure_entity(column)),
                                    glue='.')
                expression = NodeList((ensure_entity(column), SQL('='),
                                       excluded))
                updates.append(expression)

        if on_conflict._update:
            for k, v in on_conflict._update.items():
                if not isinstance(v, Node):
                    # Attempt to resolve string field-names to their respective
                    # field object, to apply data-type conversions.
                    if isinstance(k, basestring):
                        k = getattr(query.table, k)
                    converter = k.db_value if isinstance(k, Field) else None
                    v = Value(v, converter=converter, unpack=False)
                else:
                    v = QualifiedNames(v)
                updates.append(NodeList((ensure_entity(k), SQL('='), v)))

        parts = [stmt, target, SQL('DO UPDATE SET'), CommaNodeList(updates)]
        if on_conflict._where:
            parts.extend((SQL('WHERE'), QualifiedNames(on_conflict._where)))

        return NodeList(parts)

    def last_insert_id(self, cursor, query_type=None):
        """
        最后插入行的主键。
        """
        return cursor.lastrowid

    def rows_affected(self, cursor):
        """
        查询修改的行数。

        Args;
            cursor -- 游标对象。
        Returns:
            修改的行数
        """
        return cursor.rowcount

    def default_values_insert(self, ctx):
        """
        插入默认值
        """
        return ctx.literal('DEFAULT VALUES')

    def session_start(self):
        """
        开始新事务

        建议使用 Database.atomic()  进行事务管理
        """
        with self._lock:
            return self.transaction().__enter__()

    def session_commit(self):
        """
        提交在以开始的事务期间所做的任何更改
        """
        with self._lock:
            try:
                txn = self.pop_transaction()
            except IndexError:
                return False
            txn.commit(begin=self.in_transaction())
            return True

    def session_rollback(self):
        """
        回滚在以开始的事务期间所做的任何更改
        """
        with self._lock:
            try:
                txn = self.pop_transaction()
            except IndexError:
                return False
            txn.rollback(begin=self.in_transaction())
            return True

    def in_transaction(self):
        """
        Returns:
            事务当前是否打开(bool)
        """
        return bool(self._state.transactions)

    def push_transaction(self, transaction):
        """
        添加事务
        """
        self._state.transactions.append(transaction)

    def pop_transaction(self):
        """
        pop 事务
        """
        return self._state.transactions.pop()

    def transaction_depth(self):
        """
        事务深度
        """
        return len(self._state.transactions)

    def top_transaction(self):
        """
        返回列表末尾事务
        """
        if self._state.transactions:
            return self._state.transactions[-1]

    def atomic(self):
        """
        创建一个上下文管理器，在事务中运行包装块中的任何查询（如果块嵌套，则保存点）。
        """
        return _atomic(self)

    def manual_commit(self):
        """
        创建一个上下文管理器，在包装块期间禁用所有事务管理。
        """
        return _manual(self)

    def transaction(self):
        """
        创建一个上下文管理器，用于运行事务中包装块中的所有查询。
        """
        return _transaction(self)

    def savepoint(self):
        """
        创建一个上下文管理器，运行保存点中包装块中的所有查询。保存点可以任意嵌套。
        """
        return _savepoint(self)

    def begin(self):
        """
        使用手动提交模式时启动事务。
        """
        if self.is_closed():
            self.connect()

    def commit(self):
        """
        手动提交当前活动的事务。
        """
        return self._state.conn.commit()

    def rollback(self):
        """
        手动回滚当前活动的事务。
        """
        return self._state.conn.rollback()

    def batch_commit(self, it, n):
        """
        此方法的目的是简化批处理大型操作，如插入、更新等

        Args:
            it (iterable) -- 将生成其项的iterable。
            n (int) -- 每一个承诺 n 项目。
        """
        for group in chunked(it, n):
            with self.atomic():
                for obj in group:
                    yield obj

    def table_exists(self, table_name, schema=None):
        """
        表是否存在

        Args:
            table (str) -- 表名。
            schema (str) -- 架构名称（可选）。
        Returns:
            bool
        """
        return table_name in self.get_tables(schema=schema)

    def get_tables(self, schema=None):
        """
        数据库中的表名列表。

        Args:
            schema (str) -- 架构名称（可选）。
        """
        raise NotImplementedError

    def get_indexes(self, table, schema=None):
        """
        返回的列表 IndexMetadata 元组。

        Args:
            table (str) -- 表名。
            schema (str) -- 架构名称（可选）。
        """
        raise NotImplementedError

    def get_columns(self, table, schema=None):
        """
        返回的列表 ColumnMetadata 元组。

        Args:
            table (str) -- 表名。
            schema (str) -- 架构名称（可选）。
        """
        raise NotImplementedError

    def get_primary_keys(self, table, schema=None):
        """
        返回包含主键的列名列表。

        Args:
            table (str) -- 表名。
            schema (str) -- 架构名称（可选）。
        """
        raise NotImplementedError

    def get_foreign_keys(self, table, schema=None):
        """
        返回的列表 ForeignKeyMetadata 表中存在键的元组。

        Args:
            table (str) -- 表名。
            schema (str) -- 架构名称（可选）。
        """
        raise NotImplementedError

    def sequence_exists(self, seq):
        """
        Args:
            seq (str) -- 序列的名称。
        Returns:
            序列是否存在。(bool)
        """
        raise NotImplementedError

    def create_tables(self, models, **options):
        """
        为给定的模型列表创建表、索引和关联的元数据。

        Args:
            models (list) -- 列表 Model 类。
            options -- 调用时要指定的选项 Model.create_table() .
        """
        for model in sort_models(models):
            model.create_table(**options)

    def drop_tables(self, models, **kwargs):
        """
        删除给定模型列表的表、索引和相关元数据。

        Args:
            models (list) -- 列表 Model 类。
            kwargs -- 调用时要指定的选项 Model.drop_table() .
        """
        for model in reversed(sort_models(models)):
            model.drop_table(**kwargs)

    def extract_date(self, date_part, date_field):
        """
        提供用于提取日期时间部分的兼容接口。

        Args:
            date_part (str) -- 要提取的日期部分，例如“年份”。
            date_field (Node) -- 包含日期/时间的SQL节点，例如 DateTimeField
        """
        raise NotImplementedError

    def truncate_date(self, date_part, date_field):
        """
        提供一个兼容的接口，用于将日期时间截断为给定的部分。

        Args:
            date_part (str) -- 要截断到的日期部分，例如“day”。
            date_field (Node) -- 包含日期/时间的SQL节点，例如 DateTimeField
        """
        raise NotImplementedError

    def to_timestamp(self, date_field):
        """
        返回一个特定于数据库的函数调用，该函数调用允许使用给定的日期时间值作为数字时间戳。
        这有时可以以兼容的方式简化日期数学之类的任务。
        """
        raise NotImplementedError

    def from_timestamp(self, date_field):
        """
        未实现
        """
        raise NotImplementedError

    def random(self):
        """
        表示返回随机值的函数调用的 SQL 节点。
        """
        return fn.random()

    def bind(self, models, bind_refs=True, bind_backrefs=True):
        """
        将给定的模型列表和指定的关系绑定到数据库。

        Args:
            models (list) -- 一个或多个 Model 要绑定的类。
            bind_refs (bool) -- 绑定相关模型。
            bind_backrefs (bool) -- 绑定与引用相关的模型。
        """
        for model in models:
            model.bind(self, bind_refs=bind_refs, bind_backrefs=bind_backrefs)

    def bind_ctx(self, models, bind_refs=True, bind_backrefs=True):
        """
        创建一个上下文管理器，在包装块期间将给定模型与当前数据库绑定（关联）

        Args:
            models (list) -- 要绑定到数据库的模型列表。
            bind_refs (bool) -- 绑定使用外键引用的模型。
            bind_backrefs (bool) -- 用外键绑定引用给定模型的模型。
        """
        return _BoundModelsContext(models, self, bind_refs, bind_backrefs)

    def get_noop_select(self, ctx):
        """
        执行 SQL
        """
        return ctx.sql(Select().columns(SQL('0')).where(SQL('0')))


def _pragma_(name):
    """
    Sqlite 使用
    """
    def __get__(self):
        return self.pragma(name)

    def __set__(self, value):
        return self.pragma(name, value)
    return property(__get__, __set__)


class SqliteDatabase(Database):
    """
    sqlite 数据库实现
    """
    field_types = {
        'BIGAUTO': FIELD.AUTO,
        'BIGINT': FIELD.INT,
        'BOOL': FIELD.INT,
        'DOUBLE': FIELD.FLOAT,
        'SMALLINT': FIELD.INT,
        'UUID': FIELD.TEXT}
    operations = {
        'LIKE': 'GLOB',
        'ILIKE': 'LIKE'}
    index_schema_prefix = True
    limit_max = -1
    server_version = _sqlite_version_
    truncate_table = False

    def __init__(self, database, *args, **kwargs):
        self._pragmas = kwargs.pop('pragmas', ())
        super(SqliteDatabase, self).__init__(database, *args, **kwargs)
        self._aggregates = {}
        self._collations = {}
        self._functions = {}
        self._window_functions = {}
        self._table_functions = []
        self._extensions = set()
        self._attached = {}
        self.register_function(_sqlite_date_part, 'date_part', 2)
        self.register_function(_sqlite_date_trunc, 'date_trunc', 2)

    def init(self, database, pragmas=None, timeout=5, **kwargs):
        """
        初始化数据库
        """
        if pragmas is not None:
            self._pragmas = pragmas
        if isinstance(self._pragmas, dict):
            self._pragmas = list(self._pragmas.items())
        self._timeout = timeout
        super(SqliteDatabase, self).init(database, **kwargs)

    def _set_server_version(self, conn):
        pass

    def _connect(self):
        if sqlite3 is None:
            raise ImproperlyConfigured('SQLite driver not installed!')
        conn = sqlite3.connect(self.database, timeout=self._timeout,
                               isolation_level=None, **self.connect_params)
        try:
            self._add_conn_hooks(conn)
        except BaseException:
            conn.close()
            raise
        return conn

    def _add_conn_hooks(self, conn):
        if self._attached:
            self._attach_databases(conn)
        if self._pragmas:
            self._set_pragmas(conn)
        self._load_aggregates(conn)
        self._load_collations(conn)
        self._load_functions(conn)
        if self.server_version >= (3, 25, 0):
            self._load_window_functions(conn)
        if self._table_functions:
            for table_function in self._table_functions:
                table_function.register(conn)
        if self._extensions:
            self._load_extensions(conn)

    def _set_pragmas(self, conn):
        cursor = conn.cursor()
        for pragma, value in self._pragmas:
            cursor.execute('PRAGMA %s = %s;' % (pragma, value))
        cursor.close()

    def _attach_databases(self, conn):
        cursor = conn.cursor()
        for name, db in self._attached.items():
            cursor.execute('ATTACH DATABASE "%s" AS "%s"' % (db, name))
        cursor.close()

    def pragma(self, key, value=None, permanent=False, schema=None):
        """
        对活动连接执行一次 pragma 查询。如果未指定值，则返回当前值。

        Args:
            key -- 设置名称。
            value -- 设置的新值（可选）。
            permanent -- 每次打开连接时应用此pragma。
        """
        if value is None:
            value = SENTINEL

        if schema is not None:
            key = '"%s".%s' % (schema, key)
        sql = 'PRAGMA %s' % key
        if value is not SENTINEL:
            sql += ' = %s' % (value or 0)
            if permanent:
                pragmas = dict(self._pragmas or ())
                pragmas[key] = value
                self._pragmas = list(pragmas.items())
        elif permanent:
            raise ValueError('Cannot specify a permanent pragma without value')
        row = self.execute_sql(sql).fetchone()
        if row:
            return row[0]

    # 获取或设置当前连接的缓存大小 pragma。
    cache_size = _pragma_('cache_size')
    # 获取或设置当前连接的外键 pragma
    foreign_keys = _pragma_('foreign_keys')
    # 获取或设置日志模式 pragma
    journal_mode = _pragma_('journal_mode')
    # 获取或设置日志大小限制 pragma
    journal_size_limit = _pragma_('journal_size_limit')
    # 获取或设置当前连接的 mmap-size pragma
    mmap_size = _pragma_('mmap_size')
    # 获取或设置页面大小 pragma
    page_size = _pragma_('page_size')
    # 获取或设置当前连接的 read_uncommitted pragma
    read_uncommitted = _pragma_('read_uncommitted')
    # 获取或设置当前连接的同步 pragma
    synchronous = _pragma_('synchronous')
    # 获取或设置当前连接的 wal-autocheckpoint pragma
    wal_autocheckpoint = _pragma_('wal_autocheckpoint')

    @property
    def timeout(self):
        """
        获取超时（秒）
        """
        return self._timeout

    @timeout.setter
    def timeout(self, seconds):
        """
        设置超时
        """
        if self._timeout == seconds:
            return

        self._timeout = seconds
        if not self.is_closed():
            # PySQLite multiplies user timeout by 1000, but the unit of the
            # timeout PRAGMA is actually milliseconds.
            self.execute_sql('PRAGMA busy_timeout=%d;' % (seconds * 1000))

    def _load_aggregates(self, conn):
        for name, (klass, num_params) in self._aggregates.items():
            conn.create_aggregate(name, num_params, klass)

    def _load_collations(self, conn):
        for name, fn in self._collations.items():
            conn.create_collation(name, fn)

    def _load_functions(self, conn):
        for name, (fn, num_params) in self._functions.items():
            conn.create_function(name, num_params, fn)

    def _load_window_functions(self, conn):
        for name, (klass, num_params) in self._window_functions.items():
            conn.create_window_function(name, num_params, klass)

    def register_aggregate(self, klass, name=None, num_params=-1):
        """
        注册用户定义的聚合函数。每次打开新连接时都会注册该函数。
        如果一个连接已经打开，那么聚合将注册到打开的连接中。

        Args:
            klass -- 实现聚合API的类。
            name (str) -- 聚合函数名（默认为类名）。
            num_params (int) -- 聚合接受的参数个数，或-1表示任何数字。
        """
        self._aggregates[name or klass.__name__.lower()] = (klass, num_params)
        if not self.is_closed():
            self._load_aggregates(self.connection())

    def aggregate(self, name=None, num_params=-1):
        """
        类修饰器注册用户定义的聚合函数。

        Args:
            name (str) -- 聚合的名称（默认为类名）。
            num_params (int) -- 聚合接受的参数个数，或-1表示任何数字。
        """
        def decorator(klass):
            """
            decorator
            """
            self.register_aggregate(klass, name, num_params)
            return klass
        return decorator

    def register_collation(self, fn, name=None):
        """
        注册用户定义的排序规则。每次打开新连接时都会注册排序规则。
        如果连接已打开，则排序规则将注册到打开的连接。

        Args:
            fn -- 排序规则函数。
            name (str) -- 排序规则名称（默认为函数名）
        """
        name = name or fn.__name__

        def _collation(*args):
            expressions = args + (SQL('collate %s' % name),)
            return NodeList(expressions)
        fn.collation = _collation
        self._collations[name] = fn
        if not self.is_closed():
            self._load_collations(self.connection())

    def collation(self, name=None):
        """
        decorator 注册用户定义的排序规则。

        Args:
            name (str) -- 排序规则名称（默认为函数名）
        """
        def decorator(fn):
            """
            decorator
            """
            self.register_collation(fn, name)
            return fn
        return decorator

    def register_function(self, fn, name=None, num_params=-1):
        """
        注册用户定义的标量函数。每次打开新连接时都会注册该函数。
        此外，如果连接已打开，则该函数将注册为打开的连接。

        Args:
            fn -- 用户定义的标量函数。
            name (str) -- 函数名（默认为函数名）
            num_params (int) -- 函数接受的参数个数，或-1表示任何数字。
        """
        self._functions[name or fn.__name__] = (fn, num_params)
        if not self.is_closed():
            self._load_functions(self.connection())

    def func(self, name=None, num_params=-1):
        """
        decorator 注册用户定义的标量函数。

        Args:
            name (str) -- 函数名（默认为函数名）。
            num_params (int) -- 函数接受的参数个数，或-1表示任何数字。
        """
        def decorator(fn):
            """
            decorator
            """
            self.register_function(fn, name, num_params)
            return fn
        return decorator

    def register_window_function(self, klass, name=None, num_params=-1):
        """
        注册用户定义的窗口函数。(此功能需要sqlite>=3.25.0 and pysqlite3 ＞0.2.0)

        Args:
            klass -- 实现窗口函数 API 的类。
            name (str) -- 窗口函数名（默认为类名）。
            num_params (int) -- 函数接受的参数个数，或 -1 表示任何数字。
        """
        name = name or klass.__name__.lower()
        self._window_functions[name] = (klass, num_params)
        if not self.is_closed():
            self._load_window_functions(self.connection())

    def window_function(self, name=None, num_params=-1):
        """
        类decorator注册用户定义的窗口函数。窗口函数必须定义以下方法：
        * step(<params>) -从行接收值并更新状态。
        * inverse(<params>) -逆 step() 对于给定的值。
        * value() -返回window函数的当前值。
        * finalize() -返回window函数的最终值。

        Args:
            name (str) -- 窗口函数的名称（默认为类名）。
            num_params (int) -- 函数接受的参数个数，或-1表示任何数字。
        """
        def decorator(klass):
            """
            decorator
            """
            self.register_window_function(klass, name, num_params)
            return klass
        return decorator

    def register_table_function(self, klass, name=None):
        """
        注册 table function
        """
        if name is not None:
            klass.name = name
        self._table_functions.append(klass)
        if not self.is_closed():
            klass.register(self.connection())

    def table_function(self, name=None):
        """
        用于注册的类修饰符 TableFunction . 表函数是用户定义的函数，它不是返回单个标量值，而是返回任意数量的表格数据行。
        """
        def decorator(klass):
            """
            decorator
            """
            self.register_table_function(klass, name)
            return klass
        return decorator

    def unregister_aggregate(self, name):
        """
        注销用户定义的聚合函数。

        Args:
            name -- 用户定义的聚合函数的名称。
        """
        del(self._aggregates[name])

    def unregister_collation(self, name):
        """
        注销用户定义的排序规则。

        Args:
            name -- 用户定义的排序规则的名称。
        """
        del(self._collations[name])

    def unregister_function(self, name):
        """
        注销用户定义的标量函数。
        """
        del(self._functions[name])

    def unregister_window_function(self, name):
        """
        注销 window 函数
        """
        del(self._window_functions[name])

    def unregister_table_function(self, name):
        """
        注销用户定义的标量函数。判断对错，取决于函数是否被删除。
        """
        for idx, klass in enumerate(self._table_functions):
            if klass.name == name:
                break
        else:
            return False
        self._table_functions.pop(idx)
        return True

    def _load_extensions(self, conn):
        conn.enable_load_extension(True)
        for extension in self._extensions:
            conn.load_extension(extension)

    def load_extension(self, extension):
        """
        加载给定的 C 扩展。如果调用线程中当前打开了一个连接，那么将为该连接以及所有后续连接加载扩展。
        """
        self._extensions.add(extension)
        if not self.is_closed():
            conn = self.connection()
            conn.enable_load_extension(True)
            conn.load_extension(extension)

    def unload_extension(self, extension):
        """
        移除指定的 C 扩展
        """
        self._extensions.remove(extension)

    def attach(self, filename, name):
        """
        注册另一个将附加到每个数据库连接的数据库文件。如果主数据库当前已连接，则新数据库将附加到打开的连接上。

        Args:
            filename (str) -- 要附加的数据库
            name (str) -- 附加数据库的架构名称。
        """
        if name in self._attached:
            if self._attached[name] == filename:
                return False
            raise OperationalError('schema "%s" already attached.' % name)

        self._attached[name] = filename
        if not self.is_closed():
            self.execute_sql('ATTACH DATABASE "%s" AS "%s"' % (filename, name))
        return True

    def detach(self, name):
        """
        注销以前通过调用附加的另一个数据库文件 attach()

        Args:
            name (str) -- 附加数据库的架构名称。
        Returns:
            bool
        """
        if name not in self._attached:
            return False

        del self._attached[name]
        if not self.is_closed():
            self.execute_sql('DETACH DATABASE "%s"' % name)
        return True

    def atomic(self, lock_type=None):
        """
        创建一个上下文管理器，在事务中运行包装块中的任何查询（如果块嵌套，则保存点）
        """
        return _atomic(self, lock_type=lock_type)

    def transaction(self, lock_type=None):
        """
        创建一个上下文管理器，用于运行事务中包装块中的所有查询。
        """
        return _transaction(self, lock_type=lock_type)

    def begin(self, lock_type=None):
        """
        使用手动提交模式时启动事务。
        """
        statement = 'BEGIN %s' % lock_type if lock_type else 'BEGIN'
        self.execute_sql(statement, commit=False)

    def get_tables(self, schema=None):
        """
        数据库中的表名列表。

        Args:
            schema (str) -- 架构名称（可选）。
        """
        schema = schema or 'main'
        cursor = self.execute_sql('SELECT name FROM "%s".sqlite_master WHERE '
                                  'type=? ORDER BY name' % schema, ('table',))
        return [row for row, in cursor.fetchall()]

    def get_views(self, schema=None):
        """
        返回的列表 ViewMetadata 数据库中存在的视图的元组。

        Args:
            schema (str) -- 架构名称（可选）
        """
        sql = ('SELECT name, sql FROM "%s".sqlite_master WHERE type=? '
               'ORDER BY name') % (schema or 'main')
        return [ViewMetadata(*row) for row in self.execute_sql(sql, ('view',))]

    def get_indexes(self, table, schema=None):
        """
        返回的列表 IndexMetadata 元组。

        Args:
            table (str) -- 表名。
            schema (str) -- 架构名称（可选）。
        """
        schema = schema or 'main'
        query = ('SELECT name, sql FROM "%s".sqlite_master '
                 'WHERE tbl_name = ? AND type = ? ORDER BY name') % schema
        cursor = self.execute_sql(query, (table, 'index'))
        index_to_sql = dict(cursor.fetchall())

        # Determine which indexes have a unique constraint.
        unique_indexes = set()
        cursor = self.execute_sql('PRAGMA "%s".index_list("%s")' %
                                  (schema, table))
        for row in cursor.fetchall():
            name = row[1]
            is_unique = int(row[2]) == 1
            if is_unique:
                unique_indexes.add(name)

        # Retrieve the indexed columns.
        index_columns = {}
        for index_name in sorted(index_to_sql):
            cursor = self.execute_sql('PRAGMA "%s".index_info("%s")' %
                                      (schema, index_name))
            index_columns[index_name] = [row[2] for row in cursor.fetchall()]

        return [IndexMetadata(name, index_to_sql[name], index_columns[name], name in unique_indexes, table)
            for name in sorted(index_to_sql)]

    def get_columns(self, table, schema=None):
        """
        返回的列表 ColumnMetadata 元组。

        Args:
            table (str) -- 表名。
            schema (str) -- 架构名称（可选）。
        """
        cursor = self.execute_sql('PRAGMA "%s".table_info("%s")' %
                                  (schema or 'main', table))
        return [ColumnMetadata(r[1], r[2], not r[3], bool(r[5]), table, r[4])
                for r in cursor.fetchall()]

    def get_primary_keys(self, table, schema=None):
        """
        返回包含主键的列名列表。

        Args:
            table (str) -- 表名。
            schema (str) -- 架构名称（可选）。
        """
        cursor = self.execute_sql('PRAGMA "%s".table_info("%s")' %
                                  (schema or 'main', table))
        return [row[1] for row in filter(lambda r: r[-1], cursor.fetchall())]

    def get_foreign_keys(self, table, schema=None):
        """
        返回的列表 ForeignKeyMetadata 表中存在键的元组。

        Args:
            table (str) -- 表名。
            schema (str) -- 架构名称（可选）。
        """
        cursor = self.execute_sql('PRAGMA "%s".foreign_key_list("%s")' %
                                  (schema or 'main', table))
        return [ForeignKeyMetadata(row[3], row[2], row[4], table)
                for row in cursor.fetchall()]

    def get_binary_type(self):
        """
        获取 binary 类型
        """
        return sqlite3.Binary

    def conflict_statement(self, on_conflict, query):
        """
        冲突状态
        """
        action = on_conflict._action.lower() if on_conflict._action else ''
        if action and action not in ('nothing', 'update'):
            return SQL('INSERT OR %s' % on_conflict._action.upper())

    def conflict_update(self, oc, query):
        """
        # Sqlite prior to 3.24.0 does not support Postgres-style upsert.
        """
        if self.server_version < (3, 24, 0) and \
           any((oc._preserve, oc._update, oc._where, oc._conflict_target,
                oc._conflict_constraint)):
            raise ValueError('SQLite does not support specifying which values '
                             'to preserve or update.')

        action = oc._action.lower() if oc._action else ''
        if action and action not in ('nothing', 'update', ''):
            return

        if action == 'nothing':
            return SQL('ON CONFLICT DO NOTHING')
        elif not oc._update and not oc._preserve:
            raise ValueError('If you are not performing any updates (or '
                             'preserving any INSERTed values), then the '
                             'conflict resolution action should be set to '
                             '"NOTHING".')
        elif oc._conflict_constraint:
            raise ValueError('SQLite does not support specifying named '
                             'constraints for conflict resolution.')
        elif not oc._conflict_target:
            raise ValueError('SQLite requires that a conflict target be '
                             'specified when doing an upsert.')

        return self._build_on_conflict_update(oc, query)

    def extract_date(self, date_part, date_field):
        """
        提供用于提取日期时间部分的兼容接口。

        Args:
            date_part (str) -- 要提取的日期部分，例如“年份”。
            date_field (Node) -- 包含日期/时间的SQL节点，例如 DateTimeField
        """
        return fn.date_part(date_part, date_field, python_value=int)

    def truncate_date(self, date_part, date_field):
        """
        提供一个兼容的接口，用于将日期时间截断为给定的部分

        Args:
            date_part (str) -- 要截断到的日期部分，例如“day”。
            date_field (Node) -- 包含日期/时间的SQL节点，例如 DateTimeField
        """
        return fn.date_trunc(date_part, date_field,
                             python_value=simple_date_time)

    def to_timestamp(self, date_field):
        """
        返回一个特定于数据库的函数调用，该函数调用允许使用给定的日期时间值作为数字时间戳。
        这有时可以以兼容的方式简化日期数学之类的任务。
        """
        return fn.strftime('%s', date_field).cast('integer')

    def from_timestamp(self, date_field):
        """
        处理时间戳
        """
        return fn.datetime(date_field, 'unixepoch')


class MySQLDatabase(Database):
    """
    MySQL 数据库实现
    """
    field_types = {
        'AUTO': 'INTEGER AUTO_INCREMENT',
        'BIGAUTO': 'BIGINT AUTO_INCREMENT',
        'BOOL': 'BOOL',
        'DECIMAL': 'NUMERIC',
        'DOUBLE': 'DOUBLE PRECISION',
        'FLOAT': 'FLOAT',
        'UUID': 'VARCHAR(40)',
        'UUIDB': 'VARBINARY(16)'}
    operations = {
        'LIKE': 'LIKE BINARY',
        'ILIKE': 'LIKE',
        'REGEXP': 'REGEXP BINARY',
        'IREGEXP': 'REGEXP',
        'XOR': 'XOR'}
    param = '%s'
    quote = '``'

    commit_select = True
    compound_select_parentheses = CSQ_PARENTHESES_UNNESTED
    for_update = True
    limit_max = 2 ** 64 - 1
    safe_create_index = False
    safe_drop_index = False

    def init(self, database, **kwargs):
        """
        初始化数据库
        """
        params = {'charset': 'utf8', 'use_unicode': True}
        params.update(kwargs)
        if 'password' in params and mysql_passwd:
            params['passwd'] = params.pop('password')
        super(MySQLDatabase, self).init(database, **params)

    def _connect(self):
        if mysql is None:
            raise ImproperlyConfigured('MySQL driver not installed!')
        conn = mysql.connect(db=self.database, **self.connect_params)
        return conn

    def _set_server_version(self, conn):
        try:
            version_raw = conn.server_version
        except AttributeError:
            version_raw = conn.get_server_info()
        self.server_version = self._extract_server_version(version_raw)

    def _extract_server_version(self, version):
        version = version.lower()
        if 'maria' in version:
            match_obj = re.search(r'(1\d\.\d+\.\d+)', version)
        else:
            match_obj = re.search(r'(\d\.\d+\.\d+)', version)
        if match_obj is not None:
            return tuple(int(num) for num in match_obj.groups()[0].split('.'))

        warnings.warn('Unable to determine MySQL version: "%s"' % version)
        return (0, 0, 0)  # Unable to determine version!

    def default_values_insert(self, ctx):
        return ctx.literal('() VALUES ()')

    def get_tables(self, schema=None):
        """
        数据库中的表名列表。

        Args:
            schema (str) -- 架构名称（可选）。
        """
        query = ('SELECT table_name FROM information_schema.tables '
                 'WHERE table_schema = DATABASE() AND table_type != %s '
                 'ORDER BY table_name')
        return [table for table, in self.execute_sql(query, ('VIEW',))]

    def get_views(self, schema=None):
        """
        返回的列表 ViewMetadata 数据库中存在的视图的元组。

        Args:
            schema (str) -- 架构名称（可选）
        """
        query = ('SELECT table_name, view_definition '
                 'FROM information_schema.views '
                 'WHERE table_schema = DATABASE() ORDER BY table_name')
        cursor = self.execute_sql(query)
        return [ViewMetadata(*row) for row in cursor.fetchall()]

    def get_indexes(self, table, schema=None):
        """
        返回的列表 IndexMetadata 元组。

        Args:
            table (str) -- 表名。
            schema (str) -- 架构名称（可选）。
        """
        cursor = self.execute_sql('SHOW INDEX FROM `%s`' % table)
        unique = set()
        indexes = {}
        for row in cursor.fetchall():
            if not row[1]:
                unique.add(row[2])
            indexes.setdefault(row[2], [])
            indexes[row[2]].append(row[4])
        return [IndexMetadata(name, None, indexes[name], name in unique, table)
                for name in indexes]

    def get_columns(self, table, schema=None):
        """
        返回的列表 ColumnMetadata 元组。

        Args:
            table (str) -- 表名。
            schema (str) -- 架构名称（可选）。
        """
        sql = """
            SELECT column_name, is_nullable, data_type, column_default
            FROM information_schema.columns
            WHERE table_name = %s AND table_schema = DATABASE()"""
        cursor = self.execute_sql(sql, (table,))
        pks = set(self.get_primary_keys(table))
        return [ColumnMetadata(name, dt, null == 'YES', name in pks, table, df)
                for name, null, dt, df in cursor.fetchall()]

    def get_primary_keys(self, table, schema=None):
        """
        返回包含主键的列名列表。

        Args:
            table (str) -- 表名。
            schema (str) -- 架构名称（可选）。
        """
        cursor = self.execute_sql('SHOW INDEX FROM `%s`' % table)
        return [row[4] for row in filter(lambda row: row[2] == 'PRIMARY', cursor.fetchall())]

    def get_foreign_keys(self, table, schema=None):
        """
        返回的列表 ForeignKeyMetadata 表中存在键的元组。

        Args:
            table (str) -- 表名。
            schema (str) -- 架构名称（可选）。
        """
        query = """
            SELECT column_name, referenced_table_name, referenced_column_name
            FROM information_schema.key_column_usage
            WHERE table_name = %s
                AND table_schema = DATABASE()
                AND referenced_table_name IS NOT NULL
                AND referenced_column_name IS NOT NULL"""
        cursor = self.execute_sql(query, (table,))
        return [
            ForeignKeyMetadata(column, dest_table, dest_column, table)
            for column, dest_table, dest_column in cursor.fetchall()]

    def get_binary_type(self):
        """
        获取 binary 类型
        """
        return mysql.Binary

    def conflict_statement(self, on_conflict, query):
        """
        冲突状态
        """
        if not on_conflict._action:
            return

        action = on_conflict._action.lower()
        if action == 'replace':
            return SQL('REPLACE')
        elif action == 'ignore':
            return SQL('INSERT IGNORE')
        elif action != 'update':
            raise ValueError('Un-supported action for conflict resolution. '
                             'MySQL supports REPLACE, IGNORE and UPDATE.')

    def conflict_update(self, on_conflict, query):
        """
        conflict_update
        """
        if on_conflict._where or on_conflict._conflict_target or \
           on_conflict._conflict_constraint:
            raise ValueError('MySQL does not support the specification of '
                             'where clauses or conflict targets for conflict '
                             'resolution.')

        updates = []
        if on_conflict._preserve:
            # Here we need to determine which function to use, which varies
            # depending on the MySQL server version. MySQL and MariaDB prior to
            # 10.3.3 use "VALUES", while MariaDB 10.3.3+ use "VALUE".
            version = self.server_version or (0,)
            if version[0] == 10 and version >= (10, 3, 3):
                VALUE_FN = fn.VALUE
            else:
                VALUE_FN = fn.VALUES

            for column in on_conflict._preserve:
                entity = ensure_entity(column)
                expression = NodeList((
                    ensure_entity(column),
                    SQL('='),
                    VALUE_FN(entity)))
                updates.append(expression)

        if on_conflict._update:
            for k, v in on_conflict._update.items():
                if not isinstance(v, Node):
                    # Attempt to resolve string field-names to their respective
                    # field object, to apply data-type conversions.
                    if isinstance(k, basestring):
                        k = getattr(query.table, k)
                    converter = k.db_value if isinstance(k, Field) else None
                    v = Value(v, converter=converter, unpack=False)
                updates.append(NodeList((ensure_entity(k), SQL('='), v)))

        if updates:
            return NodeList((SQL('ON DUPLICATE KEY UPDATE'),
                             CommaNodeList(updates)))

    def extract_date(self, date_part, date_field):
        """
        提供用于提取日期时间部分的兼容接口。

        Args:
            date_part (str) -- 要提取的日期部分，例如“年份”。
            date_field (Node) -- 包含日期/时间的SQL节点，例如 DateTimeField
        """
        return fn.EXTRACT(NodeList((SQL(date_part), SQL('FROM'), date_field)))

    def truncate_date(self, date_part, date_field):
        """
        提供一个兼容的接口，用于将日期时间截断为给定的部分

        Args:
            date_part (str) -- 要截断到的日期部分，例如“day”。
            date_field (Node) -- 包含日期/时间的SQL节点，例如 DateTimeField
        """
        return fn.DATE_FORMAT(date_field, _mysql_date_trunc_[date_part],
                              python_value=simple_date_time)

    def to_timestamp(self, date_field):
        """
        返回一个特定于数据库的函数调用，该函数调用允许使用给定的日期时间值作为数字时间戳。
        这有时可以以兼容的方式简化日期数学之类的任务。
        """
        return fn.UNIX_TIMESTAMP(date_field)

    def from_timestamp(self, date_field):
        """
        处理时间戳
        """
        return fn.FROM_UNIXTIME(date_field)

    def random(self):
        """
        一个兼容的接口，用于调用数据库提供的适当的随机数生成函数。
        """
        return fn.rand()

    def get_noop_select(self, ctx):
        """
        执行 SQL
        """
        return ctx.literal('DO 0')


# TRANSACTION CONTROL.


class _manual(_CallableContextManager):
    def __init__(self, db):
        self.db = db

    def __enter__(self):
        top = self.db.top_transaction()
        if top and not isinstance(self.db.top_transaction(), _manual):
            raise ValueError('Cannot enter manual commit block while a '
                             'transaction is active.')
        self.db.push_transaction(self)

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.db.pop_transaction() is not self:
            raise ValueError('Transaction stack corrupted while exiting '
                             'manual commit block.')


class _atomic(_CallableContextManager):
    def __init__(self, db, lock_type=None):
        self.db = db
        self._lock_type = lock_type
        self._transaction_args = (lock_type,) if lock_type is not None else ()

    def __enter__(self):
        if self.db.transaction_depth() == 0:
            self._helper = self.db.transaction(*self._transaction_args)
        elif isinstance(self.db.top_transaction(), _manual):
            raise ValueError('Cannot enter atomic commit block while in '
                             'manual commit mode.')
        else:
            self._helper = self.db.savepoint()
        return self._helper.__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self._helper.__exit__(exc_type, exc_val, exc_tb)


class _transaction(_CallableContextManager):
    def __init__(self, db, lock_type=None):
        self.db = db
        self._lock_type = lock_type

    def _begin(self):
        if self._lock_type:
            self.db.begin(self._lock_type)
        else:
            self.db.begin()

    def commit(self, begin=True):
        """
        提交
        """
        self.db.commit()
        if begin:
            self._begin()

    def rollback(self, begin=True):
        """
        回滚
        """
        self.db.rollback()
        if begin:
            self._begin()

    def __enter__(self):
        if self.db.transaction_depth() == 0:
            self._begin()
        self.db.push_transaction(self)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if exc_type:
                self.rollback(False)
            elif self.db.transaction_depth() == 1:
                try:
                    self.commit(False)
                except BaseException:
                    self.rollback(False)
                    raise
        finally:
            self.db.pop_transaction()


class _savepoint(_CallableContextManager):
    def __init__(self, db, sid=None):
        self.db = db
        self.sid = sid or 's' + uuid.uuid4().hex
        self.quoted_sid = self.sid.join(self.db.quote)

    def _begin(self):
        self.db.execute_sql('SAVEPOINT %s;' % self.quoted_sid)

    def commit(self, begin=True):
        """
        提交
        """
        self.db.execute_sql('RELEASE SAVEPOINT %s;' % self.quoted_sid)
        if begin:
            self._begin()

    def rollback(self):
        """
        回滚
        """
        self.db.execute_sql('ROLLBACK TO SAVEPOINT %s;' % self.quoted_sid)

    def __enter__(self):
        self._begin()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.rollback()
        else:
            try:
                self.commit(begin=False)
            except BaseException:
                self.rollback()
                raise


# CURSOR REPRESENTATIONS.


class CursorWrapper(object):
    """
    封装 Cursor
    """
    def __init__(self, cursor):
        self.cursor = cursor
        self.count = 0
        self.index = 0
        self.initialized = False
        self.populated = False
        self.row_cache = []

    def __iter__(self):
        if self.populated:
            return iter(self.row_cache)
        return ResultIterator(self)

    def __getitem__(self, item):
        if isinstance(item, slice):
            stop = item.stop
            if stop is None or stop < 0:
                self.fill_cache()
            else:
                self.fill_cache(stop)
            return self.row_cache[item]
        elif isinstance(item, int):
            self.fill_cache(item if item > 0 else 0)
            return self.row_cache[item]
        else:
            raise ValueError('CursorWrapper only supports integer and slice '
                             'indexes.')

    def __len__(self):
        self.fill_cache()
        return self.count

    def initialize(self):
        """
        初始化
        """
        pass

    def iterate(self, cache=True):
        """
        迭代器
        """
        row = self.cursor.fetchone()
        if row is None:
            self.populated = True
            self.cursor.close()
            raise StopIteration
        elif not self.initialized:
            self.initialize()  # Lazy initialization.
            self.initialized = True
        self.count += 1
        result = self.process_row(row)
        if cache:
            self.row_cache.append(result)
        return result

    def process_row(self, row):
        """
        直接返回 raw
        """
        return row

    def iterator(self):
        """Efficient one-pass iteration over the result set."""
        while True:
            try:
                yield self.iterate(False)
            except StopIteration:
                return

    def fill_cache(self, n=0):
        """
        cache
        """
        n = n or float('Inf')
        if n < 0:
            raise ValueError('Negative values are not supported.')

        iterator = ResultIterator(self)
        iterator.index = self.count
        while not self.populated and (n > self.count):
            try:
                iterator.next()
            except StopIteration:
                break


class DictCursorWrapper(CursorWrapper):
    """
    DictCursor 封装
    """
    def _initialize_columns(self):
        description = self.cursor.description
        self.columns = [t[0][t[0].find('.') + 1:].strip('"')
                        for t in description]
        self.ncols = len(description)

    initialize = _initialize_columns

    def _row_to_dict(self, row):
        result = {}
        for i in range(self.ncols):
            result.setdefault(self.columns[i], row[i])  # Do not overwrite.
        return result

    process_row = _row_to_dict


class NamedTupleCursorWrapper(CursorWrapper):
    """
    NamedTupleCursor 封装
    """
    def initialize(self):
        """
        初始化
        """
        description = self.cursor.description
        self.tuple_class = collections.namedtuple(
            'Row',
            [col[0][col[0].find('.') + 1:].strip('"') for col in description])

    def process_row(self, row):
        """
        执行 row
        """
        return self.tuple_class(*row)


class ObjectCursorWrapper(DictCursorWrapper):
    """
    ObjectCursor 封装
    """
    def __init__(self, cursor, constructor):
        super(ObjectCursorWrapper, self).__init__(cursor)
        self.constructor = constructor

    def process_row(self, row):
        """
        执行 row
        """
        row_dict = self._row_to_dict(row)
        return self.constructor(**row_dict)


class ResultIterator(object):
    """
    结果迭代器
    """
    def __init__(self, cursor_wrapper):
        self.cursor_wrapper = cursor_wrapper
        self.index = 0

    def __iter__(self):
        return self

    def next(self):
        """
        迭代器 next
        """
        if self.index < self.cursor_wrapper.count:
            obj = self.cursor_wrapper.row_cache[self.index]
        elif not self.cursor_wrapper.populated:
            self.cursor_wrapper.iterate()
            obj = self.cursor_wrapper.row_cache[self.index]
        else:
            raise StopIteration
        self.index += 1
        return obj

    __next__ = next

# FIELDS


class FieldAccessor(object):
    """
    字段存取器
    """
    def __init__(self, model, field, name):
        self.model = model
        self.field = field
        self.name = name

    def __get__(self, instance, instance_type=None):
        if instance is not None:
            return instance._data_.get(self.name)
        return self.field

    def __set__(self, instance, value):
        instance._data_[self.name] = value
        instance._dirty.add(self.name)


class ForeignKeyAccessor(FieldAccessor):
    """
    外键存储器
    """
    def __init__(self, model, field, name):
        super(ForeignKeyAccessor, self).__init__(model, field, name)
        self.rel_model = field.rel_model

    def get_rel_instance(self, instance):
        """
        返回 rel 实例
        """
        value = instance._data_.get(self.name)
        if value is not None or self.name in instance._rel_:
            if self.name not in instance._rel_:
                obj = self.rel_model.get(self.field.rel_field == value)
                instance._rel_[self.name] = obj
            return instance._rel_[self.name]
        elif not self.field.null:
            raise self.rel_model.DoesNotExist
        return value

    def __get__(self, instance, instance_type=None):
        if instance is not None:
            return self.get_rel_instance(instance)
        return self.field

    def __set__(self, instance, obj):
        if isinstance(obj, self.rel_model):
            instance._data_[self.name] = getattr(obj, self.field.rel_field.name)
            instance._rel_[self.name] = obj
        else:
            fk_value = instance._data_.get(self.name)
            instance._data_[self.name] = obj
            if obj != fk_value and self.name in instance._rel_:
                del instance._rel_[self.name]
        instance._dirty.add(self.name)


class NoQueryForeignKeyAccessor(ForeignKeyAccessor):
    """
    NoQueryForeignKeyAccessor 类
    """
    def get_rel_instance(self, instance):
        """
        返回 rel 实例
        """
        value = instance._data_.get(self.name)
        if value is not None:
            return instance._rel_.get(self.name, value)
        elif not self.field.null:
            raise self.rel_model.DoesNotExist


class BackrefAccessor(object):
    """
    BackrefAccessor 类
    """
    def __init__(self, field):
        self.field = field
        self.model = field.rel_model
        self.rel_model = field.model

    def __get__(self, instance, instance_type=None):
        if instance is not None:
            dest = self.field.rel_field.name
            return (self.rel_model
                    .select()
                    .where(self.field == getattr(instance, dest)))
        return self


class ObjectIdAccessor(object):
    """Gives direct access to the underlying id"""

    def __init__(self, field):
        self.field = field

    def __get__(self, instance, instance_type=None):
        if instance is not None:
            return instance._data_.get(self.field.name)
        return self.field

    def __set__(self, instance, value):
        setattr(instance, self.field.name, value)


class Field(ColumnBase):
    """
    字段
    Field instance ===> Column on a table
    """
    _field_counter = 0
    _order = 0
    accessor_class = FieldAccessor
    auto_increment = False
    default_index_type = None
    field_type = 'DEFAULT'

    def __init__(self, null=False, index=False, unique=False, column_name=None,
                 default=None, primary_key=False, constraints=None,
                 sequence=None, collation=None, unindexed=False, choices=None,
                 help_text=None, verbose_name=None, index_type=None,
                 db_column=None, _hidden=False):
        """
        null (bool) -- 字段允许空值。
        index (bool) -- 在字段上创建索引。
        unique (bool) -- 在字段上创建唯一索引。
        column_name (str) -- 为字段指定列名。
        default -- 默认值（在python中强制执行，而不是在服务器上）。
        primary_key (bool) -- 字段是主键。
        constraints (list) -- 要应用于列的约束列表，例如： [Check('price > 0')] .
        sequence (str) -- 字段的序列名。
        collation (str) -- 字段的排序规则名称。
        unindexed (bool) -- 声明字段未索引（仅限于sqlite）。
        choices (list) -- 两元组的一个表，将列值映射到显示标签。例如，仅用于元数据目的，以帮助显示字段值选项的下拉列表。
        help_text (str) -- 字段的帮助文本，仅用于元数据。
        verbose_name (str) -- 字段的详细名称，仅用于元数据。
        index_type (str) -- 指定索引类型（仅限Postgres），例如“brin”。
        """
        if db_column is not None:
            _deprecated_('"db_column" has been deprecated in favor of '
                           '"column_name" for Field objects.')
            column_name = db_column

        self.null = null
        self.index = index
        self.unique = unique
        self.column_name = column_name
        self.default = default
        self.primary_key = primary_key
        self.constraints = constraints  # List of column constraints.
        self.sequence = sequence  # Name of sequence, e.g. foo_id_seq.
        self.collation = collation
        self.unindexed = unindexed
        self.choices = choices
        self.help_text = help_text
        self.verbose_name = verbose_name
        self.index_type = index_type or self.default_index_type
        self._hidden = _hidden

        # Used internally for recovering the order in which Fields were defined
        # on the Model class.
        Field._field_counter += 1
        self._order = Field._field_counter
        self._sort_key = (self.primary_key and 1 or 2), self._order

    def __hash__(self):
        return hash(self.name + '.' + self.model.__name__)

    def __repr__(self):
        if hasattr(self, 'model') and getattr(self, 'name', None):
            return '<%s: %s.%s>' % (type(self).__name__,
                                    self.model.__name__,
                                    self.name)
        return '<%s: (unbound)>' % type(self).__name__

    def bind(self, model, name, set_attribute=True):
        """
        绑定 model
        """
        self.model = model
        self.name = name
        self.column_name = self.column_name or name
        if set_attribute:
            setattr(model, name, self.accessor_class(model, self, name))

    @property
    def column(self):
        """
        返回 Column 对象
        """
        return Column(self.model._meta.table, self.column_name)

    def adapt(self, value):
        """
        直接返回 value
        """
        return value

    def db_value(self, value):
        """
        将 python 值强制为适合存储在数据库中的值。
        """
        return value if value is None else self.adapt(value)

    def python_value(self, value):
        """
        将数据库中的值强制为 python 对象。
        """
        return value if value is None else self.adapt(value)

    def get_sort_key(self, ctx):
        """
        返回 _sort_key
        """
        return self._sort_key

    def _sql_(self, ctx):
        return ctx.sql(self.column)

    def get_modifiers(self):
        """
        none
        """
        return

    def ddl_datatype(self, ctx):
        """
        ddl 数据类型
        """
        if ctx and ctx.state.field_types:
            column_type = ctx.state.field_types.get(self.field_type,
                                                    self.field_type)
        else:
            column_type = self.field_type

        modifiers = self.get_modifiers()
        if column_type and modifiers:
            modifier_literal = ', '.join([str(m) for m in modifiers])
            return SQL('%s(%s)' % (column_type, modifier_literal))
        else:
            return SQL(column_type)

    def ddl(self, ctx):
        """
        ddl
        """
        accum = [Entity(self.column_name)]
        data_type = self.ddl_datatype(ctx)
        if data_type:
            accum.append(data_type)
        if self.unindexed:
            accum.append(SQL('UNINDEXED'))
        if not self.null:
            accum.append(SQL('NOT NULL'))
        if self.primary_key:
            accum.append(SQL('PRIMARY KEY'))
        if self.sequence:
            accum.append(SQL("DEFAULT NEXTVAL('%s')" % self.sequence))
        if self.constraints:
            accum.extend(self.constraints)
        if self.collation:
            accum.append(SQL('COLLATE %s' % self.collation))
        return NodeList(accum)


class IntegerField(Field):
    """
    用于存储整数的字段类。
    """
    field_type = 'INT'
    adapt = int


class BigIntegerField(IntegerField):
    """
    用于存储大整数的字段类
    """
    field_type = 'BIGINT'


class SmallIntegerField(IntegerField):
    """
    用于存储小整数的字段类
    """
    field_type = 'SMALLINT'


class AutoField(IntegerField):
    """
    用于存储自动递增主键的字段类。
    """
    auto_increment = True
    field_type = 'AUTO'

    def __init__(self, *args, **kwargs):
        if kwargs.get('primary_key') is False:
            raise ValueError('%s must always be a primary key.' % type(self))
        kwargs['primary_key'] = True
        super(AutoField, self).__init__(*args, **kwargs)


class BigAutoField(AutoField):
    """
    字段类，用于存储使用64位的自动递增主键。
    """
    field_type = 'BIGAUTO'


class PrimaryKeyField(AutoField):
    """
    主键字段类
    """
    def __init__(self, *args, **kwargs):
        _deprecated_('"PrimaryKeyField" has been renamed to "AutoField". '
                       'Please update your code accordingly as this will be '
                       'completely removed in a subsequent release.')
        super(PrimaryKeyField, self).__init__(*args, **kwargs)


class FloatField(Field):
    """
    用于存储浮点数字的字段类。
    """
    field_type = 'FLOAT'
    adapt = float


class DoubleField(FloatField):
    """
    用于存储双精度浮点数字的字段类。
    """
    field_type = 'DOUBLE'


class DecimalField(Field):
    """
    数字相关字段
    """
    field_type = 'DECIMAL'

    def __init__(self, max_digits=10, decimal_places=5, auto_round=False,
                 rounding=None, *args, **kwargs):
        """
        max_digits (int) -- 要存储的最大数字。
        decimal_places (int) -- 最大精度。
        auto_round (bool) -- 自动舍入值。
        rounding -- 默认为 decimal.DefaultContext.rounding .用于存储十进制数的字段类。
        """
        self.max_digits = max_digits
        self.decimal_places = decimal_places
        self.auto_round = auto_round
        self.rounding = rounding or decimal.DefaultContext.rounding
        super(DecimalField, self).__init__(*args, **kwargs)

    def get_modifiers(self):
        """
        get modifiers
        """
        return [self.max_digits, self.decimal_places]

    def db_value(self, value):
        """
        将 python 值强制为适合存储在数据库中的值。
        """
        D = decimal.Decimal
        if not value:
            return value if value is None else D(0)
        if self.auto_round:
            exp = D(10) ** (-self.decimal_places)
            rounding = self.rounding
            return D(text_type(value)).quantize(exp, rounding=rounding)
        return value

    def python_value(self, value):
        """
        将 python 值强制为适合存储在数据库中的值。
        """
        if value is not None:
            if isinstance(value, decimal.Decimal):
                return value
            return decimal.Decimal(text_type(value))


class _StringField(Field):
    def adapt(self, value):
        """
        适配 value
        """
        if isinstance(value, text_type):
            return value
        elif isinstance(value, bytes_type):
            return value.decode('utf-8')
        return text_type(value)

    def __add__(self, other): return StringExpression(self, OP.CONCAT, other)

    def __radd__(self, other): return StringExpression(other, OP.CONCAT, self)


class CharField(_StringField):
    """
    用于存储字符串的字段类。超过长度的值不会自动截断。
    """
    field_type = 'VARCHAR'

    def __init__(self, max_length=255, *args, **kwargs):
        self.max_length = max_length
        super(CharField, self).__init__(*args, **kwargs)

    def get_modifiers(self):
        """
        返回最大长度
        """
        return self.max_length and [self.max_length] or None


class FixedCharField(CharField):
    """
    用于存储固定长度字符串的字段类。超过长度的值不会自动截断。
    """
    field_type = 'CHAR'

    def python_value(self, value):
        """
        将 python 值强制为适合存储在数据库中的值。
        """
        value = super(FixedCharField, self).python_value(value)
        if value:
            value = value.strip()
        return value


class TextField(_StringField):
    """
    用于存储文本的字段类。
    """
    field_type = 'TEXT'


class BlobField(Field):
    """
    用于存储二进制数据的字段类。
    """
    field_type = 'BLOB'

    def _db_hook(self, database):
        if database is None:
            self._constructor = bytearray
        else:
            self._constructor = database.get_binary_type()

    def bind(self, model, name, set_attribute=True):
        """
        绑定模型
        """
        self._constructor = bytearray
        if model._meta.database:
            self._db_hook(model._meta.database)

        # Attach a hook to the model metadata; in the event the database is
        # changed or set at run-time, we will be sure to apply our callback and
        # use the proper data-type for our database driver.
        model._meta._db_hooks.append(self._db_hook)
        return super(BlobField, self).bind(model, name, set_attribute)

    def db_value(self, value):
        """
        将 python 值强制为适合存储在数据库中的值。
        """
        if isinstance(value, text_type):
            value = value.encode('raw_unicode_escape')
        if isinstance(value, bytes_type):
            return self._constructor(value)
        return value


class BitField(BitwiseMixin, BigIntegerField):
    """
    用于在 64 位整数列中存储选项的字段类。
    """
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('default', 0)
        super(BitField, self).__init__(*args, **kwargs)
        self.__current_flag = 1

    def flag(self, value=None):
        """
        Args:
            value (int) -- 与标志关联的值，通常为 2 的幂。
        Returns:
            返回一个描述符
        """
        if value is None:
            value = self.__current_flag
            self.__current_flag <<= 1
        else:
            self.__current_flag = value << 1

        class FlagDescriptor(object):
            """
            flag 标记
            """
            def __init__(self, field, value):
                self._field = field
                self._value = value

            def __get__(self, instance, instance_type=None):
                if instance is None:
                    return self._field.bin_and(self._value) != 0
                value = getattr(instance, self._field.name) or 0
                return (value & self._value) != 0

            def __set__(self, instance, is_set):
                if is_set not in (True, False):
                    raise ValueError('Value must be either True or False')
                value = getattr(instance, self._field.name) or 0
                if is_set:
                    value |= self._value
                else:
                    value &= ~self._value
                setattr(instance, self._field.name, value)
        return FlagDescriptor(self, value)


class BigBitFieldData(object):
    """
    用于在 BLOB . 该字段将根据需要增加底层缓冲区，以确保有足够的数据字节来支持存储的数据位数。
    """
    def __init__(self, instance, name):
        self.instance = instance
        self.name = name
        value = self.instance._data_.get(self.name)
        if not value:
            value = bytearray()
        elif not isinstance(value, bytearray):
            value = bytearray(value)
        self._buffer = self.instance._data_[self.name] = value

    def _ensure_length(self, idx):
        byte_num, byte_offset = divmod(idx, 8)
        cur_size = len(self._buffer)
        if cur_size <= byte_num:
            self._buffer.extend(b'\x00' * ((byte_num + 1) - cur_size))
        return byte_num, byte_offset

    def set_bit(self, idx):
        """
        设置 idx
        Args:
            idx (int) -- 要设置的位，从零开始索引。
        """
        byte_num, byte_offset = self._ensure_length(idx)
        self._buffer[byte_num] |= (1 << byte_offset)

    def clear_bit(self, idx):
        """
        清除 idx
        Args:
            idx (int) -- 要清除的位，从零开始索引。
        """
        byte_num, byte_offset = self._ensure_length(idx)
        self._buffer[byte_num] &= ~(1 << byte_offset)

    def toggle_bit(self, idx):
        """
        Args:
            idx (int) -- 要切换的位，从零开始索引。
        Returns:
            位是否设置。
        """
        byte_num, byte_offset = self._ensure_length(idx)
        self._buffer[byte_num] ^= (1 << byte_offset)
        return bool(self._buffer[byte_num] & (1 << byte_offset))

    def is_set(self, idx):
        """
        Args:
            idx (int) -- 位索引，从零开始索引。
        Returns:
            位是否设置。
        """
        byte_num, byte_offset = self._ensure_length(idx)
        return bool(self._buffer[byte_num] & (1 << byte_offset))

    def __repr__(self):
        return repr(self._buffer)


class BigBitFieldAccessor(FieldAccessor):
    """
    位存储
    """
    def __get__(self, instance, instance_type=None):
        if instance is None:
            return self.field
        return BigBitFieldData(instance, self.name)

    def __set__(self, instance, value):
        if isinstance(value, memoryview):
            value = value.tobytes()
        elif isinstance(value, buffer_type):
            value = bytes(value)
        elif isinstance(value, bytearray):
            value = bytes_type(value)
        elif isinstance(value, BigBitFieldData):
            value = bytes_type(value._buffer)
        elif isinstance(value, text_type):
            value = value.encode('utf-8')
        elif not isinstance(value, bytes_type):
            raise ValueError('Value must be either a bytes, memoryview or '
                             'BigBitFieldData instance.')
        super(BigBitFieldAccessor, self).__set__(instance, value)


class BigBitField(BlobField):
    """
    字段类，用于在 BLOB
    """
    accessor_class = BigBitFieldAccessor

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('default', bytes_type)
        super(BigBitField, self).__init__(*args, **kwargs)

    def db_value(self, value):
        """
        将 python 值强制为适合存储在数据库中的值。
        """
        return bytes_type(value) if value is not None else value


class UUIDField(Field):
    """
    用于存储的字段类 uuid.UUID
    """
    field_type = 'UUID'

    def db_value(self, value):
        """
        将 python 值强制为适合存储在数据库中的值。
        """
        if isinstance(value, basestring) and len(value) == 32:
            # Hex string. No transformation is necessary.
            return value
        elif isinstance(value, bytes) and len(value) == 16:
            # Allow raw binary representation.
            value = uuid.UUID(bytes=value)
        if isinstance(value, uuid.UUID):
            return value.hex
        try:
            return uuid.UUID(value).hex
        except BaseException:
            return value

    def python_value(self, value):
        """
        将 python 值强制为适合存储在数据库中的值。
        """
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(value) if value is not None else None


class BinaryUUIDField(BlobField):
    """
    用于存储的字段类 uuid.UUID 以 16 字节为单位的有效对象。
    """
    field_type = 'UUIDB'

    def db_value(self, value):
        """
        将 python 值强制为适合存储在数据库中的值。
        """
        if isinstance(value, bytes) and len(value) == 16:
            # Raw binary value. No transformation is necessary.
            return self._constructor(value)
        elif isinstance(value, basestring) and len(value) == 32:
            # Allow hex string representation.
            value = uuid.UUID(hex=value)
        if isinstance(value, uuid.UUID):
            return self._constructor(value.bytes)
        elif value is not None:
            raise ValueError('value for binary UUID field must be UUID(), '
                             'a hexadecimal string, or a bytes object.')

    def python_value(self, value):
        """
        将 python 值强制为适合存储在数据库中的值。
        """
        if isinstance(value, uuid.UUID):
            return value
        elif isinstance(value, memoryview):
            value = value.tobytes()
        elif value and not isinstance(value, bytes):
            value = bytes(value)
        return uuid.UUID(bytes=value) if value is not None else None


def _date_part(date_part):
    def dec(self):
        """
        inner function
        """
        return self.model._meta.database.extract_date(date_part, self)
    return dec


def format_date_time(value, formats, post_process=None):
    """
    格式化日期时间
    """
    post_process = post_process or (lambda x: x)
    for fmt in formats:
        try:
            return post_process(datetime.datetime.strptime(value, fmt))
        except ValueError:
            pass
    return value


def simple_date_time(value):
    """
    格式化输出时间
    """
    try:
        return datetime.datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
    except (TypeError, ValueError):
        return value


class _BaseFormattedField(Field):
    formats = None

    def __init__(self, formats=None, *args, **kwargs):
        if formats is not None:
            self.formats = formats
        super(_BaseFormattedField, self).__init__(*args, **kwargs)


class DateTimeField(_BaseFormattedField):
    """
    datetime.datetime
    """
    field_type = 'DATETIME'
    formats = [
        '%Y-%m-%d %H:%M:%S.%f',
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d',
    ]

    def adapt(self, value):
        """
        格式化 value
        """
        if value and isinstance(value, basestring):
            return format_date_time(value, self.formats)
        return value

    def to_timestamp(self):
        """
        返回一个特定于数据库的函数调用，该函数调用允许使用给定的日期时间值作为数字时间戳。
        这有时可以以兼容的方式简化日期数学之类的任务。
        """
        return self.model._meta.database.to_timestamp(self)

    def truncate(self, part):
        """
        将列中的值截断为给定部分。
        例如，此方法对于查找给定月份内的所有行很有用。
        """
        return self.model._meta.database.truncate_date(part, self)

    year = property(_date_part('year'))
    month = property(_date_part('month'))
    day = property(_date_part('day'))
    hour = property(_date_part('hour'))
    minute = property(_date_part('minute'))
    second = property(_date_part('second'))


class DateField(_BaseFormattedField):
    """
    datetime.date
    """
    field_type = 'DATE'
    formats = [
        '%Y-%m-%d',
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d %H:%M:%S.%f',
    ]

    def adapt(self, value):
        """
        格式化 value
        """
        if value and isinstance(value, basestring):
            def pp(x):
                """
                返回日期
                """
                return x.date()
            return format_date_time(value, self.formats, pp)
        elif value and isinstance(value, datetime.datetime):
            return value.date()
        return value

    def to_timestamp(self):
        """
        返回一个特定于数据库的函数调用，该函数调用允许使用给定的日期时间值作为数字时间戳。
        这有时可以以兼容的方式简化日期数学之类的任务。
        """
        return self.model._meta.database.to_timestamp(self)

    def truncate(self, part):
        """
        将列中的值截断为给定部分。
        例如，此方法对于查找给定月份内的所有行很有用。
        """
        return self.model._meta.database.truncate_date(part, self)

    year = property(_date_part('year'))
    month = property(_date_part('month'))
    day = property(_date_part('day'))


class TimeField(_BaseFormattedField):
    """
    datetime.time
    """
    field_type = 'TIME'
    formats = [
        '%H:%M:%S.%f',
        '%H:%M:%S',
        '%H:%M',
        '%Y-%m-%d %H:%M:%S.%f',
        '%Y-%m-%d %H:%M:%S',
    ]

    def adapt(self, value):
        """
        格式化 value
        """
        if value:
            if isinstance(value, basestring):
                def pp(x):
                    """
                    返回时间
                    """
                    return x.time()
                return format_date_time(value, self.formats, pp)
            elif isinstance(value, datetime.datetime):
                return value.time()
        if value is not None and isinstance(value, datetime.timedelta):
            return (datetime.datetime.min + value).time()
        return value

    hour = property(_date_part('hour'))
    minute = property(_date_part('minute'))
    second = property(_date_part('second'))


def _timestamp_date_part(date_part):
    def dec(self):
        """
        inner function
        """
        db = self.model._meta.database
        expr = ((self / Value(self.resolution, converter=False))
                if self.resolution > 1 else self)
        return db.extract_date(date_part, db.from_timestamp(expr))
    return dec


class TimestampField(BigIntegerField):
    """
    用于将日期时间存储为整数时间戳的字段类。
    """
    # Support second -> microsecond resolution.
    valid_resolutions = [10 ** i for i in range(7)]

    def __init__(self, *args, **kwargs):
        """
        resolution: 1=秒、1000=ms、1000000=us
        utc (bool) -- 将时间戳视为 UTC。
        """
        self.resolution = kwargs.pop('resolution', None)
        if not self.resolution:
            self.resolution = 1
        elif self.resolution in range(7):
            self.resolution = 10 ** self.resolution
        elif self.resolution not in self.valid_resolutions:
            raise ValueError('TimestampField resolution must be one of: %s' %
                             ', '.join(str(i) for i in self.valid_resolutions))
        self.ticks_to_microsecond = 1000000 // self.resolution

        self.utc = kwargs.pop('utc', False) or False
        dflt = datetime.datetime.utcnow if self.utc else datetime.datetime.now
        kwargs.setdefault('default', dflt)
        super(TimestampField, self).__init__(*args, **kwargs)

    def local_to_utc(self, dt):
        """
        # Convert naive local datetime into naive UTC, e.g.:
        # 2019-03-01T12:00:00 (local=US/Central) -> 2019-03-01T18:00:00.
        # 2019-05-01T12:00:00 (local=US/Central) -> 2019-05-01T17:00:00.
        # 2019-03-01T12:00:00 (local=UTC)        -> 2019-03-01T12:00:00.
        """
        return datetime.datetime(*time.gmtime(time.mktime(dt.timetuple()))[:6])

    def utc_to_local(self, dt):
        """
        # Convert a naive UTC datetime into local time, e.g.:
        # 2019-03-01T18:00:00 (local=US/Central) -> 2019-03-01T12:00:00.
        # 2019-05-01T17:00:00 (local=US/Central) -> 2019-05-01T12:00:00.
        # 2019-03-01T12:00:00 (local=UTC)        -> 2019-03-01T12:00:00.
        """
        ts = calendar.timegm(dt.utctimetuple())
        return datetime.datetime.fromtimestamp(ts)

    def get_timestamp(self, value):
        """
        获取时间戳
        """
        if self.utc:
            # If utc-mode is on, then we assume all naive datetimes are in UTC.
            return calendar.timegm(value.utctimetuple())
        else:
            return time.mktime(value.timetuple())

    def db_value(self, value):
        """
        将 python 值强制为适合存储在数据库中的值。
        """
        if value is None:
            return

        if isinstance(value, datetime.datetime):
            pass
        elif isinstance(value, datetime.date):
            value = datetime.datetime(value.year, value.month, value.day)
        else:
            return int(round(value * self.resolution))

        timestamp = self.get_timestamp(value)
        if self.resolution > 1:
            timestamp += (value.microsecond * .000001)
            timestamp *= self.resolution
        return int(round(timestamp))

    def python_value(self, value):
        """
        将 python 值强制为适合存储在数据库中的值。
        """
        if value is not None and isinstance(value, (int, float, long)):
            if self.resolution > 1:
                value, ticks = divmod(value, self.resolution)
                microseconds = int(ticks * self.ticks_to_microsecond)
            else:
                microseconds = 0

            if self.utc:
                value = datetime.datetime.utcfromtimestamp(value)
            else:
                value = datetime.datetime.fromtimestamp(value)

            if microseconds:
                value = value.replace(microsecond=microseconds)

        return value

    def from_timestamp(self):
        """
        处理时间戳
        """
        expr = ((self / Value(self.resolution, converter=False))
                if self.resolution > 1 else self)
        return self.model._meta.database.from_timestamp(expr)

    year = property(_timestamp_date_part('year'))
    month = property(_timestamp_date_part('month'))
    day = property(_timestamp_date_part('day'))
    hour = property(_timestamp_date_part('hour'))
    minute = property(_timestamp_date_part('minute'))
    second = property(_timestamp_date_part('second'))


class IPField(BigIntegerField):
    """
    用于高效存储 IPv4 地址的字段类（整数）。
    """
    def db_value(self, val):
        """
        将 python 值强制为适合存储在数据库中的值。
        """
        if val is not None:
            return struct.unpack('!I', socket.inet_aton(val))[0]

    def python_value(self, val):
        """
        将 python 值强制为适合存储在数据库中的值。
        """
        if val is not None:
            return socket.inet_ntoa(struct.pack('!I', val))


class BooleanField(Field):
    """
    用于存储布尔值的字段类。
    """
    field_type = 'BOOL'
    adapt = bool


class BareField(Field):
    """
    不指定数据类型的字段类（sqlite only）。
    """
    def __init__(self, adapt=None, *args, **kwargs):
        super(BareField, self).__init__(*args, **kwargs)
        if adapt is not None:
            self.adapt = adapt

    def ddl_datatype(self, ctx):
        """
        ddl 数据类型
        """
        return


class ForeignKeyField(Field):
    """
    用于存储外键的字段类。
    """
    accessor_class = ForeignKeyAccessor

    def __init__(self, model, field=None, backref=None, on_delete=None,
                 on_update=None, deferrable=None, _deferred=None,
                 rel_model=None, to_field=None, object_id_name=None,
                 lazy_load=True, related_name=None, *args, **kwargs):
        kwargs.setdefault('index', True)

        # If lazy_load is disable, we use a different descriptor/accessor that
        # will ensure we don't accidentally perform a query.
        if not lazy_load:
            self.accessor_class = NoQueryForeignKeyAccessor

        super(ForeignKeyField, self).__init__(*args, **kwargs)

        if rel_model is not None:
            _deprecated_('"rel_model" has been deprecated in favor of '
                           '"model" for ForeignKeyField objects.')
            model = rel_model
        if to_field is not None:
            _deprecated_('"to_field" has been deprecated in favor of '
                           '"field" for ForeignKeyField objects.')
            field = to_field
        if related_name is not None:
            _deprecated_('"related_name" has been deprecated in favor of '
                           '"backref" for Field objects.')
            backref = related_name

        self.rel_model = model
        self.rel_field = field
        self.declared_backref = backref
        self.backref = None
        self.on_delete = on_delete
        self.on_update = on_update
        self.deferrable = deferrable
        self.deferred = _deferred
        self.object_id_name = object_id_name
        self.lazy_load = lazy_load

    @property
    def field_type(self):
        """
        自动适配 field_type 类型
        """
        if not isinstance(self.rel_field, AutoField):
            return self.rel_field.field_type
        elif isinstance(self.rel_field, BigAutoField):
            return BigIntegerField.field_type
        return IntegerField.field_type

    def get_modifiers(self):
        """
        返回 modifiers
        """
        if not isinstance(self.rel_field, AutoField):
            return self.rel_field.get_modifiers()
        return super(ForeignKeyField, self).get_modifiers()

    def adapt(self, value):
        """
        格式化 value
        """
        return self.rel_field.adapt(value)

    def db_value(self, value):
        """
        将 python 值强制为适合存储在数据库中的值。
        """
        if isinstance(value, self.rel_model):
            value = value.get_id()
        return self.rel_field.db_value(value)

    def python_value(self, value):
        """
        将 python 值强制为适合存储在数据库中的值。
        """
        if isinstance(value, self.rel_model):
            return value
        return self.rel_field.python_value(value)

    def bind(self, model, name, set_attribute=True):
        """
        绑定 model
        """
        if not self.column_name:
            self.column_name = name if name.endswith('_id') else name + '_id'
        if not self.object_id_name:
            self.object_id_name = self.column_name
            if self.object_id_name == name:
                self.object_id_name += '_id'
        elif self.object_id_name == name:
            raise ValueError('ForeignKeyField "%s"."%s" specifies an '
                             'object_id_name that conflicts with its field '
                             'name.' % (model._meta.name, name))
        if self.rel_model == 'self':
            self.rel_model = model
        if isinstance(self.rel_field, basestring):
            self.rel_field = getattr(self.rel_model, self.rel_field)
        elif self.rel_field is None:
            self.rel_field = self.rel_model._meta.primary_key

        # Bind field before assigning backref, so field is bound when
        # calling declared_backref() (if callable).
        super(ForeignKeyField, self).bind(model, name, set_attribute)

        if callable_(self.declared_backref):
            self.backref = self.declared_backref(self)
        else:
            self.backref, self.declared_backref = self.declared_backref, None
        if not self.backref:
            self.backref = '%s_set' % model._meta.name

        if set_attribute:
            setattr(model, self.object_id_name, ObjectIdAccessor(self))
            if self.backref not in '!+':
                setattr(self.rel_model, self.backref, BackrefAccessor(self))

    def foreign_key_constraint(self):
        """
        外键约束
        """
        parts = [
            SQL('FOREIGN KEY'),
            EnclosedNodeList((self,)),
            SQL('REFERENCES'),
            self.rel_model,
            EnclosedNodeList((self.rel_field,))]
        if self.on_delete:
            parts.append(SQL('ON DELETE %s' % self.on_delete))
        if self.on_update:
            parts.append(SQL('ON UPDATE %s' % self.on_update))
        if self.deferrable:
            parts.append(SQL('DEFERRABLE %s' % self.deferrable))
        return NodeList(parts)

    def __getattr__(self, attr):
        if attr.startswith('__'):
            # Prevent recursion error when deep-copying.
            raise AttributeError('Cannot look-up non-existant "__" methods.')
        if attr in self.rel_model._meta.fields:
            return self.rel_model._meta.fields[attr]
        raise AttributeError('Foreign-key has no attribute %s, nor is it a '
                             'valid field on the related model.' % attr)


class DeferredForeignKey(Field):
    """
    用于表示延迟的外键的字段类。用于循环外键引用
    """
    _unresolved = set()

    def __init__(self, rel_model_name, **kwargs):
        """
        rel_model_name (str) -- 要引用的模型名称。
        """
        self.field_kwargs = kwargs
        self.rel_model_name = rel_model_name.lower()
        DeferredForeignKey._unresolved.add(self)
        super(DeferredForeignKey, self).__init__(
            column_name=kwargs.get('column_name'),
            null=kwargs.get('null'))

    __hash__ = object.__hash__

    def __deepcopy__(self, memo=None):
        return DeferredForeignKey(self.rel_model_name, **self.field_kwargs)

    def set_model(self, rel_model):
        """
        设置 model
        """
        field = ForeignKeyField(rel_model, _deferred=True, **self.field_kwargs)
        self.model._meta.add_field(self.name, field)

    @staticmethod
    def resolve(model_cls):
        """
        +------------------------------------------------------
        | # Tweet.user will be resolved into a ForeignKeyField:
        | DeferredForeignKey.resolve(User)
        +------------------------------------------------------
        """
        unresolved = sorted(DeferredForeignKey._unresolved,
                            key=operator.attrgetter('_order'))
        for dr in unresolved:
            if dr.rel_model_name == model_cls.__name__.lower():
                dr.set_model(model_cls)
                DeferredForeignKey._unresolved.discard(dr)


class MetaField(Field):
    """
    MetaField 类
    """
    column_name = default = model = name = None
    primary_key = False


class VirtualField(MetaField):
    """
    虚拟字段
    """
    field_class = None

    def __init__(self, field_class=None, *args, **kwargs):
        Field = field_class if field_class is not None else self.field_class
        self.field_instance = Field() if Field is not None else None
        super(VirtualField, self).__init__(*args, **kwargs)

    def db_value(self, value):
        """
        将 python 值强制为适合存储在数据库中的值。
        """
        if self.field_instance is not None:
            return self.field_instance.db_value(value)
        return value

    def python_value(self, value):
        """
        将 python 值强制为适合存储在数据库中的值。
        """
        if self.field_instance is not None:
            return self.field_instance.python_value(value)
        return value

    def bind(self, model, name, set_attribute=True):
        """
        绑定 model
        """
        self.model = model
        self.column_name = self.name = name
        setattr(model, name, self.accessor_class(model, self, name))


class CompositeKey(MetaField):
    """
    由多列组成的主键。与其他字段不同，复合键是在模型的 Meta 定义字段后初始化。
    它将用作主键的字段的字符串名称作为参数：
    +----------------------------------------------------------
    | class BlogTagThrough(Model):
    |     blog = ForeignKeyField(Blog, backref='tags')
    |     tag = ForeignKeyField(Tag, backref='blogs')
    |
    |     class Meta:
    |         primary_key = CompositeKey('blog', 'tag')
    +----------------------------------------------------------
    """
    sequence = None

    def __init__(self, *field_names):
        self.field_names = field_names

    def __get__(self, instance, instance_type=None):
        if instance is not None:
            return tuple([getattr(instance, field_name)
                          for field_name in self.field_names])
        return self

    def __set__(self, instance, value):
        if not isinstance(value, (list, tuple)):
            raise TypeError('A list or tuple must be used to set the value of '
                            'a composite primary key.')
        if len(value) != len(self.field_names):
            raise ValueError('The length of the value must equal the number '
                             'of columns of the composite primary key.')
        for idx, field_value in enumerate(value):
            setattr(instance, self.field_names[idx], field_value)

    def __eq__(self, other):
        expressions = [(self.model._meta.fields[field] == value)
                       for field, value in zip(self.field_names, other)]
        return reduce(operator.and_, expressions)

    def __ne__(self, other):
        return ~(self == other)

    def __hash__(self):
        return hash((self.model.__name__, self.field_names))

    def _sql_(self, ctx):
        # If the composite PK is being selected, do not use parens. Elsewhere,
        # such as in an expression, we want to use parentheses and treat it as
        # a row value.
        parens = ctx.scope != SCOPE_SOURCE
        return ctx.sql(NodeList([self.model._meta.fields[field]
                                 for field in self.field_names], ', ', parens))

    def bind(self, model, name, set_attribute=True):
        """
        绑定 model
        """
        self.model = model
        self.column_name = self.name = name
        setattr(model, self.name, self)


class _SortedFieldList(object):
    __slots__ = ('_keys', '_items')

    def __init__(self):
        self._keys = []
        self._items = []

    def __getitem__(self, i):
        return self._items[i]

    def __iter__(self):
        return iter(self._items)

    def __contains__(self, item):
        k = item._sort_key
        i = bisect_left(self._keys, k)
        j = bisect_right(self._keys, k)
        return item in self._items[i:j]

    def index(self, field):
        """
        索引 field
        """
        return self._keys.index(field._sort_key)

    def insert(self, item):
        """
        插入 item
        """
        k = item._sort_key
        i = bisect_left(self._keys, k)
        self._keys.insert(i, k)
        self._items.insert(i, item)

    def remove(self, item):
        """
        remove item
        """
        idx = self.index(item)
        del self._items[idx]
        del self._keys[idx]


# MODELS


class SchemaManager(object):
    """
    提供用于管理为给定模型创建和删除表和索引的方法。
    """
    def __init__(self, model, database=None, **context_options):
        self.model = model
        self._database = database
        context_options.setdefault('scope', SCOPE_VALUES)
        self.context_options = context_options

    @property
    def database(self):
        """
        数据库
        """
        db = self._database or self.model._meta.database
        if db is None:
            raise ImproperlyConfigured('database attribute does not appear to '
                                       'be set on the model: %s' % self.model)
        return db

    @database.setter
    def database(self, value):
        """
        指定数据库
        """
        self._database = value

    def _create_context(self):
        return self.database.get_sql_context(**self.context_options)

    def _create_table(self, safe=True, **options):
        is_temp = options.pop('temporary', False)
        ctx = self._create_context()
        ctx.literal('CREATE TEMPORARY TABLE ' if is_temp else 'CREATE TABLE ')
        if safe:
            ctx.literal('IF NOT EXISTS ')
        ctx.sql(self.model).literal(' ')

        columns = []
        constraints = []
        meta = self.model._meta
        if meta.composite_key:
            pk_columns = [meta.fields[field_name].column
                          for field_name in meta.primary_key.field_names]
            constraints.append(NodeList((SQL('PRIMARY KEY'),
                                         EnclosedNodeList(pk_columns))))

        for field in meta.sorted_fields:
            columns.append(field.ddl(ctx))
            if isinstance(field, ForeignKeyField) and not field.deferred:
                constraints.append(field.foreign_key_constraint())

        if meta.constraints:
            constraints.extend(meta.constraints)

        constraints.extend(self._create_table_option_sql(options))
        ctx.sql(EnclosedNodeList(columns + constraints))

        if meta.table_settings is not None:
            table_settings = ensure_tuple(meta.table_settings)
            for setting in table_settings:
                if not isinstance(setting, basestring):
                    raise ValueError('table_settings must be strings')
                ctx.literal(' ').literal(setting)

        if meta.without_rowid:
            ctx.literal(' WITHOUT ROWID')
        return ctx

    def _create_table_option_sql(self, options):
        accum = []
        options = merge_dict(self.model._meta.options or {}, options)
        if not options:
            return accum

        for key, value in sorted(options.items()):
            if not isinstance(value, Node):
                if is_model(value):
                    value = value._meta.table
                else:
                    value = SQL(str(value))
            accum.append(NodeList((SQL(key), value), glue='='))
        return accum

    def create_table(self, safe=True, **options):
        """
        创建表
        """
        self.database.execute(self._create_table(safe=safe, **options))

    def _create_table_as(self, table_name, query, safe=True, **meta):
        ctx = (self._create_context()
               .literal('CREATE TEMPORARY TABLE '
                        if meta.get('temporary') else 'CREATE TABLE '))
        if safe:
            ctx.literal('IF NOT EXISTS ')
        return (ctx
                .sql(Entity(table_name))
                .literal(' AS ')
                .sql(query))

    def create_table_as(self, table_name, query, safe=True, **meta):
        """
        创建 table
        """
        ctx = self._create_table_as(table_name, query, safe=safe, **meta)
        self.database.execute(ctx)

    def _drop_table(self, safe=True, **options):
        ctx = (self._create_context()
               .literal('DROP TABLE IF EXISTS ' if safe else 'DROP TABLE ')
               .sql(self.model))
        if options.get('cascade'):
            ctx = ctx.literal(' CASCADE')
        elif options.get('restrict'):
            ctx = ctx.literal(' RESTRICT')
        return ctx

    def drop_table(self, safe=True, **options):
        """
        drop 表
        """
        self.database.execute(self._drop_table(safe=safe, **options))

    def _truncate_table(self, restart_identity=False, cascade=False):
        db = self.database
        if not db.truncate_table:
            return (self._create_context()
                    .literal('DELETE FROM ').sql(self.model))

        ctx = self._create_context().literal('TRUNCATE TABLE ').sql(self.model)
        if restart_identity:
            ctx = ctx.literal(' RESTART IDENTITY')
        if cascade:
            ctx = ctx.literal(' CASCADE')
        return ctx

    def truncate_table(self, restart_identity=False, cascade=False):
        """
        截断（删除所有行）模型。
        """
        self.database.execute(self._truncate_table(restart_identity, cascade))

    def _create_indexes(self, safe=True):
        return [self._create_index(index, safe)
                for index in self.model._meta.fields_to_index()]

    def _create_index(self, index, safe=True):
        if isinstance(index, Index):
            if not self.database.safe_create_index:
                index = index.safe(False)
            elif index._safe != safe:
                index = index.safe(safe)
        return self._create_context().sql(index)

    def create_indexes(self, safe=True):
        """
        创建索引
        """
        for query in self._create_indexes(safe=safe):
            self.database.execute(query)

    def _drop_indexes(self, safe=True):
        return [self._drop_index(index, safe)
                for index in self.model._meta.fields_to_index()
                if isinstance(index, Index)]

    def _drop_index(self, index, safe):
        statement = 'DROP INDEX '
        if safe and self.database.safe_drop_index:
            statement += 'IF EXISTS '
        if isinstance(index._table, Table) and index._table._schema:
            index_name = Entity(index._table._schema, index._name)
        else:
            index_name = Entity(index._name)
        return (self
                ._create_context()
                .literal(statement)
                .sql(index_name))

    def drop_indexes(self, safe=True):
        """
        删除索引
        """
        for query in self._drop_indexes(safe=safe):
            self.database.execute(query)

    def _check_sequences(self, field):
        if not field.sequence or not self.database.sequences:
            raise ValueError('Sequences are either not supported, or are not '
                             'defined for "%s".' % field.name)

    def _sequence_for_field(self, field):
        if field.model._meta.schema:
            return Entity(field.model._meta.schema, field.sequence)
        else:
            return Entity(field.sequence)

    def _create_sequence(self, field):
        self._check_sequences(field)
        if not self.database.sequence_exists(field.sequence):
            return (self
                    ._create_context()
                    .literal('CREATE SEQUENCE ')
                    .sql(self._sequence_for_field(field)))

    def create_sequence(self, field):
        """
        Args:
            field (Field) -- 指定序列的字段实例
        """
        seq_ctx = self._create_sequence(field)
        if seq_ctx is not None:
            self.database.execute(seq_ctx)

    def _drop_sequence(self, field):
        self._check_sequences(field)
        if self.database.sequence_exists(field.sequence):
            return (self
                    ._create_context()
                    .literal('DROP SEQUENCE ')
                    .sql(self._sequence_for_field(field)))

    def drop_sequence(self, field):
        """
        drop_sequence
        """
        seq_ctx = self._drop_sequence(field)
        if seq_ctx is not None:
            self.database.execute(seq_ctx)

    def _create_foreign_key(self, field):
        name = 'fk_%s_%s_refs_%s' % (field.model._meta.table_name,
                                     field.column_name,
                                     field.rel_model._meta.table_name)
        return (self
                ._create_context()
                .literal('ALTER TABLE ')
                .sql(field.model)
                .literal(' ADD CONSTRAINT ')
                .sql(Entity(_truncate_constraint_name(name)))
                .literal(' ')
                .sql(field.foreign_key_constraint()))

    def create_foreign_key(self, field):
        """
        为给定字段添加外键约束。
        在大多数情况下，不需要使用此方法，因为外键约束是作为表创建的一部分创建的。
        """
        self.database.execute(self._create_foreign_key(field))

    def create_sequences(self):
        """
        create_sequences
        """
        if self.database.sequences:
            for field in self.model._meta.sorted_fields:
                if field.sequence:
                    self.create_sequence(field)

    def create_all(self, safe=True, **table_options):
        """
        为模型创建序列、索引和表。
        """
        self.create_sequences()
        self.create_table(safe, **table_options)
        self.create_indexes(safe=safe)

    def drop_sequences(self):
        """
        drop_sequences
        """
        if self.database.sequences:
            for field in self.model._meta.sorted_fields:
                if field.sequence:
                    self.drop_sequence(field)

    def drop_all(self, safe=True, drop_sequences=True, **options):
        """
        drop all table
        """
        self.drop_table(safe, **options)
        if drop_sequences:
            self.drop_sequences()


class Metadata(object):
    """
    存储 Model 元数据
    """
    def __init__(self, model, database=None, table_name=None, indexes=None,
                 primary_key=None, constraints=None, schema=None,
                 only_save_dirty=False, depends_on=None, options=None,
                 db_table=None, table_function=None, table_settings=None,
                 without_rowid=False, temporary=False, legacy_table_names=True,
                 **kwargs):
        """
        model (Model) -- 模型类
        database (Database) -- 数据库
        table_name (str) -- 指定模型的表名
        indexes (list) -- ModelIndex
        primary_key -- 模型的主键
        constraints (list) -- 表约束列表
        schema (str) -- 架构
        only_save_dirty (bool)
        options (dict) -- 模型的任意选项。
        without_rowid (bool) -- 指定不带 rowid（仅限于sqlite）。
        kwargs -- 任意设置属性和值。
        """
        if db_table is not None:
            _deprecated_('"db_table" has been deprecated in favor of '
                           '"table_name" for Models.')
            table_name = db_table
        self.model = model
        self.database = database

        self.fields = {}
        self.columns = {}
        self.combined = {}

        self._sorted_field_list = _SortedFieldList()
        self.sorted_fields = []
        self.sorted_field_names = []

        self.defaults = {}
        self._default_by_name = {}
        self._default_dict = {}
        self._default_callables = {}
        self._default_callable_list = []

        self.name = model.__name__.lower()
        self.table_function = table_function
        self.legacy_table_names = legacy_table_names
        if not table_name:
            table_name = (self.table_function(model)
                          if self.table_function
                          else self.make_table_name())
        self.table_name = table_name
        self._table = None

        self.indexes = list(indexes) if indexes else []
        self.constraints = constraints
        self._schema = schema
        self.primary_key = primary_key
        self.composite_key = self.auto_increment = None
        self.only_save_dirty = only_save_dirty
        self.depends_on = depends_on
        self.table_settings = table_settings
        self.without_rowid = without_rowid
        self.temporary = temporary

        self.refs = {}
        self.backrefs = {}
        self.model_refs = collections.defaultdict(list)
        self.model_backrefs = collections.defaultdict(list)

        self.options = options or {}
        for key, value in kwargs.items():
            setattr(self, key, value)
        self._additional_keys = set(kwargs.keys())

        # Allow objects to register hooks that are called if the model is bound
        # to a different database. For example, BlobField uses a different
        # Python data-type depending on the db driver / python version. When
        # the database changes, we need to update any BlobField so they can use
        # the appropriate data-type.
        self._db_hooks = []

    def make_table_name(self):
        """
        生成 table 名字
        """
        if self.legacy_table_names:
            return re.sub(r'[^\w]+', '_', self.name)
        return make_snake_case(self.model.__name__)

    def model_graph(self, refs=True, backrefs=True, depth_first=True):
        """
        Args:
            refs (bool) -- 遵循外键引用。
            backrefs (bool) -- 遵循外键返回引用。
            depth_first (bool) -- 进行深度优先搜索（ False 宽度优先）。
        Returns:
            3 个元组的列表, 其中包括 (foreign key field, model class, is_backref) .
        """
        if not refs and not backrefs:
            raise ValueError('One of `refs` or `backrefs` must be True.')

        accum = [(None, self.model, None)]
        seen = set()
        queue = collections.deque((self,))
        method = queue.pop if depth_first else queue.popleft

        while queue:
            curr = method()
            if curr in seen:
                continue
            seen.add(curr)

            if refs:
                for fk, model in curr.refs.items():
                    accum.append((fk, model, False))
                    queue.append(model._meta)
            if backrefs:
                for fk, model in curr.backrefs.items():
                    accum.append((fk, model, True))
                    queue.append(model._meta)

        return accum

    def add_ref(self, field):
        """
        add ref
        """
        rel = field.rel_model
        self.refs[field] = rel
        self.model_refs[rel].append(field)
        rel._meta.backrefs[field] = self.model
        rel._meta.model_backrefs[self.model].append(field)

    def remove_ref(self, field):
        """
        remove ref
        """
        rel = field.rel_model
        del self.refs[field]
        self.model_refs[rel].remove(field)
        del rel._meta.backrefs[field]
        rel._meta.model_backrefs[self.model].remove(field)

    @property
    def table(self):
        """
         Table 对象
        """
        if self._table is None:
            self._table = Table(
                self.table_name,
                [field.column_name for field in self.sorted_fields],
                schema=self.schema,
                _model=self.model,
                _database=self.database)
        return self._table

    @table.setter
    def table(self, value):
        """
         Table 对象
        """
        raise AttributeError('Cannot set the "table".')

    @table.deleter
    def table(self):
        """
         Table 对象
        """
        self._table = None

    @property
    def schema(self):
        """
        返回 schema
        """
        return self._schema

    @schema.setter
    def schema(self, value):
        """
        设置 schema 属性
        """
        self._schema = value
        del self.table

    @property
    def entity(self):
        """
        entity 属性
        """
        if self._schema:
            return Entity(self._schema, self.table_name)
        else:
            return Entity(self.table_name)

    def _update_sorted_fields(self):
        self.sorted_fields = list(self._sorted_field_list)
        self.sorted_field_names = [f.name for f in self.sorted_fields]

    def get_rel_for_model(self, model):
        """
        获取 rel
        """
        if isinstance(model, ModelAlias):
            model = model.model
        forwardrefs = self.model_refs.get(model, [])
        backrefs = self.model_backrefs.get(model, [])
        return (forwardrefs, backrefs)

    def add_field(self, field_name, field, set_attribute=True):
        """
        添加字段
        """
        if field_name in self.fields:
            self.remove_field(field_name)

        if not isinstance(field, MetaField):
            del self.table
            field.bind(self.model, field_name, set_attribute)
            self.fields[field.name] = field
            self.columns[field.column_name] = field
            self.combined[field.name] = field
            self.combined[field.column_name] = field

            self._sorted_field_list.insert(field)
            self._update_sorted_fields()

            if field.default is not None:
                # This optimization helps speed up model instance construction.
                self.defaults[field] = field.default
                if callable_(field.default):
                    self._default_callables[field] = field.default
                    self._default_callable_list.append((field.name,
                                                        field.default))
                else:
                    self._default_dict[field] = field.default
                    self._default_by_name[field.name] = field.default
        else:
            field.bind(self.model, field_name, set_attribute)

        if isinstance(field, ForeignKeyField):
            self.add_ref(field)

    def remove_field(self, field_name):
        """
        删除字段
        """
        if field_name not in self.fields:
            return

        del self.table
        original = self.fields.pop(field_name)
        del self.columns[original.column_name]
        del self.combined[field_name]
        try:
            del self.combined[original.column_name]
        except KeyError:
            pass
        self._sorted_field_list.remove(original)
        self._update_sorted_fields()

        if original.default is not None:
            del self.defaults[original]
            if self._default_callables.pop(original, None):
                for i, (name, _) in enumerate(self._default_callable_list):
                    if name == field_name:
                        self._default_callable_list.pop(i)
                        break
            else:
                self._default_dict.pop(original, None)
                self._default_by_name.pop(original.name, None)

        if isinstance(original, ForeignKeyField):
            self.remove_ref(original)

    def set_primary_key(self, name, field):
        """
        设置主键
        """
        self.composite_key = isinstance(field, CompositeKey)
        self.add_field(name, field)
        self.primary_key = field
        self.auto_increment = (
            field.auto_increment or
            bool(field.sequence))

    def get_primary_keys(self):
        """
        获取主键
        """
        if self.composite_key:
            return tuple([self.fields[field_name]
                          for field_name in self.primary_key.field_names])
        else:
            return (self.primary_key,) if self.primary_key is not False else ()

    def get_default_dict(self):
        """
        获取默认值字典
        """
        dd = self._default_by_name.copy()
        for field_name, default in self._default_callable_list:
            dd[field_name] = default()
        return dd

    def fields_to_index(self):
        """
        有索引的字段
        """
        indexes = []
        for f in self.sorted_fields:
            if f.primary_key:
                continue
            if f.index or f.unique:
                indexes.append(ModelIndex(self.model, (f,), unique=f.unique,
                                          using=f.index_type))

        for index_obj in self.indexes:
            if isinstance(index_obj, Node):
                indexes.append(index_obj)
            elif isinstance(index_obj, (list, tuple)):
                index_parts, unique = index_obj
                fields = []
                for part in index_parts:
                    if isinstance(part, basestring):
                        fields.append(self.combined[part])
                    elif isinstance(part, Node):
                        fields.append(part)
                    else:
                        raise ValueError('Expected either a field name or a '
                                         'subclass of Node. Got: %s' % part)
                indexes.append(ModelIndex(self.model, fields, unique=unique))

        return indexes

    def set_database(self, database):
        """
        设置 database
        """
        self.database = database
        self.model._schema._database = database
        del self.table

        # Apply any hooks that have been registered.
        for hook in self._db_hooks:
            hook(database)

    def set_table_name(self, table_name):
        """
        设置 table name
        """
        self.table_name = table_name
        del self.table


class DoesNotExist(Exception):
    """
    DoesNotExist 异常
    """
    pass


class ModelBase(type):
    """
    ModelBase Metaclass
    """
    # 定义可被继承的属性列表（全局）
    inheritable = set(['constraints', 'database', 'indexes', 'primary_key',
                       'options', 'schema', 'table_function', 'temporary',
                       'only_save_dirty', 'legacy_table_names',
                       'table_settings'])

    def __new__(cls, name, bases, attrs):
        if name == MODEL_BASE or bases[0].__name__ == MODEL_BASE:
            return super(ModelBase, cls).__new__(cls, name, bases, attrs)

        # Meta 类的属性通过 meta_options 存储在 Model 类中
        meta_options = {}
        # 将 Meta 从属性中移除，将 Meta 中的非私有属性加入 meta_options 中
        meta = attrs.pop('Meta', None)
        if meta:
            for k, v in meta.__dict__.items():
                if not k.startswith('_'):
                    meta_options[k] = v

        # 从 meta 中获取主键信息
        pk = getattr(meta, 'primary_key', None)
        pk_name = parent_pk = None

        # Inherit any field descriptors by deep copying the underlying field
        # into the attrs of the new model, additionally see if the bases define
        # inheritable model options and swipe them.
        ##################################################################
        # 开始考虑从父类中继承的情况
        #################################################################
        for b in bases:
            if not hasattr(b, '_meta'):
                continue

            base_meta = b._meta
            if parent_pk is None:
                parent_pk = deepcopy(base_meta.primary_key)
            all_inheritable = cls.inheritable | base_meta._additional_keys

            # 获取父类中的 Meta 内部类字段，只考虑 all_inheritable 中的字段
            for k in base_meta.__dict__:
                if k in all_inheritable and k not in meta_options:
                    meta_options[k] = base_meta.__dict__[k]
            meta_options.setdefault('schema', base_meta.schema)

            # 获取父类中的 Fields, 即表的字段
            for (k, v) in b.__dict__.items():
                if k in attrs:
                    continue

                if isinstance(v, FieldAccessor) and not v.field.primary_key:
                    attrs[k] = deepcopy(v.field)

        sopts = meta_options.pop('schema_options', None) or {}
        Meta = meta_options.get('model_metadata_class', Metadata)
        Schema = meta_options.get('schema_manager_class', SchemaManager)

        # Construct the new class.
        cls = super(ModelBase, cls).__new__(cls, name, bases, attrs)
        cls._data_ = cls._rel_ = None

        cls._meta = Meta(cls, **meta_options)
        cls._schema = Schema(cls, **sopts)

        # 检查 attr 中的 Field 类型字段，设置 Model 中的数据类型
        fields = []
        for key, value in cls.__dict__.items():
            if isinstance(value, Field):
                if value.primary_key and pk:
                    raise ValueError('over-determined primary key %s.' % name)
                elif value.primary_key:
                    pk, pk_name = value, key
                else:
                    fields.append((key, value))

        # 默认主键的设置，如果无法从父类继承，则使用 'id' 为key
        if pk is None:
            if parent_pk is not False:
                pk, pk_name = ((parent_pk, parent_pk.name)
                               if parent_pk is not None else
                               (AutoField(), 'id'))
            else:
                pk = False
        elif isinstance(pk, CompositeKey):
            pk_name = '__composite_key__'
            cls._meta.composite_key = True

        # 如果 model 本身有主键的情况
        if pk is not False:
            cls._meta.set_primary_key(pk_name, pk)

        # 设置 Fields
        for name, field in fields:
            cls._meta.add_field(name, field)

        # Create a repr and error class before finalizing.
        if hasattr(cls, '__str__') and '__repr__' not in attrs:
            setattr(cls, '__repr__', lambda self: '<%s: %s>' % (cls.__name__, self.__str__()))

        # 错误信息
        exc_name = '%sDoesNotExist' % cls.__name__
        exc_attrs = {'__module__': cls.__module__}
        exception_class = type(exc_name, (DoesNotExist,), exc_attrs)
        cls.DoesNotExist = exception_class

        # Call validation hook, allowing additional model validation.
        cls.validate_model()
        DeferredForeignKey.resolve(cls)
        return cls

    def __repr__(self):
        return '<Model: %s>' % self.__name__

    def __iter__(self):
        return iter(self.select())

    def __getitem__(self, key):
        return self.get_by_id(key)

    def __setitem__(self, key, value):
        self.set_by_id(key, value)

    def __delitem__(self, key):
        self.delete_by_id(key)

    def __contains__(self, key):
        try:
            self.get_by_id(key)
        except self.DoesNotExist:
            return False
        else:
            return True

    def __len__(self):
        return self.select().count()

    def __bool__(self): return True
    __nonzero__ = __bool__  # Python 2.


class _BoundModelsContext(_CallableContextManager):
    def __init__(self, models, database, bind_refs, bind_backrefs):
        self.models = models
        self.database = database
        self.bind_refs = bind_refs
        self.bind_backrefs = bind_backrefs

    def __enter__(self):
        self._orig_database = []
        for model in self.models:
            self._orig_database.append(model._meta.database)
            model.bind(self.database, self.bind_refs, self.bind_backrefs)
        return self.models

    def __exit__(self, exc_type, exc_val, exc_tb):
        for model, db in zip(self.models, self._orig_database):
            model.bind(db, self.bind_refs, self.bind_backrefs)


class Model(with_metaclass(ModelBase, Node)):
    """
    模型类
    模型是与数据库表的一对一映射。Model 的子类声明任意数量的 Field 实例作为类属性。这些字段对应于表中的列。
    表级操作，例如 select() ， update() ， insert() 和 delete() 实现为类方法。
    """
    def __init__(self, *args, **kwargs):
        if kwargs.pop('__no_default__', None):
            self._data_ = {}
        else:
            self._data_ = self._meta.get_default_dict()
        self._dirty = set(self._data_)
        self._rel_ = {}

        for k in kwargs:
            setattr(self, k, kwargs[k])

    def __str__(self):
        return str(self._pk) if self._meta.primary_key is not False else 'n/a'

    @classmethod
    def validate_model(cls):
        """
        None
        """
        pass

    @classmethod
    def alias(cls, alias=None):
        """
        创建模型类的别名
        Returns:
            返回 ModelAlias 对象
        """
        return ModelAlias(cls, alias)

    @classmethod
    def select(cls, *fields):
        """
        select 方法
        """
        is_default = not fields
        if not fields:
            fields = cls._meta.sorted_fields
        return ModelSelect(cls, fields, is_default=is_default)

    @classmethod
    def _normalize_data(cls, data, kwargs):
        normalized = {}
        if data:
            if not isinstance(data, dict):
                if kwargs:
                    raise ValueError('Data cannot be mixed with keyword '
                                     'arguments: %s' % data)
                return data
            for key in data:
                try:
                    field = (key if isinstance(key, Field)
                             else cls._meta.combined[key])
                except KeyError:
                    raise ValueError('Unrecognized field name: "%s" in %s.' %
                                     (key, data))
                normalized[field] = data[key]
        if kwargs:
            for key in kwargs:
                try:
                    normalized[cls._meta.combined[key]] = kwargs[key]
                except KeyError:
                    normalized[getattr(cls, key)] = kwargs[key]
        return normalized

    @classmethod
    def update(cls, __data=None, **update):
        """
        update 方法
        """
        return ModelUpdate(cls, cls._normalize_data(__data, update))

    @classmethod
    def insert(cls, __data=None, **insert):
        """
        insert 方法
        """
        return ModelInsert(cls, cls._normalize_data(__data, insert))

    @classmethod
    def insert_many(cls, rows, fields=None):
        """
        插入多行数据
        """
        return ModelInsert(cls, insert=rows, columns=fields)

    @classmethod
    def insert_from(cls, query, fields):
        """
        使用 select 查询作为源插入数据
        +------------------------------------------------------
        | source = (User.select(User.username, fn.COUNT(Tweet.id)).join(Tweet, JOIN.LEFT_OUTER).group_by(User.username))
        | UserTweetDenorm.insert_from(source, [UserTweetDenorm.username, UserTweetDenorm.num_tweets]).execute()
        +------------------------------------------------------
        """
        columns = [getattr(cls, field) if isinstance(field, basestring) else field for field in fields]
        return ModelInsert(cls, insert=query, columns=columns)

    @classmethod
    def replace(cls, __data=None, **insert):
        """
        创建使用 replace 解决冲突的插入查询

        Args:
            __data (dict) -- dict 字段到要插入的值。
            insert -- 字段名到值的映射。
        """
        return cls.insert(__data, **insert).on_conflict('REPLACE')

    @classmethod
    def replace_many(cls, rows, fields=None):
        """
        使用替换来解决冲突，插入多行数据。

        Args:
            rows -- 生成要插入的行的ITable。
            fields (list) -- 正在插入的字段列表。
        """
        return (cls
                .insert_many(rows=rows, fields=fields)
                .on_conflict('REPLACE'))

    @classmethod
    def raw(cls, sql, *params):
        """
        直接执行 SQL 查询。
        +------------------------------------------------------
        | q = User.raw('select id, username from users')
        | for user in q:
        |     print(user.id, user.username)
        +------------------------------------------------------
        """
        return ModelRaw(cls, sql, params)

    @classmethod
    def delete(cls):
        """
        删除
        +------------------------------------------------------
        | q = User.delete().where(User.active == False)
        | q.execute()  # Remove the rows, return number of rows removed.
        +------------------------------------------------------
        """
        return ModelDelete(cls)

    @classmethod
    def create(cls, **query):
        """
        在表中插入新行并返回相应的模型实例。

        Args:
            query -- 字段名到值的映射。
        """
        inst = cls(**query)
        inst.save(force_insert=True)
        return inst

    @classmethod
    def bulk_create(cls, model_list, batch_size=None):
        """
        有效地将多个未保存的模型实例插入数据库。

        Args:
            model_list (iterable) -- 未保存的列表或其他不可保存的列表 Model 实例。
            batch_size (int) -- 每次插入要批处理的行数。如果未指定，所有模型都将插入到单个查询中。
        """
        if batch_size is not None:
            batches = chunked(model_list, batch_size)
        else:
            batches = [model_list]

        field_names = list(cls._meta.sorted_field_names)
        if cls._meta.auto_increment:
            pk_name = cls._meta.primary_key.name
            field_names.remove(pk_name)
            ids_returned = cls._meta.database.returning_clause
        else:
            ids_returned = False

        fields = [cls._meta.fields[field_name] for field_name in field_names]
        for batch in batches:
            accum = ([getattr(model, f) for f in field_names]
                     for model in batch)
            res = cls.insert_many(accum, fields=fields).execute()
            if ids_returned and res is not None:
                for (obj_id,), model in zip(res, batch):
                    setattr(model, pk_name, obj_id)

    @classmethod
    def bulk_update(cls, model_list, fields, batch_size=None):
        """
        有效更新多个模型实例。

        Args:
            model_list (iterable) -- 列表 Model 实例。
            fields (list) -- 要更新的字段列表。
            batch_size (int) -- 每次插入要批处理的行数。如果未指定，所有模型都将插入到单个查询中。
        Returns:
            已更新的行总数。
        """
        if isinstance(cls._meta.primary_key, CompositeKey):
            raise ValueError('bulk_update() is not supported for models with '
                             'a composite primary key.')

        # First normalize list of fields so all are field instances.
        fields = [cls._meta.fields[f] if isinstance(f, basestring) else f
                  for f in fields]
        # Now collect list of attribute names to use for values.
        attrs = [field.object_id_name if isinstance(field, ForeignKeyField) else field.name for field in fields]

        if batch_size is not None:
            batches = chunked(model_list, batch_size)
        else:
            batches = [model_list]

        n = 0
        for batch in batches:
            id_list = [model._pk for model in batch]
            update = {}
            for field, attr in zip(fields, attrs):
                accum = []
                for model in batch:
                    value = getattr(model, attr)
                    if not isinstance(value, Node):
                        value = Value(value, converter=field.db_value)
                    accum.append((model._pk, value))
                case = Case(cls._meta.primary_key, accum)
                update[field] = case

            n += (cls.update(update)
                  .where(cls._meta.primary_key.in_(id_list))
                  .execute())
        return n

    @classmethod
    def noop(cls):
        """
        返回 NoopModelSelect
        """
        return NoopModelSelect(cls, ())

    @classmethod
    def get(cls, *query, **filters):
        """
        检索与给定筛选器匹配的单个模型实例

        Args:
            query -- 零或更多 Expression 物体。
            filters -- 将字段名映射为django样式筛选器的值。
        Returns:
            与指定筛选器匹配的模型实例
        """
        sq = cls.select()
        if query:
            # Handle simple lookup using just the primary key.
            if len(query) == 1 and isinstance(query[0], int):
                sq = sq.where(cls._meta.primary_key == query[0])
            else:
                sq = sq.where(*query)
        if filters:
            sq = sq.filter(**filters)
        return sq.get()

    @classmethod
    def get_or_none(cls, *query, **filters):
        """
        相同的 Model.get() 但回报 None 如果没有与给定过滤器匹配的模型。
        """
        try:
            return cls.get(*query, **filters)
        except DoesNotExist:
            pass

    @classmethod
    def get_by_id(cls, pk):
        """
        Args:
            pk -- 主键值。
        Returns:
            Model.get() 按主键指定查找
        """
        return cls.get(cls._meta.primary_key == pk)

    @classmethod
    def set_by_id(cls, key, value):
        """
        Args:
            key -- 主键值。
            value (dict) -- 字段到要更新的值的映射。
        Returns:
            用给定的主键更新数据的简写方法。如果不存在具有给定主键的行，则不会引发异常。
        +------------------------------------------------------
        | # Set "is_admin" to True on user with id=3.
        | User.set_by_id(3, {'is_admin': True})
        +------------------------------------------------------
        """
        if key is None:
            return cls.insert(value).execute()
        else:
            return (cls.update(value)
                    .where(cls._meta.primary_key == key).execute())

    @classmethod
    def delete_by_id(cls, pk):
        """
        用于删除具有给定主键的行

        Args:
            pk -- 主键值
        """
        return cls.delete().where(cls._meta.primary_key == pk).execute()

    @classmethod
    def get_or_create(cls, **kwargs):
        """
        尝试获取与给定筛选器匹配的行。如果找不到匹配行，则创建新行。

        Args:
            kwargs -- 字段名到值的映射。
            defaults -- 创建新行时使用的默认值。
        """
        defaults = kwargs.pop('defaults', {})
        query = cls.select()
        for field, value in kwargs.items():
            query = query.where(getattr(cls, field) == value)

        try:
            return query.get(), False
        except cls.DoesNotExist:
            try:
                if defaults:
                    kwargs.update(defaults)
                with cls._meta.database.atomic():
                    return cls.create(**kwargs), True
            except IntegrityError as exc:
                try:
                    return query.get(), False
                except cls.DoesNotExist:
                    raise exc

    @classmethod
    def filter(cls, *dq_nodes, **filters):
        """
        ModelSelect 查询。

        Args:
            dq_nodes -- 零或更多 DQ 物体。
            filters -- Django 风格的过滤器。
        """
        return cls.select().filter(*dq_nodes, **filters)

    def get_id(self):
        """
        返回模型实例的主键
        """
        return getattr(self, self._meta.primary_key.name)

    _pk = property(get_id)

    @_pk.setter
    def _pk(self, value):
        setattr(self, self._meta.primary_key.name, value)

    def _pk_expr(self):
        return self._meta.primary_key == self._pk

    def _prune_fields(self, field_dict, only):
        new_data = {}
        for field in only:
            if isinstance(field, basestring):
                field = self._meta.combined[field]
            if field.name in field_dict:
                new_data[field.name] = field_dict[field.name]
        return new_data

    def _populate_unsaved_relations(self, field_dict):
        for foreign_key_field in self._meta.refs:
            foreign_key = foreign_key_field.name
            conditions = (
                foreign_key in field_dict and
                field_dict[foreign_key] is None and
                self._rel_.get(foreign_key) is not None)
            if conditions:
                setattr(self, foreign_key, getattr(self, foreign_key))
                field_dict[foreign_key] = self._data_[foreign_key]

    def save(self, force_insert=False, only=None):
        """
        在模型实例中保存数据。
        """
        field_dict = self._data_.copy()
        if self._meta.primary_key is not False:
            pk_field = self._meta.primary_key
            pk_value = self._pk
        else:
            pk_field = pk_value = None
        if only:
            field_dict = self._prune_fields(field_dict, only)
        elif self._meta.only_save_dirty and not force_insert:
            field_dict = self._prune_fields(field_dict, self.dirty_fields)
            if not field_dict:
                self._dirty.clear()
                return False

        self._populate_unsaved_relations(field_dict)
        rows = 1

        if pk_value is not None and not force_insert:
            if self._meta.composite_key:
                for pk_part_name in pk_field.field_names:
                    field_dict.pop(pk_part_name, None)
            else:
                field_dict.pop(pk_field.name, None)
            if not field_dict:
                raise ValueError('no data to save!')
            rows = self.update(**field_dict).where(self._pk_expr()).execute()
        elif pk_field is not None:
            pk = self.insert(**field_dict).execute()
            if pk is not None and (self._meta.auto_increment or
                                   pk_value is None):
                self._pk = pk
        else:
            self.insert(**field_dict).execute()

        self._dirty.clear()
        return rows

    def is_dirty(self):
        """
        返回布尔值，指示是否手动设置了任何字段。
        """
        return bool(self._dirty)

    @property
    def dirty_fields(self):
        """
        返回已修改字段的列表。
        """
        return [f for f in self._meta.sorted_fields if f.name in self._dirty]

    def dependencies(self, search_nullable=False):
        """
        生成依赖模型的查询列表

        Args:
            search_nullable (bool)
        """
        model_class = type(self)
        stack = [(type(self), None)]
        seen = set()

        while stack:
            klass, query = stack.pop()
            if klass in seen:
                continue
            seen.add(klass)
            for fk, rel_model in klass._meta.backrefs.items():
                if rel_model is model_class or query is None:
                    node = (fk == self._data_[fk.rel_field.name])
                else:
                    node = fk << query
                subquery = (rel_model.select(rel_model._meta.primary_key)
                            .where(node))
                if not fk.null or search_nullable:
                    stack.append((rel_model, subquery))
                yield (node, fk)

    def delete_instance(self, recursive=False, delete_nullable=False):
        """
        删除给定的实例

        Args;
            recursive (bool) -- 删除相关模型。
            delete_nullable (bool) -- 删除具有空外键的相关模型。
        """
        if recursive:
            dependencies = self.dependencies(delete_nullable)
            for query, fk in reversed(list(dependencies)):
                model = fk.model
                if fk.null and not delete_nullable:
                    model.update(**{fk.name: None}).where(query).execute()
                else:
                    model.delete().where(query).execute()
        return type(self).delete().where(self._pk_expr()).execute()

    def __hash__(self):
        return hash((self.__class__, self._pk))

    def __eq__(self, other):
        return (
            other.__class__ == self.__class__ and
            self._pk is not None and
            other._pk == self._pk)

    def __ne__(self, other):
        return not self == other

    def _sql_(self, ctx):
        return ctx.sql(getattr(self, self._meta.primary_key.name))

    @classmethod
    def bind(cls, database, bind_refs=True, bind_backrefs=True):
        """
        Args:
            database (Database) -- 要绑定到的数据库。
            bind_refs (bool) -- 绑定相关模型。
            bind_backrefs (bool) -- 绑定与引用相关的模型。
        """
        is_different = cls._meta.database is not database
        cls._meta.set_database(database)
        if bind_refs or bind_backrefs:
            G = cls._meta.model_graph(refs=bind_refs, backrefs=bind_backrefs)
            for _, model, is_backref in G:
                model._meta.set_database(database)
        return is_different

    @classmethod
    def bind_ctx(cls, database, bind_refs=True, bind_backrefs=True):
        """
        bind() ，但返回一个上下文管理器，该管理器只在包装块的持续时间内绑定模型。
        """
        return _BoundModelsContext((cls,), database, bind_refs, bind_backrefs)

    @classmethod
    def table_exists(cls):
        """
        布尔值，指示表是否存在。
        """
        M = cls._meta
        return cls._schema.database.table_exists(M.table.__name__, M.schema)

    @classmethod
    def create_table(cls, safe=True, **options):
        """
        创建模型表、索引、约束和序列。
        """
        if 'fail_silently' in options:
            _deprecated_('"fail_silently" has been deprecated in favor of '
                           '"safe" for the create_table() method.')
            safe = options.pop('fail_silently')

        if safe and not cls._schema.database.safe_create_index \
           and cls.table_exists():
            return
        if cls._meta.temporary:
            options.setdefault('temporary', cls._meta.temporary)
        cls._schema.create_all(safe, **options)

    @classmethod
    def drop_table(cls, safe=True, drop_sequences=True, **options):
        """
        删除模型表
        safe (bool) -- 如果设置为 True ，创建表查询将包括 IF EXISTS 条款。
        """
        if safe and not cls._schema.database.safe_drop_index \
           and not cls.table_exists():
            return
        if cls._meta.temporary:
            options.setdefault('temporary', cls._meta.temporary)
        cls._schema.drop_all(safe, drop_sequences, **options)

    @classmethod
    def truncate_table(cls, **options):
        """
        截断（删除所有行）模型。
        """
        cls._schema.truncate_table(**options)

    @classmethod
    def index(cls, *fields, **kwargs):
        """
        索引
        """
        return ModelIndex(cls, fields, **kwargs)

    @classmethod
    def add_index(cls, *fields, **kwargs):
        """
        添加索引
        """
        if len(fields) == 1 and isinstance(fields[0], (SQL, Index)):
            cls._meta.indexes.append(fields[0])
        else:
            cls._meta.indexes.append(ModelIndex(cls, fields, **kwargs))


class ModelAlias(Node):
    """Provide a separate reference to a model in a query."""

    def __init__(self, model, alias=None):
        self.__dict__['model'] = model
        self.__dict__['alias'] = alias

    def __getattr__(self, attr):
        model_attr = getattr(self.model, attr)
        if isinstance(model_attr, Field):
            self.__dict__[attr] = FieldAlias.create(self, model_attr)
            return self.__dict__[attr]
        return model_attr

    def __setattr__(self, attr, value):
        raise AttributeError('Cannot set attributes on model aliases.')

    def get_field_aliases(self):
        """
        获取 field aliases
        """
        return [getattr(self, n) for n in self.model._meta.sorted_field_names]

    def select(self, *selection):
        """
        Select 查询方法
        """
        if not selection:
            selection = self.get_field_aliases()
        return ModelSelect(self, selection)

    def __call__(self, **kwargs):
        return self.model(**kwargs)

    def _sql_(self, ctx):
        if ctx.scope == SCOPE_VALUES:
            # Return the quoted table name.
            return ctx.sql(self.model)

        if self.alias:
            ctx.alias_manager[self] = self.alias

        if ctx.scope == SCOPE_SOURCE:
            # Define the table and its alias.
            return (ctx
                    .sql(self.model._meta.entity)
                    .literal(' AS ')
                    .sql(Entity(ctx.alias_manager[self])))
        else:
            # Refer to the table using the alias.
            return ctx.sql(Entity(ctx.alias_manager[self]))


class FieldAlias(Field):
    """
    字段别名
    """
    def __init__(self, source, field):
        self.source = source
        self.model = source.model
        self.field = field

    @classmethod
    def create(cls, source, field):
        """
        创建字段别名
        """
        class _FieldAlias(cls, type(field)):
            pass
        return _FieldAlias(source, field)

    def clone(self):
        """
        clone
        """
        return FieldAlias(self.source, self.field)

    def adapt(self, value):
        """
        格式化 value
        """
        return self.field.adapt(value)

    def python_value(self, value):
        """
        将 python 值强制为适合存储在数据库中的值。
        """
        return self.field.python_value(value)

    def db_value(self, value):
        """
        将 python 值强制为适合存储在数据库中的值。
        """
        return self.field.db_value(value)

    def __getattr__(self, attr):
        return self.source if attr == 'model' else getattr(self.field, attr)

    def _sql_(self, ctx):
        return ctx.sql(Column(self.source, self.field.column_name))


def sort_models(models):
    """
    排序
    """
    models = set(models)
    seen = set()
    ordering = []

    def dfs(model):
        """
        dfs
        """
        if model in models and model not in seen:
            seen.add(model)
            for foreign_key, rel_model in model._meta.refs.items():
                # Do not depth-first search deferred foreign-keys as this can
                # cause tables to be created in the incorrect order.
                if not foreign_key.deferred:
                    dfs(rel_model)
            if model._meta.depends_on:
                for dependency in model._meta.depends_on:
                    dfs(dependency)
            ordering.append(model)

    def names(m):
        """
        返回二元组
        """
        return (m._meta.name, m._meta.table_name)

    for m in sorted(models, key=names):
        dfs(m)
    return ordering


class _ModelQueryHelper(object):
    default_row_type = ROW.MODEL

    def __init__(self, *args, **kwargs):
        super(_ModelQueryHelper, self).__init__(*args, **kwargs)
        if not self._database:
            self._database = self.model._meta.database

    @Node.copy
    def objects(self, constructor=None):
        """
        objects
        """
        self._row_type = ROW.CONSTRUCTOR
        self._constructor = self.model if constructor is None else constructor

    def _get_cursor_wrapper(self, cursor):
        row_type = self._row_type or self.default_row_type
        if row_type == ROW.MODEL:
            return self._get_model_cursor_wrapper(cursor)
        elif row_type == ROW.DICT:
            return ModelDictCursorWrapper(cursor, self.model, self._returning)
        elif row_type == ROW.TUPLE:
            return ModelTupleCursorWrapper(cursor, self.model, self._returning)
        elif row_type == ROW.NAMED_TUPLE:
            return ModelNamedTupleCursorWrapper(cursor, self.model,
                                                self._returning)
        elif row_type == ROW.CONSTRUCTOR:
            return ModelObjectCursorWrapper(cursor, self.model,
                                            self._returning, self._constructor)
        else:
            raise ValueError('Unrecognized row type: "%s".' % row_type)

    def _get_model_cursor_wrapper(self, cursor):
        return ModelObjectCursorWrapper(cursor, self.model, [], self.model)


class ModelRaw(_ModelQueryHelper, RawQuery):
    """
    Raw 类
    """
    def __init__(self, model, sql, params, **kwargs):
        self.model = model
        self._returning = ()
        super(ModelRaw, self).__init__(sql=sql, params=params, **kwargs)

    def get(self):
        """
        获取第一条数据
        """
        try:
            return self.execute()[0]
        except IndexError:
            sql, params = self.sql()
            raise self.model.DoesNotExist('%s instance matching query does '
                                          'not exist:\nSQL: %s\nParams: %s' %
                                          (self.model, sql, params))


class BaseModelSelect(_ModelQueryHelper):
    """
    select 基类
    """
    def union_all(self, rhs):
        """
        UNION ALL
        """
        return ModelCompoundSelectQuery(self.model, self, 'UNION ALL', rhs)
    __add__ = union_all

    def union(self, rhs):
        """
        UNION
        """
        return ModelCompoundSelectQuery(self.model, self, 'UNION', rhs)
    __or__ = union

    def intersect(self, rhs):
        """
        INTERSECT
        """
        return ModelCompoundSelectQuery(self.model, self, 'INTERSECT', rhs)
    __and__ = intersect

    def except_(self, rhs):
        """
        EXCEPT
        """
        return ModelCompoundSelectQuery(self.model, self, 'EXCEPT', rhs)
    __sub__ = except_

    def __iter__(self):
        if not self._cursor_wrapper:
            self.execute()
        return iter(self._cursor_wrapper)

    def prefetch(self, *subqueries):
        """
        prefetch
        """
        return prefetch(self, *subqueries)

    def get(self, database=None):
        """
        获取数据
        """
        clone = self.paginate(1, 1)
        clone._cursor_wrapper = None
        try:
            return clone.execute(database)[0]
        except IndexError:
            sql, params = clone.sql()
            raise self.model.DoesNotExist('%s instance matching query does '
                                          'not exist:\nSQL: %s\nParams: %s' %
                                          (clone.model, sql, params))

    @Node.copy
    def group_by(self, *columns):
        """
        GROUP BY, 组合数据
        """
        grouping = []
        for column in columns:
            if is_model(column):
                grouping.extend(column._meta.sorted_fields)
            elif isinstance(column, Table):
                if not column._columns:
                    raise ValueError('Cannot pass a table to group_by() that '
                                     'does not have columns explicitly '
                                     'declared.')
                grouping.extend([getattr(column, col_name)
                                 for col_name in column._columns])
            else:
                grouping.append(column)
        self._group_by = grouping


class ModelCompoundSelectQuery(BaseModelSelect, CompoundSelectQuery):
    """
    ModelCompound SelectQuery
    """
    def __init__(self, model, *args, **kwargs):
        self.model = model
        super(ModelCompoundSelectQuery, self).__init__(*args, **kwargs)

    def _get_model_cursor_wrapper(self, cursor):
        return self.lhs._get_model_cursor_wrapper(cursor)


def _normalize_model_select(fields_or_models):
    fields = []
    for fm in fields_or_models:
        if is_model(fm):
            fields.extend(fm._meta.sorted_fields)
        elif isinstance(fm, ModelAlias):
            fields.extend(fm.get_field_aliases())
        elif isinstance(fm, Table) and fm._columns:
            fields.extend([getattr(fm, col) for col in fm._columns])
        else:
            fields.append(fm)
    return fields


class ModelSelect(BaseModelSelect, Select):
    """
    Select
    """
    def __init__(self, model, fields_or_models, is_default=False):
        self.model = self._join_ctx = model
        self._joins = {}
        self._is_default = is_default
        fields = _normalize_model_select(fields_or_models)
        super(ModelSelect, self).__init__([model], fields)

    def clone(self):
        """
        clone
        """
        clone = super(ModelSelect, self).clone()
        if clone._joins:
            clone._joins = dict(clone._joins)
        return clone

    def select(self, *fields_or_models):
        """
        select
        """
        if fields_or_models or not self._is_default:
            self._is_default = False
            fields = _normalize_model_select(fields_or_models)
            return super(ModelSelect, self).select(*fields)
        return self

    def switch(self, ctx=None):
        """
        switch
        """
        self._join_ctx = self.model if ctx is None else ctx
        return self

    def _get_model(self, src):
        if is_model(src):
            return src, True
        elif isinstance(src, Table) and src._model:
            return src._model, False
        elif isinstance(src, ModelAlias):
            return src.model, False
        elif isinstance(src, ModelSelect):
            return src.model, False
        return None, False

    def _normalize_join(self, src, dest, on, attr):
        # Allow "on" expression to have an alias that determines the
        # destination attribute for the joined data.
        on_alias = isinstance(on, Alias)
        if on_alias:
            attr = attr or on._alias
            on = on.alias()

        # Obtain references to the source and destination models being joined.
        src_model, src_is_model = self._get_model(src)
        dest_model, dest_is_model = self._get_model(dest)

        if src_model and dest_model:
            self._join_ctx = dest
            constructor = dest_model

            # In the case where the "on" clause is a Column or Field, we will
            # convert that field into the appropriate predicate expression.
            if not (src_is_model and dest_is_model) and isinstance(on, Column):
                if on.source is src:
                    to_field = src_model._meta.columns[on.name]
                elif on.source is dest:
                    to_field = dest_model._meta.columns[on.name]
                else:
                    raise AttributeError('"on" clause Column %s does not '
                                         'belong to %s or %s.' %
                                         (on, src_model, dest_model))
                on = None
            elif isinstance(on, Field):
                to_field = on
                on = None
            else:
                to_field = None

            fk_field, is_backref = self._generate_on_clause(
                src_model, dest_model, to_field, on)

            if on is None:
                src_attr = 'name' if src_is_model else 'column_name'
                dest_attr = 'name' if dest_is_model else 'column_name'
                if is_backref:
                    lhs = getattr(dest, getattr(fk_field, dest_attr))
                    rhs = getattr(src, getattr(fk_field.rel_field, src_attr))
                else:
                    lhs = getattr(src, getattr(fk_field, src_attr))
                    rhs = getattr(dest, getattr(fk_field.rel_field, dest_attr))
                on = (lhs == rhs)

            if not attr:
                if fk_field is not None and not is_backref:
                    attr = fk_field.name
                else:
                    attr = dest_model._meta.name
            elif on_alias and fk_field is not None and \
                    attr == fk_field.object_id_name and not is_backref:
                raise ValueError('Cannot assign join alias to "%s", as this '
                                 'attribute is the object_id_name for the '
                                 'foreign-key field "%s"' % (attr, fk_field))

        elif isinstance(dest, Source):
            constructor = dict
            attr = attr or dest._alias
            if not attr and isinstance(dest, Table):
                attr = attr or dest.__name__

        return (on, attr, constructor)

    def _generate_on_clause(self, src, dest, to_field=None, on=None):
        meta = src._meta
        is_backref = fk_fields = False

        # Get all the foreign keys between source and dest, and determine if
        # the join is via a back-reference.
        if dest in meta.model_refs:
            fk_fields = meta.model_refs[dest]
        elif dest in meta.model_backrefs:
            fk_fields = meta.model_backrefs[dest]
            is_backref = True

        if not fk_fields:
            if on is not None:
                return None, False
            raise ValueError('Unable to find foreign key between %s and %s. '
                             'Please specify an explicit join condition.' %
                             (src, dest))
        elif to_field is not None:
            # If the foreign-key field was specified explicitly, remove all
            # other foreign-key fields from the list.
            target = (to_field.field if isinstance(to_field, FieldAlias)
                      else to_field)
            fk_fields = [f for f in fk_fields if ((f is target) or (is_backref and f.rel_field is to_field))]

        if len(fk_fields) == 1:
            return fk_fields[0], is_backref

        if on is None:
            # If multiple foreign-keys exist, try using the FK whose name
            # matches that of the related model. If not, raise an error as this
            # is ambiguous.
            for fk in fk_fields:
                if fk.name == dest._meta.name:
                    return fk, is_backref

            raise ValueError('More than one foreign key between %s and %s.'
                             ' Please specify which you are joining on.' %
                             (src, dest))

        # If there are multiple foreign-keys to choose from and the join
        # predicate is an expression, we'll try to figure out which
        # foreign-key field we're joining on so that we can assign to the
        # correct attribute when resolving the model graph.
        to_field = None
        if isinstance(on, Expression):
            lhs, rhs = on.lhs, on.rhs
            # Coerce to set() so that we force Python to compare using the
            # object's hash rather than equality test, which returns a
            # false-positive due to overriding __eq__.
            fk_set = set(fk_fields)

            if isinstance(lhs, Field):
                lhs_f = lhs.field if isinstance(lhs, FieldAlias) else lhs
                if lhs_f in fk_set:
                    to_field = lhs_f
            elif isinstance(rhs, Field):
                rhs_f = rhs.field if isinstance(rhs, FieldAlias) else rhs
                if rhs_f in fk_set:
                    to_field = rhs_f

        return to_field, False

    @Node.copy
    def join(self, dest, join_type='INNER', on=None, src=None, attr=None):
        """
        join

        Args:
            dest -- A Model ， ModelAlias ， Select 查询或要联接到的其他对象。
            join_type (str) -- 连接类型，默认为内部。
            on -- 连接谓词或 ForeignKeyField 加入。
            src -- 显式指定联接的源。如果未指定，则当前 join context 将被使用。
            attr (str) -- 从联接模型投影列时使用的属性。
        """
        src = self._join_ctx if src is None else src

        if join_type != JOIN.CROSS:
            on, attr, constructor = self._normalize_join(src, dest, on, attr)
            if attr:
                self._joins.setdefault(src, [])
                self._joins[src].append((dest, attr, constructor))
        elif on is not None:
            raise ValueError('Cannot specify on clause with cross join.')

        if not self._from_list:
            raise ValueError('No sources to join on.')

        item = self._from_list.pop()
        self._from_list.append(Join(item, dest, join_type, on))

    def join_from(self, src, dest, join_type='INNER', on=None, attr=None):
        """
        Args:
            src -- 联接的源。
            dest -- 要联接到的表。
        """
        return self.join(dest, join_type, on, src, attr)

    def _get_model_cursor_wrapper(self, cursor):
        if len(self._from_list) == 1 and not self._joins:
            return ModelObjectCursorWrapper(cursor, self.model,
                                            self._returning, self.model)
        return ModelCursorWrapper(cursor, self.model, self._returning,
                                  self._from_list, self._joins)

    def ensure_join(self, lm, rm, on=None, **join_kwargs):
        """
        ensure_join
        """
        join_ctx = self._join_ctx
        for dest, attr, constructor in self._joins.get(lm, []):
            if dest == rm:
                return self
        return self.switch(lm).join(rm, on=on, **join_kwargs).switch(join_ctx)

    def convert_dict_to_node(self, qdict):
        """
        转换 dict to node
        """
        accum = []
        joins = []
        fks = (ForeignKeyField, BackrefAccessor)
        for key, value in sorted(qdict.items()):
            curr = self.model
            if '__' in key and key.rsplit('__', 1)[1] in DJANGO_MAP:
                key, op = key.rsplit('__', 1)
                op = DJANGO_MAP[op]
            elif value is None:
                op = DJANGO_MAP['is']
            else:
                op = DJANGO_MAP['eq']

            if '__' not in key:
                # Handle simplest case. This avoids joining over-eagerly when a
                # direct FK lookup is all that is required.
                model_attr = getattr(curr, key)
            else:
                for piece in key.split('__'):
                    for dest, attr, _ in self._joins.get(curr, ()):
                        if attr == piece or (isinstance(dest, ModelAlias) and
                                             dest.alias == piece):
                            curr = dest
                            break
                    else:
                        model_attr = getattr(curr, piece)
                        if value is not None and isinstance(model_attr, fks):
                            curr = model_attr.rel_model
                            joins.append(model_attr)
            accum.append(op(model_attr, value))
        return accum, joins

    def filter(self, *args, **kwargs):
        """
        # normalize args and kwargs into a new expression
        """
        dq_node = ColumnBase()
        if args:
            dq_node &= reduce(operator.and_, [a.clone() for a in args])
        if kwargs:
            dq_node &= DQ(**kwargs)

        # dq_node should now be an Expression, lhs = Node(), rhs = ...
        q = collections.deque([dq_node])
        dq_joins = set()
        while q:
            curr = q.popleft()
            if not isinstance(curr, Expression):
                continue
            for side, piece in (('lhs', curr.lhs), ('rhs', curr.rhs)):
                if isinstance(piece, DQ):
                    query, joins = self.convert_dict_to_node(piece.query)
                    dq_joins.update(joins)
                    expression = reduce(operator.and_, query)
                    # Apply values from the DQ object.
                    if piece._negated:
                        expression = Negated(expression)
                    #expression._alias = piece._alias
                    setattr(curr, side, expression)
                else:
                    q.append(piece)

        dq_node = dq_node.rhs

        query = self.clone()
        for field in dq_joins:
            if isinstance(field, ForeignKeyField):
                lm, rm = field.model, field.rel_model
                field_obj = field
            elif isinstance(field, BackrefAccessor):
                lm, rm = field.model, field.rel_model
                field_obj = field.field
            query = query.ensure_join(lm, rm, field_obj)
        return query.where(dq_node)

    def create_table(self, name, safe=True, **meta):
        """
        创建 table
        """
        return self.model._schema.create_table_as(name, self, safe, **meta)

    def _sql_selection_(self, ctx, is_subquery=False):
        if self._is_default and is_subquery and len(self._returning) > 1 and \
           self.model._meta.primary_key is not False:
            return ctx.sql(self.model._meta.primary_key)

        return ctx.sql(CommaNodeList(self._returning))


class NoopModelSelect(ModelSelect):
    """
    NoopModelSelect
    """
    def _sql_(self, ctx):
        return self.model._meta.database.get_noop_select(ctx)

    def _get_cursor_wrapper(self, cursor):
        return CursorWrapper(cursor)


class _ModelWriteQueryHelper(_ModelQueryHelper):
    def __init__(self, model, *args, **kwargs):
        self.model = model
        super(_ModelWriteQueryHelper, self).__init__(model, *args, **kwargs)

    def returning(self, *returning):
        """
        返回结果
        """
        accum = []
        for item in returning:
            if is_model(item):
                accum.extend(item._meta.sorted_fields)
            else:
                accum.append(item)
        return super(_ModelWriteQueryHelper, self).returning(*accum)

    def _set_table_alias(self, ctx):
        table = self.model._meta.table
        ctx.alias_manager[table] = table.__name__


class ModelUpdate(_ModelWriteQueryHelper, Update):
    """
    update 类
    """
    pass


class ModelInsert(_ModelWriteQueryHelper, Insert):
    """
    Insert 类
    """
    default_row_type = ROW.TUPLE

    def __init__(self, *args, **kwargs):
        super(ModelInsert, self).__init__(*args, **kwargs)
        if self._returning is None and self.model._meta.database is not None:
            if self.model._meta.database.returning_clause:
                self._returning = self.model._meta.get_primary_keys()

    def returning(self, *returning):
        """
        # By default ModelInsert will yield a `tuple` containing the
        # primary-key of the newly inserted row. But if we are explicitly
        # specifying a returning clause and have not set a row type, we will
        # default to returning model instances instead.
        """
        if returning and self._row_type is None:
            self._row_type = ROW.MODEL
        return super(ModelInsert, self).returning(*returning)

    def get_default_data(self):
        """
        返回默认数据
        """
        return self.model._meta.defaults

    def get_default_columns(self):
        """
        返回默认列
        """
        fields = self.model._meta.sorted_fields
        return fields[1:] if self.model._meta.auto_increment else fields


class ModelDelete(_ModelWriteQueryHelper, Delete):
    """
    Delete 类
    """
    pass


def safe_python_value(conv_func):
    """
    转换 python 数据
    """
    def validate(value):
        """
        返回转换后的数据
        """
        try:
            return conv_func(value)
        except (TypeError, ValueError):
            return value
    return validate


class BaseModelCursorWrapper(DictCursorWrapper):

    """
    BaseModelCursor 封装
    """
    def __init__(self, cursor, model, columns):
        super(BaseModelCursorWrapper, self).__init__(cursor)
        self.model = model
        self.select = columns or []

    def _initialize_columns(self):
        combined = self.model._meta.combined
        table = self.model._meta.table
        description = self.cursor.description

        self.ncols = len(self.cursor.description)
        self.columns = []
        self.converters = converters = [None] * self.ncols
        self.fields = fields = [None] * self.ncols

        for idx, description_item in enumerate(description):
            column = description_item[0]
            dot_index = column.find('.')
            if dot_index != -1:
                column = column[dot_index + 1:]

            column = column.strip('"')
            self.columns.append(column)
            try:
                raw_node = self.select[idx]
            except IndexError:
                if column in combined:
                    raw_node = node = combined[column]
                else:
                    continue
            else:
                node = raw_node.unwrap()

            # Heuristics used to attempt to get the field associated with a
            # given SELECT column, so that we can accurately convert the value
            # returned by the database-cursor into a Python object.
            if isinstance(node, Field):
                if raw_node._coerce:
                    converters[idx] = node.python_value
                fields[idx] = node
                if (column == node.name or column == node.column_name) and \
                   not raw_node.is_alias():
                    self.columns[idx] = node.name
            elif isinstance(node, Function) and node._coerce:
                if node._python_value is not None:
                    converters[idx] = node._python_value
                elif node.arguments and isinstance(node.arguments[0], Node):
                    # If the first argument is a field or references a column
                    # on a Model, try using that field's conversion function.
                    # This usually works, but we use "safe_python_value()" so
                    # that if a TypeError or ValueError occurs during
                    # conversion we can just fall-back to the raw cursor value.
                    first = node.arguments[0].unwrap()
                    if isinstance(first, Entity):
                        path = first._path[-1]  # Try to look-up by name.
                        first = combined.get(path)
                    if isinstance(first, Field):
                        converters[idx] = safe_python_value(first.python_value)
            elif column in combined:
                if node._coerce:
                    converters[idx] = combined[column].python_value
                if isinstance(node, Column) and node.source == table:
                    fields[idx] = combined[column]

    initialize = _initialize_columns

    def process_row(self, row):
        """
        处理 row
        """
        raise NotImplementedError


class ModelDictCursorWrapper(BaseModelCursorWrapper):
    """
    ModelDictCursor 封装
    """
    def process_row(self, row):
        """
        处理 row
        """
        result = {}
        columns, converters = self.columns, self.converters
        fields = self.fields

        for i in range(self.ncols):
            attr = columns[i]
            if attr in result:
                continue  # Don't overwrite if we have dupes.
            if converters[i] is not None:
                result[attr] = converters[i](row[i])
            else:
                result[attr] = row[i]

        return result


class ModelTupleCursorWrapper(ModelDictCursorWrapper):
    """
    ModelTupleCursor 封装
    """
    constructor = tuple

    def process_row(self, row):
        """
        处理 row
        """
        columns, converters = self.columns, self.converters
        return self.constructor([
            (converters[i](row[i]) if converters[i] is not None else row[i])
            for i in range(self.ncols)])


class ModelNamedTupleCursorWrapper(ModelTupleCursorWrapper):
    """
    ModelNamedTupleCursor 封装
    """
    def initialize(self):
        """
        初始化
        """
        self._initialize_columns()
        attributes = []
        for i in range(self.ncols):
            attributes.append(self.columns[i])
        self.tuple_class = collections.namedtuple('Row', attributes)
        self.constructor = lambda row: self.tuple_class(*row)


class ModelObjectCursorWrapper(ModelDictCursorWrapper):
    """
    ModelObjectCursor 封装
    """
    def __init__(self, cursor, model, select, constructor):
        self.constructor = constructor
        self.is_model = is_model(constructor)
        super(ModelObjectCursorWrapper, self).__init__(cursor, model, select)

    def process_row(self, row):
        """
        处理 row
        """
        data = super(ModelObjectCursorWrapper, self).process_row(row)
        if self.is_model:
            # Clear out any dirty fields before returning to the user.
            obj = self.constructor(__no_default__=1, **data)
            obj._dirty.clear()
            return obj
        else:
            return self.constructor(**data)


class ModelCursorWrapper(BaseModelCursorWrapper):
    """
    ModelCursor 封装
    """
    def __init__(self, cursor, model, select, from_list, joins):
        super(ModelCursorWrapper, self).__init__(cursor, model, select)
        self.from_list = from_list
        self.joins = joins

    def initialize(self):
        """
        初始化
        """
        self._initialize_columns()
        selected_src = set([field.model for field in self.fields
                            if field is not None])
        select, columns = self.select, self.columns

        self.key_to_constructor = {self.model: self.model}
        self.src_is_dest = {}
        self.src_to_dest = []
        accum = collections.deque(self.from_list)
        dests = set()
        while accum:
            curr = accum.popleft()
            if isinstance(curr, Join):
                accum.append(curr.lhs)
                accum.append(curr.rhs)
                continue

            if curr not in self.joins:
                continue

            for key, attr, constructor in self.joins[curr]:
                if key not in self.key_to_constructor:
                    self.key_to_constructor[key] = constructor
                    self.src_to_dest.append((curr, attr, key,
                                             isinstance(curr, dict)))
                    dests.add(key)
                    accum.append(key)

        # Ensure that we accommodate everything selected.
        for src in selected_src:
            if src not in self.key_to_constructor:
                if is_model(src):
                    self.key_to_constructor[src] = src
                elif isinstance(src, ModelAlias):
                    self.key_to_constructor[src] = src.model

        # Indicate which sources are also dests.
        for src, _, dest, _ in self.src_to_dest:
            self.src_is_dest[src] = src in dests and (dest in selected_src
                                                      or src in selected_src)

        self.column_keys = []
        for idx, node in enumerate(select):
            key = self.model
            field = self.fields[idx]
            if field is not None:
                if isinstance(field, FieldAlias):
                    key = field.source
                else:
                    key = field.model
            else:
                if isinstance(node, Node):
                    node = node.unwrap()
                if isinstance(node, Column):
                    key = node.source

            self.column_keys.append(key)

    def process_row(self, row):
        """
        执行 row
        """
        objects = {}
        object_list = []
        for key, constructor in self.key_to_constructor.items():
            objects[key] = constructor(__no_default__=True)
            object_list.append(objects[key])

        set_keys = set()
        for idx, key in enumerate(self.column_keys):
            instance = objects[key]
            column = self.columns[idx]
            value = row[idx]
            if value is not None:
                set_keys.add(key)
            if self.converters[idx]:
                value = self.converters[idx](value)

            if isinstance(instance, dict):
                instance[column] = value
            else:
                setattr(instance, column, value)

        # Need to do some analysis on the joins before this.
        for (src, attr, dest, is_dict) in self.src_to_dest:
            instance = objects[src]
            try:
                joined_instance = objects[dest]
            except KeyError:
                continue

            # If no fields were set on the destination instance then do not
            # assign an "empty" instance.
            if instance is None or dest is None or \
               (dest not in set_keys and not self.src_is_dest.get(dest)):
                continue

            if is_dict:
                instance[attr] = joined_instance
            else:
                setattr(instance, attr, joined_instance)

        # When instantiating models from a cursor, we clear the dirty fields.
        for instance in object_list:
            if isinstance(instance, Model):
                instance._dirty.clear()

        return objects[self.model]


class PrefetchQuery(collections.namedtuple('_PrefetchQuery', (
        'query', 'fields', 'is_backref', 'rel_models', 'field_to_name', 'model'))):
    """
    预查询
    """
    def __new__(cls, query, fields=None, is_backref=None, rel_models=None,
                field_to_name=None, model=None):
        if fields:
            if is_backref:
                if rel_models is None:
                    rel_models = [field.model for field in fields]
                foreign_key_attrs = [field.rel_field.name for field in fields]
            else:
                if rel_models is None:
                    rel_models = [field.rel_model for field in fields]
                foreign_key_attrs = [field.name for field in fields]
            field_to_name = list(zip(fields, foreign_key_attrs))
        model = query.model
        return super(PrefetchQuery, cls).__new__(
            cls, query, fields, is_backref, rel_models, field_to_name, model)

    def populate_instance(self, instance, id_map):
        """
        填充实例
        """
        if self.is_backref:
            for field in self.fields:
                identifier = instance._data_[field.name]
                key = (field, identifier)
                if key in id_map:
                    setattr(instance, field.name, id_map[key])
        else:
            for field, attname in self.field_to_name:
                identifier = instance._data_[field.rel_field.name]
                key = (field, identifier)
                rel_instances = id_map.get(key, [])
                for inst in rel_instances:
                    setattr(inst, attname, instance)
                setattr(instance, field.backref, rel_instances)

    def store_instance(self, instance, id_map):
        """
        存储实例
        """
        for field, attname in self.field_to_name:
            identity = field.rel_field.python_value(instance._data_[attname])
            key = (field, identity)
            if self.is_backref:
                id_map[key] = instance
            else:
                id_map.setdefault(key, [])
                id_map[key].append(instance)


def prefetch_add_subquery(sq, subqueries):
    """
    预取查询
    """
    fixed_queries = [PrefetchQuery(sq)]
    for i, subquery in enumerate(subqueries):
        if isinstance(subquery, tuple):
            subquery, target_model = subquery
        else:
            target_model = None
        if not isinstance(subquery, Query) and is_model(subquery) or \
           isinstance(subquery, ModelAlias):
            subquery = subquery.select()
        subquery_model = subquery.model
        fks = backrefs = None
        for j in reversed(range(i + 1)):
            fixed = fixed_queries[j]
            last_query = fixed.query
            last_model = last_obj = fixed.model
            if isinstance(last_model, ModelAlias):
                last_model = last_model.model
            rels = subquery_model._meta.model_refs.get(last_model, [])
            if rels:
                fks = [getattr(subquery_model, fk.name) for fk in rels]
                pks = [getattr(last_obj, fk.rel_field.name) for fk in rels]
            else:
                backrefs = subquery_model._meta.model_backrefs.get(last_model)
            if (fks or backrefs) and ((target_model is last_obj) or
                                      (target_model is None)):
                break

        if not fks and not backrefs:
            tgt_err = ' using %s' % target_model if target_model else ''
            raise AttributeError('Error: unable to find foreign key for '
                                 'query: %s%s' % (subquery, tgt_err))

        dest = (target_model,) if target_model else None

        if fks:
            expr = reduce(operator.or_, [
                (fk << last_query.select(pk))
                for (fk, pk) in zip(fks, pks)])
            subquery = subquery.where(expr)
            fixed_queries.append(PrefetchQuery(subquery, fks, False, dest))
        elif backrefs:
            expressions = []
            for backref in backrefs:
                rel_field = getattr(subquery_model, backref.rel_field.name)
                fk_field = getattr(last_obj, backref.name)
                expressions.append(rel_field << last_query.select(fk_field))
            subquery = subquery.where(reduce(operator.or_, expressions))
            fixed_queries.append(PrefetchQuery(subquery, backrefs, True, dest))

    return fixed_queries


def prefetch(sq, *subqueries):
    """
    预查询
    """
    if not subqueries:
        return sq

    fixed_queries = prefetch_add_subquery(sq, subqueries)
    deps = {}
    rel_map = {}
    for pq in reversed(fixed_queries):
        query_model = pq.model
        if pq.fields:
            for rel_model in pq.rel_models:
                rel_map.setdefault(rel_model, [])
                rel_map[rel_model].append(pq)

        deps[query_model] = {}
        id_map = deps[query_model]
        has_relations = bool(rel_map.get(query_model))

        for instance in pq.query:
            if pq.fields:
                pq.store_instance(instance, id_map)
            if has_relations:
                for rel in rel_map[query_model]:
                    rel.populate_instance(instance, deps[rel.model])

    return list(pq.query)
