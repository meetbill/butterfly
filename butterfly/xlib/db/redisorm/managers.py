# -*- coding: utf-8 -*-
import pickle
from xlib.db import redis
from .utils import (timestamp_to_datetime, datetime_to_timestamp, random_string,
                    utcnow, random_true)
from .compat import xrange, b, u


# --- Systems related ----------------------------------------------

SYSTEMS = {
    'default': redis.Redis(host='localhost', port=6379)
}


def setup_redis(name, host=None, port=None, **kw):
    """
    Setup a redis system.

    :param name: The name of the system
    :param host: The host of the redis installation
    :param port: The port of the redis installation
    :param redis: It's a special keyword. If you don't want to use standard
                  :class:`redis.Redis` and have your own pre-configured
                  object, feel free to pass it as a "redis" parameter
    :param \*\*kw: Any additional keyword arguments to be passed to
                  :class:`redis.Redis`.

    Example::

        setup_redis('stats_redis', 'localhost', 6380)
        mark_event('active', 1, system='stats_redis')
    """
    redis_instance = kw.pop('redis', None)
    if not redis_instance:
        redis_instance = redis.Redis(host=host, port=port, **kw)
    SYSTEMS[name] = redis_instance


def get_redis(system='default'):
    """
    Get a redis-py client instance with entry `system`.

    :param :system The name of the system, extra systems can be setup via `setup_redis`
    """
    return SYSTEMS[system]


class ModelManager(object):
    # metaclass ModelBase ensures this object has "model_name", "id_length"
    # and "model" attribute,
    # def __init__(self):
    #    self.exclude_attrs = set(exclude_attrs or [])

    def _key(self, key, *args, **kwargs):
        key = u(key)
        prefix = 'redisorm'
        model_name = self.model_name
        template = '{0}:{1}:{2}'.format(prefix, model_name, key)

        if args or kwargs:
            template = template.format(*args, **kwargs)
        return b(template)

    def set_system(self, system):
        """
        setup default system for all models of the manager
        """
        self.system = system

    def get_system(self, arg):
        """
        get system to use for operation. If arg is not None, use it, otherwise
        use default system, defined in manager
        """
        return arg or self.system


    def get(self, id, system=None):
        system = self.get_system(system)
        id = u(id)
        # There is a 1% chance to clean up expire data
        if random_true(0.01):
            self.expire()
        key = self._key('object:{0}', id)
        value = get_redis(system).get(key)
        instance = 0
        if value:
            # check key expire
            expire_key = self._key('object:{0}:expire', id)
            expire_value = get_redis(system).get(expire_key)
            expire = timestamp_to_datetime(expire_value)
            if expire and expire < utcnow():
                return None
            attrs = pickle.loads(value)
            instance = self.model(id=id, expire=expire, **attrs)
        if instance:
            tags_key = self._key('object:{0}:tags', u(id))
            tags = get_redis(system).smembers(u(tags_key)) or []
            instance.tags = [u(tag) for tag in tags]
        return instance

    def create(self, *args, **attrs):
        """
        create 记录
        """
        model = self.model(*args, **attrs)
        # check unique_tag
        if model.unique_tag:
            keys = []
            key = self._key('tags:{0}', model.unique_tag)
            keys.append(u(key))
            ids = get_redis("default").sinter(*keys)
            if ids:
                for instance_id in ids:
                    instance = self.get(instance_id)
                    if instance:
                        self.delete_instance(instance)
        self._save_instance(model)
        return model

    def _save_instance(self, instance, system=None):
        """
        write data to redis
        """
        system = self.get_system(system)
        if instance.id is None:
            instance.id = self._reserve_random_id(system=system)

        # object itself
        value = pickle.dumps(instance.attrs)

        pipe = get_redis(system).pipeline(transaction=False)
        pipe.sadd(self._key('__all__'), instance.id)
        pipe.set(self._key('object:{0}', instance.id), value)
        if instance.expire:
            expire_ts = datetime_to_timestamp(instance.expire)
            # python redis cli 3.0.x 后 zadd 需要使用 mapping = {member: score, }
            mapping = {instance.id: expire_ts}
            pipe.set(self._key('object:{0}:expire', instance.id), expire_ts)
            pipe.zadd(self._key('__expire__'), mapping)
        pipe.execute()
        if not instance.tags:
            return
        pipe = get_redis(system).pipeline(transaction=False)
        tags_key = self._key('object:{0}:tags', instance.id)
        pipe.sadd(tags_key, *instance.tags)
        for tag in instance.tags:
            key = self._key('tags:{0}', tag)
            pipe.sadd(key, instance.id)
        for tag_to_rm in set(instance._saved_tags) - set(instance.tags):
            key = self._key('tags:{0}', tag_to_rm)
            pipe.srem(key, instance.id)
        pipe.execute()
        instance._saved_tags = instance.tags

    def delete_instance(self, instance, system=None):
        """
        # we have to remove instance from all tags before removing the
        # object itself
        """
        system = self.get_system(system)
        tags_keys = self._key('object:{0}:tags', u(instance.id))
        tags = get_redis(system).smembers(tags_keys)
        pipe = get_redis(system).pipeline(transaction=False)
        for tag in tags:
            key = self._key('tags:{0}', u(tag))
            pipe.srem(key, instance.id)
        self._delete_instance_by_id(instance.id, pipe=pipe, apply=False, system=system)
        pipe.execute()

    def _delete_instance_by_id(self, instance_id, pipe=None, apply=True, system=None):
        """
        删除记录级别的如下key:
        > * (set) redisorm:{model_name}:object:{instance_id}
        > * (set) redisorm:{model_name}:object:{instance_id}:tags
        > * (string) redisorm:{model_name}:object:{instance_id}:expire 设置 instance 过期时才会有此 key

        从 model 中删除此 instance_id
        > * (set) redisorm:{model_name}:__all__
        > * (zset) redisorm:{model_name}:__expire__
        Args:
            instance_id:isinstance
            pipe:pipeline
            apply:
            system: redis
        Returns:
        """
        system = self.get_system(system)
        instance_id = u(instance_id)
        all_key = self._key('__all__')
        expire_key = self._key('__expire__')
        key = self._key('object:{0}', instance_id)
        ###############################################################
        # extra_keys
        # tags key: 记录此 instance 的所有 tags
        # (set) redisorm:{model_name}:object:{instance_id}:tags
        # 过期时间 key: 记录此 instance 的过期时间，当设置过期时，才会设置此 key
        # (string) redisorm:{model_name}:object:{instance_id}:expire
        ###############################################################
        extra_keys = [self._key('object:{0}:tags', instance_id), self._key('object:{0}:expire', instance_id) ]
        if not pipe:
            pipe = get_redis(system).pipeline(transaction=False)

        # 从 redisorm:{model_name}:__all__ key 中删除此 instance_id
        pipe.srem(all_key, instance_id)
        # 从 redisorm:{model_name}:__expire__ key 中删除此 instance_id
        pipe.zrem(expire_key, instance_id)
        pipe.delete(key, *extra_keys)
        if apply:
            pipe.execute()

    def expire(self, system=None):
        system = self.get_system(system)
        expire_ts = datetime_to_timestamp(utcnow())
        expire_key = self._key('__expire__')
        remove_ids = get_redis(system).zrangebyscore(expire_key, 0, expire_ts)
        if remove_ids:
            pipe = get_redis(system).pipeline(transaction=False)
            for id in remove_ids:
                tags_keys = self._key('object:{0}:tags', u(id))
                tags = get_redis(system).smembers(tags_keys)
                for tag in tags:
                    key = self._key('tags:{0}', u(tag))
                    pipe.srem(key, id)
                self._delete_instance_by_id(id, pipe=pipe, apply=False, system=system)
            pipe.execute()

    def _reserve_random_id(self, max_attempts=10, system=None):
        system = self.get_system(system)
        key = self._key('__all__')
        for _ in xrange(max_attempts):
            value = random_string(self.id_length)
            ret = get_redis(system).sadd(key, value)
            if ret != 0:
                return value
        raise RuntimeError('Unable to reserve random id for model "%s"' % self.model_name)

    def all(self, system=None):
        system = self.get_system(system)
        all_key = self._key('__all__')
        ids = []
        if get_redis(system).exists(all_key):
            ids = get_redis(system).smembers(all_key)
        return ModelResultSet(self, ids, system)

    def _gen_unitque_tag(self, attrs, unique_field):
        """
        get tags(string)
        """
        unique_tag = ""
        for k, v in attrs.items():
            if k == unique_field:
                unique_tag = u'{0}:{1}'.format(u(k), u(v))
        return unique_tag

    def _attrs_to_tags(self, attrs, exclude_attrs_set=[]):
        """
        get tags(list)
        """
        tags = []
        for k, v in attrs.items():
            if k not in exclude_attrs_set:
                tags.append(u'{0}:{1}'.format(u(k), u(v)))
        return tags

    def find_ids(self, *tags, **kw):
        system = self.get_system(kw.get('system'))
        if not tags:
            return []
        keys = []
        for tag in tags:
            key = self._key('tags:{0}', tag)
            keys.append(u(key))
        return get_redis(system).sinter(*keys)

    def find(self, **attrs):
        system = self.get_system(attrs.pop('system', None))
        tags = self._attrs_to_tags(attrs)
        ids = self.find_ids(system=system, *tags)
        return ModelResultSet(self, ids, system)


class ModelResultSet(object):

    def __init__(self, manager, ids, system=None):
        self.manager = manager
        self.ids = ids
        self.system = system
        # we intentionally fill the cache only in list() method
        self._cache = None

    def __iter__(self):
        if self._cache is not None:
            for item in self._cache:
                yield item
        else:
            for id in self.ids:
                instance = self.manager.get(id, system=self.system)
                if instance:
                    yield instance

    def list(self):
        if self._cache is not None:
            return self._cache

        ret = []
        for item in self:
            ret.append(item)
        self._cache = ret
        return ret

    def count(self):
        return len(self.list())

    def __len__(self):
        return self.count()

    def __getitem__(self, item):
        return self.list()[item]
