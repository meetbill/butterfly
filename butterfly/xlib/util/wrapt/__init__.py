# coding=utf8
"""
# File Name: __init__.py
# Description:
    代理对象: ObjectProxy, CallableObjectProxy, WeakFunctionProxy
    包装对象: FunctionWrapper, BoundFunctionWrapper
    装饰器工厂函数: function_wrapper, decorator
    辅助测试的工厂函数: wrap_function_wrapper, patch_function_wrapper, transient_function_wrapper
    猴子补丁相关: .importer
    synchronized: java synchronized 的 Python 实现
"""
__version_info = ('1', '11', '2')
__version__ = '.'.join(__version_info)

from .wrappers import (ObjectProxy, CallableObjectProxy, FunctionWrapper,
        BoundFunctionWrapper, WeakFunctionProxy, PartialCallableObjectProxy,
        resolve_path, apply_patch, wrap_object, wrap_object_attribute,
        function_wrapper, wrap_function_wrapper, patch_function_wrapper,
        transient_function_wrapper)

from .decorators import (adapter_factory, AdapterFactory, decorator,
        synchronized)

from .importer import (register_post_import_hook, when_imported,
        notify_module_loaded, discover_post_import_hooks)

from inspect import getcallargs
