import json
from pprint import pformat


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
        return '\n' + json.dumps(
            self.result,
            indent=2
        )


class Pretty:
    def __init__(self, obj):
        self.obj = obj

    def __str__(self):
        return pformat(self.obj)
