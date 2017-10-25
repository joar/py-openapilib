"""
OpenAPI 3 Specification Object Model

:mod:`openapilib.spec` contains classes, each class representing an object in
the
`OpenAPI 3 Specification
<https://github.com/OAI/OpenAPI-Specification/blob/master/versions/3.0.0.md>`_

Raw example:

>>> from openapilib import serialize_spec, spec
>>> api_spec = spec.OpenAPI(
...     info=spec.Info(
...         title='Foo',
...     ),
...     paths={
...         '/': spec.PathItem(
...             get=spec.Operation(
...                 responses={
...                     '200': spec.Response(
...                         description='Your favourite pet',
...                         content={
...                             'application/json': spec.MediaType(
...                                 schema=spec.Schema(
...                                     ref_name='Pet',
...                                     title='Pet',
...                                     type='object',
...                                     properties={
...                                         'name': spec.Schema.from_type(str),
...                                         'age': spec.Schema.from_type(int),
...                                     }
...                                 )
...                             )
...                         }
...                     )
...                 }
...             )
...         )
...     }
... )
>>> import json
>>> print(json.dumps(serialize_spec(api_spec), indent=2))
{
  "openapi": "3.0.0",
  "info": {
    "title": "Foo",
    "version": "0.0.1-dev"
  },
  "paths": {
    "/": {
      "get": {
        "responses": {
          "200": {
            "description": "Your favourite pet",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Pet"
                }
              }
            }
          }
        }
      }
    }
  },
  "components": {
    "schemas": {
      "Pet": {
        "title": "Pet",
        "type": "object",
        "properties": {
          "name": {
            "type": "string"
          },
          "age": {
            "type": "integer",
            "format": "int64"
          }
        }
      }
    }
  }
}
"""
import enum
import logging
import posixpath
from typing import (
    Dict,
    Any,
    List,
    Union,
    Optional,
    GenericMeta,
    Callable,
    Type,
    TypeVar,
    Set,
)
from unittest.mock import sentinel

import attr

from openapilib.base import Base, MayBeReferenced
from openapilib.sentinel import Sentinel

builtin_type = type

_log = logging.getLogger(__name__)

T = TypeVar('T')
KT = TypeVar('KT')
VT = TypeVar('VT')

T_SchemaFromSimple = Union[
    Type[str],
    Type[int],
    Type[float],
    Type[bool],
    Type[list],
    Type[dict],
]
T_SchemaFromTyping = GenericMeta
T_SchemaFrom = Union[
    T_SchemaFromSimple,
    T_SchemaFromTyping,
    Dict,
    Any  # in case a fallback handler is specified
]
T_SchemaFallbackHandler = Callable[
    [
        T_SchemaFrom,
        Dict[str, Any],  # additional kwargs passed to Schema.from_type
    ],
    'Schema'
]

#
# class DefaultValue(enum.Enum):
#     #: Used as Object attribute default value to mark an attribute as skippable,
#     #: while still allowing "None" to be distinct from "unspecified".
#     #: The end result is that if the user does not specify an attribute value,
#     #: the property is not included in the output. If the user specifies "None"
#     #: as the attribute value, it will be included as "null".
#     SKIP = 'SKIP'
#
#     #: Used as Object attribute default value to mark an object as required.
#     #: When # used together with the :any:`attr_required()` helper, the value
#     #: "None" for an attribute will be allowed, omitting the property will
#     #: raise an error.
#     REQUIRED = 'REQUIRED'
#
#     def __repr__(self):
#         return f'{self.name}'
#
#
# SKIP = DefaultValue.SKIP
# REQUIRED = DefaultValue.REQUIRED
#
# Skippable = Union[DefaultValue, T]

SKIP = Sentinel('SKIP', """
Used as Object attribute default value to mark an attribute as skippable,
while still allowing "None" to be distinct from "unspecified".
The end result is that if the user does not specify an attribute value,
the property is not included in the output. If the user specifies "None"
as the attribute value, it will be included as "null".
""")

REQUIRED = Sentinel('REQUIRED', """
Used as Object attribute default value to mark an object as required. When
used together with the :any:`attr_required()` helper, the value "None" for
an attribute will be allowed, omitting the property will raise an error.
""")

Skippable = Union[Sentinel, T]


class ParameterLocation(enum.Enum):
    QUERY = 'query'
    HEADER = 'header'
    PATH = 'path'
    COOKIE = 'cookie'


def enum_to_string(member: enum.Enum):
    return member.value


def attr_skippable(**kwargs) -> Skippable:
    kwargs.setdefault('default', SKIP)
    return attr.ib(**kwargs)


def validate_required(instance, attribute: attr.Attribute, value):
    if value is REQUIRED:
        raise ValueError(
            f'Missing required attribute: {attribute.name} for type '
            f'{instance.__class__.__name__}.'
        )


def attr_required(**kwargs):
    kwargs.setdefault('default', REQUIRED)
    kwargs.setdefault('validator', []).append(validate_required)
    return attr.ib(**kwargs)


# Specification
# ------------------------------------------------------------------------------


@attr.s(slots=True)
class Info(Base):
    """
    https://github.com/OAI/OpenAPI-Specification/blob/master/versions/3.0.0.md#infoObject
    """
    title: str = attr_required()
    description: str = attr_skippable()
    terms_of_service: str = attr_skippable()
    contact: 'Contact' = attr_skippable()
    license: 'License' = attr_skippable()
    version: str = attr.ib(
        default='0.0.1-dev',
        validator=attr.validators.instance_of(str)
    )


@attr.s(slots=True)
class Contact(Base):
    """
    https://github.com/OAI/OpenAPI-Specification/blob/master/versions/3.0.0.md#contactObject
    """
    name: str = attr_skippable()
    url: str = attr_skippable()
    email: str = attr_skippable()


@attr.s(slots=True)
class License(Base):
    """
    https://github.com/OAI/OpenAPI-Specification/blob/master/versions/3.0.0.md#licenseObject
    """
    name: str = attr_skippable()
    url: str = attr_skippable()


@attr.s(slots=True)
class OpenAPI(Base):
    """
    https://github.com/OAI/OpenAPI-Specification/blob/master/versions/3.0.0.md#openapi-object
    """
    openapi: str = attr.ib(
        default='3.0.0',
        validator=attr.validators.instance_of(str)
    )
    info: 'Info' = attr_required()
    servers: List['Server'] = attr_skippable()
    paths: Dict[str, 'PathItem'] = attr_required()
    components: 'Components' = attr_skippable()
    security: 'SecurityRequirement' = attr_skippable()
    tags: List['Tag'] = attr_skippable()
    external_docs: 'ExternalDocs' = attr_skippable()


@attr.s(slots=True)
class PathItem(Base):
    """
    https://github.com/OAI/OpenAPI-Specification/blob/master/versions/3.0.0.md#pathItemObject
    """
    summary: Skippable[str] = attr_skippable()
    description: Skippable[str] = attr_skippable()

    # HTTP Methods
    get: Skippable['Operation'] = attr_skippable()
    put: Skippable['Operation'] = attr_skippable()
    post: Skippable['Operation'] = attr_skippable()
    delete: Skippable['Operation'] = attr_skippable()
    options: Skippable['Operation'] = attr_skippable()
    head: Skippable['Operation'] = attr_skippable()
    patch: Skippable['Operation'] = attr_skippable()
    trace: Skippable['Operation'] = attr_skippable()

    parameters: Skippable[List['Parameter']] = attr_skippable()


@attr.s(slots=True)
class Operation(Base):
    """
    https://github.com/OAI/OpenAPI-Specification/blob/master/versions/3.0.0.md#operation-object
    """
    tags: Skippable[Set[str]] = attr_skippable()
    summary: str = attr_skippable()
    description: str = attr_skippable()

    responses: Dict[str, 'Response'] = attr_required()

    operation_id: str = attr_skippable()
    parameters: List['Parameter'] = attr_skippable()
    request_body: 'RequestBody' = attr_skippable()

    def add_tags(self, *tags):
        if self.tags is SKIP:
            self.tags = set()

        self.tags |= set(tags)


@attr.s(slots=True)
class Parameter(Base, MayBeReferenced):
    """
    https://github.com/OAI/OpenAPI-Specification/blob/master/versions/3.0.0.md#parameter-object
    """
    name: str = attr_required()
    in_: str = attr_required(
        default=ParameterLocation.QUERY,
        convert=enum_to_string,
    )
    description: str = attr_skippable()
    required: Skippable[bool] = attr_skippable()
    deprecated: Skippable[bool] = attr_skippable()
    allow_empty_value: Skippable[bool] = attr_skippable()
    schema: Skippable['Schema'] = attr_skippable()


@attr.s(slots=True)
class RequestBody(Base, MayBeReferenced):
    """
    https://github.com/OAI/OpenAPI-Specification/blob/master/versions/3.0.0.md#request-body-object
    """
    content: Dict[str, 'MediaType'] = attr_required()
    description: str = attr_skippable()


@attr.s(slots=True)
class Response(Base, MayBeReferenced):
    """
    https://github.com/OAI/OpenAPI-Specification/blob/master/versions/3.0.0.md#response-object
    """
    description: str = attr_required()
    content: Dict[str, 'MediaType'] = attr_skippable()


@attr.s(slots=True)
class MediaType(Base):
    """
    https://github.com/OAI/OpenAPI-Specification/blob/master/versions/3.0.0.md#media-type-object
    """
    schema: Union['Schema', 'Reference'] = attr_required()
    example: Any = attr_skippable()


SCHEMA_SIMPLE_TYPE_ARGS = {
    str: dict(
        type='string',
    ),
    int: dict(
        type='integer',
        format='int64',
    ),
    float: dict(
        type='number',
        format='double',
    ),
    bool: dict(
        type='boolean',
    ),
    list: dict(
        type='array'
    ),
    tuple: dict(
        type='array'
    )
}


@attr.s(slots=True)
class Schema(Base, MayBeReferenced):
    """
    https://github.com/OAI/OpenAPI-Specification/blob/master/versions/3.0.0.md#schema-object
    """

    # Metadata keywords
    title: str = attr_skippable()
    description: str = attr_skippable()

    default: Any = attr_skippable()
    examples: List[Any] = attr_skippable()
    definitions: Dict[str, 'Schema'] = attr_skippable()

    # Validation keywords
    type: str = attr_skippable()
    multiple_of: int = attr_skippable()

    maximum: int = attr_skippable()
    exclusive_maximum: int = attr_skippable()
    minimum: int = attr_skippable()
    exclusive_minimum: int = attr_skippable()
    max_length: int = attr_skippable()
    min_length: int = attr_skippable()
    pattern: str = attr_skippable()
    items: 'Schema' = attr_skippable()
    additional_items: 'Schema' = attr_skippable()
    format: str = attr_skippable()
    # (Missing some validation keywords)

    all_of: List['Schema'] = attr_skippable()
    one_of: List['Schema'] = attr_skippable()
    not_: 'Schema' = attr_skippable()
    any_of: List['Schema'] = attr_skippable()
    properties: Dict[str, 'Schema'] = attr_skippable()

    @classmethod
    def from_type(
            cls,
            type_: T_SchemaFrom,
            fallback_handler: T_SchemaFallbackHandler=None,
            **kwargs,
    ):
        from_hint = cls.from_type_hint(
            type_,
            fallback_handler=fallback_handler,
            **kwargs
        )
        if from_hint is not None:
            return from_hint

        simple = cls.from_builtin_simple_type(type_, **kwargs)
        if simple is not None:
            return simple

        if fallback_handler is not None:
            fallback = fallback_handler(type_, kwargs)
            if fallback is not None:
                return fallback

        raise TypeError(
            f'Can not create schema from type: {type_!r}'
        )

    @classmethod
    def from_user_type(
            cls,
            user_type: Type,
            fallback_handler: T_SchemaFallbackHandler=None,
            **kwargs
    ) -> 'Schema':
        """
        Create a Schema from a user-defined class object.

        Example:

        >>> class Book:
        ...     name = str
        ...     pages = int
        >>> Schema.from_user_type(Book)
        """
        return cls.from_properties(
            properties={
                key: value
                for key, value in user_type.__dict__.items()
                if not key.startswith('_')
            },
            fallback_handler=fallback_handler,
            **kwargs,
        )

    @classmethod
    def from_properties(
            cls,
            properties: Dict[str, T_SchemaFrom],
            fallback_handler: T_SchemaFallbackHandler=None,
            **kwargs,
    ):
        """
        Create a ``Schema(type='object')`` from a mapping of
         ``property_name: property_type``.

        Example:

        >>> from openapilib.serialization import serialize
        >>> from openapilib.spec import Schema
        >>> props = {'name': str, 'age': int, 'favourite_numbers': List[int]}
        >>> schema = Schema.from_properties(props, title='Pet')
        >>> import json
        >>> print(json.dumps(serialize(schema), indent=2))
        {
          "title": "Pet",
          "properties": {
            "name": {
              "type": "string"
            },
            "age": {
              "type": "integer",
              "format": "int64"
            },
            "favourite_numbers": {
              "type": "array",
              "items": {
                "type": "integer",
                "format": "int64"
              }
            }
          }
        }

        """
        return cls(
            properties={
                key: Schema.from_type(
                    value,
                    fallback_handler=fallback_handler)
                for key, value in properties.items()
            },
            **kwargs
        )

    @classmethod
    def from_type_hint(
            cls,
            type_: T_SchemaFromTyping,
            fallback_handler: T_SchemaFallbackHandler=None,
            **kwargs,
    ) -> 'Schema':
        # import locally, since we're using
        # "from typing import .."
        # outside this scope, and my editor get confused when trying to help
        # me import.
        import typing

        t = type_  # convenient

        if isinstance(t, GenericMeta):
            # We're dealing with a typing.* object
            if t.__origin__ is typing.List:
                items = SKIP
                if t.__args__:
                    items = cls.from_type(
                        t.__args__[0],
                        fallback_handler=fallback_handler,
                    )

                return cls(
                    type='array',
                    items=items,
                    **kwargs,
                )

            if t.__origin__ is typing.Dict:
                value_schema = SKIP
                if t.__args__:
                    value_schema = cls.from_type(
                        t.__args__[1],
                        fallback_handler=fallback_handler,
                    )

                return cls(
                    type='object',
                    properties={},
                    additional_properties=value_schema,
                    **kwargs,
                )

    @classmethod
    def from_builtin_simple_type(
            cls,
            type_: T_SchemaFromSimple,
            fallback_handler: T_SchemaFallbackHandler=None,
            **kwargs,
    ) -> Optional['Schema']:
        if not isinstance(type_, type):
            _log.debug('%r is not a simple type.', type_)
            return

        for base, params in SCHEMA_SIMPLE_TYPE_ARGS.items():
            if issubclass(type_, base):
                return cls(
                    **params,
                    **kwargs,
                )


@attr.s(slots=True)
class Reference(Base):
    ref: str = attr_required(
        metadata=dict(
            spec_name='$ref'
        )
    )


COMPONENT_TYPES = {
    Schema: 'schemas',
    Response: 'responses',
    Parameter: 'parameters',
    RequestBody: 'request_bodies',
}

T_Component = TypeVar('T_Component', bound=MayBeReferenced)
T_Registry = Dict[str, Union[T_Component, 'Reference']]


def attr_registry(**kwargs):
    return attr_skippable(**kwargs)


@attr.s(slots=True)
class Components(Base):
    """
    https://github.com/OAI/OpenAPI-Specification/blob/master/versions/3.0.0.md#componentsObject
    """

    schemas: T_Registry['Schema'] = attr_registry()
    responses: T_Registry['Response'] = attr_registry()
    parameters: T_Registry['Parameter'] = attr_registry()
    examples: T_Registry['Example'] = attr_registry()
    request_bodies: T_Registry['RequestBody'] = attr_registry()
    headers: T_Registry['Header'] = attr_registry()
    security_schemas: T_Registry['SecuritySchema'] = attr_registry()
    links: T_Registry['Link'] = attr_registry()
    callbacks: T_Registry['Callback'] = attr_registry()

    def get_registry_for_spec(
            self,
            spec: T_Component
    ) -> Optional[T_Registry[T_Component]]:
        registry: Skippable[T_Registry[T_Component]] = getattr(
            self,
            self.component_type_for_spec(spec)
        )
        if registry is not SKIP:
            return registry

        _log.debug('Registry for type %s does not exist', type(spec))
        return None

    def create_registry_for_spec(
            self,
            spec: T_Component
    ) -> T_Registry[T_Component]:
        registry = self.get_registry_for_spec(spec)
        if registry is not None:
            return registry

        registry: T_Registry[T_Component] = {}
        setattr(self, self.component_type_for_spec(spec), registry)
        return registry

    @staticmethod
    def component_type_for_spec(spec: T_Component):
        for base, component_type in COMPONENT_TYPES.items():
            if isinstance(spec, base):
                return component_type

        raise TypeError(
            f'Unhandled type: {type(spec)}'
        )

    def get_ref_str(self, spec: T_Component) -> str:
        return posixpath.join(
            '#/components',
            self.component_type_for_spec(spec),
            spec.ref_name
        )

    def get_ref(self, spec: T_Component) -> 'Reference':
        return Reference(
            ref=self.get_ref_str(spec)
        )

    def get_stored(self, spec: T_Component) -> Optional[T_Component]:
        registry = self.get_registry_for_spec(spec)
        if registry is None:
            return
        return registry.get(spec.ref_name)

    def exists(self, spec: T_Component) -> bool:
        return self.get_stored(spec) is not None

    def store(self, spec: T_Component) -> 'Reference':
        registry = self.create_registry_for_spec(spec)
        registry[spec.ref_name] = spec
        return self.get_ref(spec)

