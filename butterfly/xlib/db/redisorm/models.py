# -*- coding: utf-8 -*-
import calendar
import time
import re
from .managers import ModelManager
from .utils import expire_to_datetime

# --- Metaclass magic


class ModelBase(type):
    """
    Metaclass for Model and its subclasses

    Used to set up a manager for model. Class constructor searches
    for model_manager instance and adds the reference to
    """
    def __new__(cls, name, parents, attrs):
        model_manager = attrs.pop('objects', None)
        if not model_manager:
            parent_mgrs = list(filter(None, [getattr(p, 'objects', None) for p in parents]))
            mgr_class = parent_mgrs[0].__class__
            model_manager = mgr_class()
        attrs['objects'] = model_manager
        model_manager.model_name = attrs.pop('model_name', to_underscore(name))
        model_manager.id_length = attrs.pop('id_length', 16)
        model_manager.system = attrs.pop('system', 'default')
        ret = type.__new__(cls, name, parents, attrs)
        model_manager.model = ret
        return ret


def to_underscore(name):
    """
    Helper function converting CamelCase to underscore: camel_case
    """
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


class ModelRedis(object):
    """
    Base model class
    """
    exclude_attrs = []
    unique_field = ""

    def __init__(self, **attrs):
        """
        Create a new model instance.

        :param id: optional. Create an instance with given id
        :param expire: optional. Set up expiration timestamp for the instance.
        When the expiration timestamp has reached, the model won't be accessible
        anymore and eventually will be removed from the database

        :param \*\*attrs: additional attributes of the instance. Will be pickled and
        written to the store
        """
        if self.unique_field:
            self.unique_tag = self.objects._gen_unitque_tag(attrs, self.unique_field)
        else:
            self.unique_tag = ""
        exclude_attrs_set = set(self.exclude_attrs or [])
        tags = self.objects._attrs_to_tags(attrs, exclude_attrs_set)
        self.tags = tags or []
        self._saved_tags = self.tags
        id = attrs.pop('id', None)
        expire = attrs.pop('expire', None)
        if id is not None:
            id = str(id)
        self.id = id
        self.attrs = attrs
        self.expire = expire_to_datetime(expire)

    def __getattr__(self, attr):
        try:
            return self.attrs[attr]
        except KeyError as e:
            raise AttributeError(e)

    def __eq__(self, other):
        if other.__class__ != self.__class__:
            return False
        return self.id == other.id

    def __repr__(self):
        return '<%s id:%s attrs:%s>' % (self.__class__.__name__, self.id, self.attrs)

    def set_expire(self, expire):
        self.expire = expire_to_datetime(expire)

    def set_unique(self, field_name=""):
        self.unique_field = field_name

    def ttl(self):
        """
        Return time to live in seconds (integer) or None, if instance is never
        expired

        If expire value is in the past, return 0.

        .. note:: test for ``instance.ttl is None``, not ``not instance.ttl``,
                  because in this context None is not the same as 0.
        """
        if not self.expire:
            return None
        expire = calendar.timegm(self.expire.timetuple())
        now = int(time.time())
        ttl = expire - now
        if ttl < 0:
            return 0
        return ttl


Model = ModelBase('Model', (ModelRedis, ), {'objects': ModelManager()})
"""
ModelBase 是元类
> (1) 元类是由“type”衍生而出
> (2) 元类的操作都在 __new__ 中完成

注意：通过元类创建的类（即 Model)，第一个参数是父类，第二个参数是 metaclass

class 后声明“我是谁”
小括号内声明“我来自哪里”
中括号内声明“我要到哪里去”

Model = ModelBase('Model', (ModelRedis, ), {'objects': ModelManager()})
等同于：
class Model(ModelRedis, metaclass=ModelBase){
    objects = ModelManager()
    ...
}
"""
