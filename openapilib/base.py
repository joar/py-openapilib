import logging
from typing import Optional

import attr

_log = logging.getLogger(__name__)


class Base:
    """
    Root type of OpenAPI Specification Object types.
    """
    __slots__ = ()

    @classmethod
    def fields_by_name(cls):
        return {field.name: field for field in attr.fields(cls)}

    def to_dict(self):
        from .serialization import spec_to_dict
        return spec_to_dict(self)

    def __str__(self):
        from .serialization import serialize
        import json
        return json.dumps(
            serialize(self),
            indent=2
        )


@attr.s(slots=True)
class MayBeReferenced:
    ref_name: Optional[str] = attr.ib(
        default=None,
        metadata=dict(
            non_spec=True
        )
    )

