import enum
import logging
import posixpath
from functools import partial
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
    cast,
    Iterable,
    Generic,
    ClassVar,
    Tuple,
)

import attr

from openapilib.base import Base, MayBeReferenced
from openapilib.helpers import convert_skippable
from openapilib.sentinel import Sentinel

builtin_type = type

_log = logging.getLogger(__name__)

T_co = TypeVar('T_co', covariant=True)
T = TypeVar('T')
KT = TypeVar('KT')
VT = TypeVar('VT')

SchemaSimpleSourceType = Union[
    Type[str],
    Type[int],
    Type[float],
    Type[bool],
    Type[list],
    Type[dict],
]

SchemaTypingSourceType = Union[
    GenericMeta
    # Type[List],
    # Type[type(ClassVar)],
    # Type[Dict],
    # Type[Union]
]
SchemaSourceType = Union[
    SchemaTypingSourceType,
    SchemaSimpleSourceType,
    Dict[str, 'SchemaSourceType'],
    Any
]
SchemaFallbackHandlerType = Callable[
    [
        SchemaSourceType,
        Dict[str, Any],  # additional kwargs passed to Schema.from_type
    ],
    Optional['Schema']
]

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
    """
    https://github.com/OAI/OpenAPI-Specification/blob/master/versions/3.0.0.md#parameter-locations
    """
    QUERY = 'query'
    HEADER = 'header'
    PATH = 'path'
    COOKIE = 'cookie'


class StringFormat(enum.Enum):
    """
    http://json-schema.org/latest/json-schema-validation.html#rfc.section.8.3
    """
    EMAIL = 'email'
    IPV4 = 'ipv4'
    IPV6 = 'ipv6'
    DATETIME = 'date-time'
    HOSTNAME = 'hostname'
    URI = 'uri'
    URI_REFERENCE = 'uri-reference'
    URI_TEMPLATE = 'uri-template'
    JSON_POINTER = 'json-pointer'


def enum_to_string(member: enum.Enum):
    return member.value


def attr_skippable(**kwargs) -> Skippable:
    kwargs.setdefault('default', SKIP)
    return attr.ib(**kwargs)


def validate_required(
        instance,
        attribute: attr.Attribute,
        value,
):
    if value is REQUIRED:
        raise ValueError(
            'Missing required attribute: {attribute_name} for type '
            '{type}.'.format(
                attribute_name=attribute.name,
                type=type(instance)
            )
        )


ValidatorType = Callable[[Base, attr.Attribute, Any], None]


def attr_required(**kwargs):
    kwargs.setdefault('default', REQUIRED)
    validator: Union[
        ValidatorType,
        List[ValidatorType]
    ] = kwargs.get('validator', [])
    if not isinstance(validator, list):
        if not callable(validator):
            raise TypeError(
                'validator is not callable: {validator!r}'.format(
                    validator=validator
                )
            )

        validator = [validator]

    validator = [validate_required] + validator

    kwargs['validator'] = validator


    kwargs.setdefault('validator', [])
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

    def _validate_responses(self, attribute, value):
        assert isinstance(value, dict)
        for k, v in value.items():
            assert isinstance(k, str)
            assert isinstance(v, Response)


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


class SchemaHelperError(Exception):
    pass


class SchemaHelperUnhandled(Exception):
    """
    Raised by Schema.from_type methods if they do not handle the provided
    source.
    """
    pass


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
    _type: str = attr_skippable()
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
    additional_properties: Dict[str, 'Schema'] = attr_skippable()
    required: Skippable[Iterable[str]] = attr_skippable(
        convert=convert_skippable(set)
    )
    read_only: Skippable[bool] = attr_skippable()
    write_only: Skippable[bool] = attr_skippable()
    example: Skippable[Any] = attr_skippable()

    @classmethod
    def from_type(
            cls,
            source: SchemaSourceType,
            fallback_handler: SchemaFallbackHandlerType=None,
            **kwargs
    ) -> 'Schema':
        if isinstance(source, (Schema, Reference)):
            # Allow a pre-made Schema/Reference to be passed in directly
            return source

        HandlerType = Callable[[SchemaSourceType], Schema]

        handlers: List[
            Union[
                HandlerType,
                Tuple[HandlerType, bool]
            ]
        ] = [
            cls.from_type_hint,
            cls.from_builtin_simple_type,
            (
                cls.from_properties,
                isinstance(source, dict),
            ),
            (
                cls.from_user_type,
                # Restrict the set of matched classes by only handling classes
                # without base classes as "user type" classes
                isinstance(source, type) and not source.__bases__,
            ),
        ]

        for handler in handlers:
            if isinstance(handler, tuple):
                handler, is_enabled = handler
                if not is_enabled:
                    continue

            try:
                return handler(
                    source,
                    fallback_handler=fallback_handler,
                    **kwargs
                )
            except SchemaHelperUnhandled as exc:
                _log.debug('%s raised %r', handler, exc)
            except SchemaHelperError as exc:
                raise exc
            except Exception as exc:
                raise SchemaHelperError(
                    'Could not create schema from {source!r}'.format(
                        source=source
                    )
                ) from exc

        if fallback_handler is not None:
            schema = fallback_handler(
                source,
                kwargs
            )
            if schema is not None:
                return schema

        raise SchemaHelperError(
            'Can not create schema from type: {source!r}'.format(
                source=source
            )
        )

    @classmethod
    def from_user_type(
            cls,
            user_type: type,
            fallback_handler: SchemaFallbackHandlerType=None,
            **kwargs
    ) -> 'Schema':
        """
        Create a Schema from a user-defined class object.

        Example:

        >>> class Book:
        >>>     name = str
        >>>     pages = int
        >>> print(Schema.from_user_type(Book))
        {
          "properties": {
            "name": {
              "type": "string"
            },
            "pages": {
              "type": "integer",
              "format": "int64"
            }
          }
        }

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
            properties: Dict,
            fallback_handler: SchemaFallbackHandlerType=None,
            **kwargs
    ):
        """
        Create a ``Schema(type='object')`` from a mapping of
        ``property_name: property_type``.

        Example:

        >>> props = {'name': str, 'age': int, 'favourite_numbers': List[int]}
        >>> schema = Schema.from_properties(props, title='Pet')
        >>> print(schema)
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
        try:
            return cls(
                type='object',
                properties={
                    key: Schema.from_type(
                        value,
                        fallback_handler=fallback_handler)
                    for key, value in properties.items()
                },
                **kwargs
            )
        except SchemaHelperError as exc:
            raise SchemaHelperError(
                'Exception when creating schema from: {properties}'.format(
                    properties=properties
                )
            ) from exc

    @classmethod
    def from_type_hint(
            cls,
            hint: SchemaTypingSourceType,
            fallback_handler: SchemaFallbackHandlerType=None,
            **kwargs,
    ) -> Skippable['Schema']:
        """
        Create a Schema from a :mod:`typing` type hint.

        >>> # from typing import List
        >>> schema = Schema.from_type_hint(List[int])
        >>> print(schema)
        {
          "type": "array",
          "items": {
            "type": "integer",
            "format": "int64"
          }
        }

        """
        if isinstance(hint, type(ClassVar)):
            return cls.from_type(
                hint.__type__,
                fallback_handler=fallback_handler,
                **kwargs
            )

        if isinstance(hint, type(Any)):
            return cls()

        generic_types = (
            type(List),
            type(Dict),
            type(Union),
        )

        if not isinstance(hint, generic_types):
            raise SchemaHelperUnhandled(
                '{hint} is not a type hint.'.format(hint=hint)
            )

        origin = getattr(hint, '__origin__', hint)

        hint_arg_types: List[Schema] = []

        if hasattr(hint, '__args__'):
            try:
                hint_arg_types = [
                    Schema.from_type(
                        arg,
                        fallback_handler=fallback_handler
                    )
                    for arg in hint.__args__
                ]
            except SchemaHelperError as exc:
                raise SchemaHelperError(
                    'Could not create schemas for type '
                    'hint\'s argument types. Hint: {hint}'.format(
                        hint=hint
                    )
                ) from exc

        # We're dealing with a typing.* object
        if origin is List:
            items = SKIP
            if hint_arg_types:
                items = hint_arg_types[0]

            return cls(
                type='array',
                items=items,
                **kwargs,
            )

        if origin is Union:
            if hint_arg_types:
                return cls(
                    any_of=hint_arg_types,
                    fallback_handler=fallback_handler,
                    **kwargs
                )
            else:
                return cls()

        if origin is Dict:
            value_schema = SKIP

            if len(hint_arg_types) >= 2:
                value_schema = hint_arg_types[1]

            return cls(
                type='object',
                additional_properties=value_schema,
                **kwargs,
            )

        if origin is ClassVar:
            if hint_arg_types:
                return cls.from_type(
                    hint_arg_types[0],
                    fallback_handler=fallback_handler,
                    **kwargs
                )

        raise SchemaHelperError(
            'Unsupported type hint: {hint}'.format(hint=hint)
        )

    @classmethod
    def from_builtin_simple_type(
            cls,
            source: SchemaSimpleSourceType,
            fallback_handler: SchemaFallbackHandlerType=None,
            **kwargs,
    ) -> Skippable['Schema']:
        """
        Create a Schema from a builtin type, such as:

        -   :class:`int`
        -   :class:`str`
        -   :class:`list`
        -   :class:`tuple`
        -   :class:`dict`
        -   :class:`float`
        -   :class:`bool`

        Examples
        --------

        >>> print(Schema.from_builtin_simple_type(int))
        {
          "type": "integer",
          "format": "int64"
        }
        """
        if not isinstance(source, type):
            _log.debug('%r is not a simple type.', source)
            raise SchemaHelperUnhandled(
                '{source!r} is not a type'.format(source=source)
            )

        for base, params in SCHEMA_SIMPLE_TYPE_ARGS.items():
            if issubclass(source, base):
                return cls(
                    **params,
                    **kwargs,
                )

        raise SchemaHelperUnhandled(
            '{type} is not a subclass of any of {simple_types}'.format(
                type=type(source),
                simple_types=SCHEMA_SIMPLE_TYPE_ARGS.keys()
            )
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


class ComponentType(Generic[T_co], extra=MayBeReferenced):
    __slots__ = ()


T_Component = ComponentType[T_co]
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
            'Unhandled type: {spec}'.format(type=type(spec))
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
