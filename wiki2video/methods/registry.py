from typing import Type, Dict
from .base import BaseMethod

# 全局注册表，key=方法名，value=类
_METHOD_REGISTRY: Dict[str, Type[BaseMethod]] = {}


def register_method(cls: Type[BaseMethod]) -> Type[BaseMethod]:
    """
    装饰器：注册一个方法类到全局字典
    用法:
        @register_method
        class MyMethod(BaseMethod): ...
    """
    name = getattr(cls, "NAME", cls.__name__)
    if name in _METHOD_REGISTRY:
        raise ValueError(f"Method '{name}' already registered.")
    _METHOD_REGISTRY[name] = cls
    return cls


def get_method(name: str) -> Type[BaseMethod]:
    """
    根据名字获取类；不存在则报错
    """
    if name not in _METHOD_REGISTRY:
        raise KeyError(f"Method '{name}' not found. Registered: {list(_METHOD_REGISTRY)}")
    return _METHOD_REGISTRY[name]


def create_method(name: str, **kwargs) -> BaseMethod:
    """
    工厂方法：直接创建实例
    """
    cls = get_method(name)
    return cls(**kwargs)


def list_methods() -> Dict[str, Type[BaseMethod]]:
    """
    返回当前所有已注册的方法
    """
    return dict(_METHOD_REGISTRY)
