import json
from typing import TYPE_CHECKING, TypeVar, Callable, Any

if TYPE_CHECKING:
    from .spec import Skippable


T = TypeVar('T')


def convert_skippable(
        convert: Callable[
            [
                'Skippable[Any]'
            ],
            T
        ],
) -> Callable[
    [
        'Skippable[Any]'
    ],
    'Skippable[T]'
]:
    def convert_if_not_skip(value: 'Skippable[Any]') -> 'Skippable[T]':
        from .spec import SKIP
        if value is SKIP:
            return SKIP
        else:
            return convert(value)

    return convert_if_not_skip


class LazyString:
    NOTHING = object()

    def __init__(self, callback):
        self.callback = callback
        self._result = self.NOTHING

    @property
    def result(self):
        if self._result is self.NOTHING:
            self._result = self.callback()
        return self._result

    def __str__(self):
        return self.result


class LazyPretty(LazyString):
    def __str__(self):
        return '\n' + pretty_json(self.result)


class Pretty:
    def __init__(self, obj):
        self.obj = obj

    def __str__(self):
        return '\n' + pretty_json(self.obj)


def pretty_json(obj):
    return json.dumps(
        obj,
        indent=2,
        default=lambda o: repr(o),
    )
