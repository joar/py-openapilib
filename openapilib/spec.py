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
    NewType,
    TYPE_CHECKING,
    TypeVar,
    Set,
)
from unittest.mock import sentinel

import attr
import deepdiff
import stringcase

from openapilib.logging_helpers import LazyPretty

if TYPE_CHECKING:
    from unittest.mock import _SentinelObject
    T_SKIP = NewType('T_SKIP', _SentinelObject)

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
    Any  # in case a fallback handler is specified
]
T_SchemaFallbackHandler = Callable[
    [
        T_SchemaFrom,
        Dict[str, Any],  # additional kwargs passed to Schema.from_type
    ],
    'Schema'
]

Skippable = Union['T_SKIP', T]

SKIP: 'T_SKIP' = sentinel.OPENAPI_SPEC_SKIP
REQUIRED = sentinel.OPENAPI_SPEC_REQUIRED


class ParameterLocation(enum.Enum):
    QUERY = 'query'
    HEADER = 'header'
    PATH = 'path'
    COOKIE = 'cookie'


def rename_key(key: str, a: attr.Attribute) -> str:
    if key.endswith('_'):
        assert len(key) > 1
        key = key[:-1]

    #: Name of field according to spec.
    spec_name = a.metadata.get('spec_name', stringcase.camelcase(key))
    return spec_name


def enum_to_string(member: enum.Enum):
    return member.value


def attr_skippable(**kwargs) -> Skippable:
    kwargs.setdefault('default', SKIP)
    return attr.ib(**kwargs)


def validate_required(instance, attribute: attr.Attribute, value):
    if value is REQUIRED:
        raise ValueError(
            f'Missing required value for attribute: {attribute.name}'
        )


def attr_required(**kwargs):
    kwargs.setdefault('default', REQUIRED)
    kwargs.setdefault('validator', []).append(validate_required)
    return attr.ib(**kwargs)


def attr_dict(**kwargs) -> Dict[KT, VT]:
    kwargs.setdefault('default', attr.Factory(dict))
    return attr.ib(**kwargs)


@attr.s(slots=True, frozen=True)
class SerializationContext:
    disable_referencing: bool = attr.ib(default=False)
    components: Optional['Components'] = attr.ib(
        default=attr.Factory(lambda: Components())
    )

    @classmethod
    def debug(cls):
        return SerializationContext(
            disable_referencing=True
        )


def serialize(
        value: Union['Base', List, Any],
        ctx: SerializationContext,
):
    if isinstance(value, Base):
        return serialize_spec(value, ctx=ctx)

    if isinstance(value, dict):
        return {
            serialize(k, ctx=ctx): serialize(v, ctx=ctx)
            for k, v in value.items()
        }

    if isinstance(value, (list, tuple, set)):
        return [serialize(v, ctx=ctx) for v in value]

    return value


def serialize_spec(
        spec: 'Base',
        ctx: SerializationContext,
):
    _log.debug(
        'Serializing %s, ctx.disable_referencing=%r',
        spec.__class__.__name__,
        ctx.disable_referencing
    )
    may_be_referenced = (
        isinstance(spec, MayBeReferenced) and
        spec.ref_name is not None
    )
    should_reference = (
        ctx is not None and
        not ctx.disable_referencing and
        may_be_referenced
    )

    if should_reference and False:
        # Store definition in context, return reference
        import typing
        spec = typing.cast(Components.T_Component, spec)
        _log.debug(
            'trying to reference, ref_name=%r, ctx.components=%r',
            spec.ref_name,
            ctx.components.serialize(DEBUG_CONTEXT)
        )
        return ctx.components.get_or_create(
            spec,
        ).serialize(
            ctx=ctx
        )

    if may_be_referenced:
        _log.debug(
            'not referencing. ref_name=%r, ctx=%r',
            spec.ref_name,
            ctx
        )

    fields = spec.fields_by_name()

    filtered = attr.asdict(
        spec,
        filter=filter_attributes,
        recurse=False,
    )

    serialized = {
        rename_key(key, fields[key]): serialize(
            value,
            ctx=ctx
        )
        for key, value in filtered.items()
    }
    return serialized


def filter_attributes(attribute: attr.Attribute, value):
    is_skipped = value is SKIP
    non_spec = attribute.metadata.get('non_spec')

    return (not is_skipped) and not non_spec


# Specification
# ------------------------------------------------------------------------------


class Base:
    __slots__ = ()

    @classmethod
    def fields_by_name(cls):
        return {field.name: field for field in attr.fields(cls)}

    def serialize(
            self,
            ctx: SerializationContext,
    ):
        if ctx is None:
            _log.warning(
                'No SerializationContext provided, creating ad-hoc context.',
                stack_info=True
            )
            ctx = SerializationContext(disable_referencing=True)
        return serialize_spec(
            self,
            ctx=ctx
        )


@attr.s(slots=True)
class MayBeReferenced:
    ref_name: Optional[str] = attr.ib(
        default=None,
        metadata=dict(
            non_spec=True
        )
    )


@attr.s(slots=True)
class _Described:
    description: str = attr_skippable()


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
class Components(Base):
    """
    https://github.com/OAI/OpenAPI-Specification/blob/master/versions/3.0.0.md#componentsObject
    """
    T_Component = MayBeReferenced
    Registry = Dict[str, Union[T, 'Reference']]

    schemas: Registry['Schema'] = attr_dict()
    responses: Registry['Response'] = attr_dict()
    parameters: Registry['Parameter'] = attr_dict()
    examples: Registry['Example'] = attr_dict()
    request_bodies: Registry['RequestBody'] = attr_dict()
    headers: Registry['Header'] = attr_dict()
    security_schemas: Registry['SecuritySchema'] = attr_dict()
    links: Registry['Link'] = attr_dict()
    callbacks: Registry['Callback'] = attr_dict()

    def registry_for_spec(self, spec: T_Component):
        return getattr(self, self.component_type_for_spec(spec))

    @staticmethod
    def component_type_for_spec(spec: T_Component):
        base_to_component_type = {
            Schema: 'schemas',
            Response: 'responses',
            Parameter: 'parameters',
            RequestBody: 'request_bodies',
        }

        for base, component_type in base_to_component_type.items():
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

    def get_or_create(self, spec: T_Component) -> 'Reference':
        registry = self.registry_for_spec(spec)
        existing: Optional[Base] = registry.get(spec.ref_name)
        if existing:
            _log.debug(
                'Found existing: %r.',
                existing.ref_name,
                extra=dict(
                    diff=LazyPretty(
                        lambda: deepdiff.DeepDiff(
                            existing.serialize(DEBUG_CONTEXT),
                            spec.serialize(DEBUG_CONTEXT),
                        )
                    ),
                )
            )
            return self.get_ref(spec)

        _log.info(
            'Storing definition %r:%s',
            spec.ref_name,
            LazyPretty(lambda: spec.serialize(DEBUG_CONTEXT))
        )

        registry[spec.ref_name] = spec
        return self.get_ref(spec)

    def serialize(
            self,
            ctx: SerializationContext=None,
    ):
        # Prevent components from referencing instead of rendering.
        _log.debug('Components serialize')
        if ctx is not None:
            ctx = attr.evolve(ctx, disable_referencing=True)
        else:
            _log.warning('Missing SerializationContext')
        return super(Components, self).serialize(ctx=ctx)


DEBUG_CONTEXT = SerializationContext.debug()


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
    components: 'Components' = attr.ib(
        default=attr.Factory(lambda: Components())
    )
    security: 'SecurityRequirement' = attr_skippable()
    tags: List['Tag'] = attr_skippable()
    external_docs: 'ExternalDocs' = attr_skippable()

    def serialize(
            self,
            ctx: SerializationContext=None,
    ):
        assert ctx is None
        ctx = SerializationContext(
            components=self.components
        )
        _log.debug('Using SerializationContext: %r', ctx)
        return super(OpenAPI, self).serialize(ctx=ctx)


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


@attr.s(slots=True)
class Schema(Base, MayBeReferenced):
    """
    https://github.com/OAI/OpenAPI-Specification/blob/master/versions/3.0.0.md#schema-object
    """
    SIMPLE_TYPE_ARGS = {
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
            type_: type,
            fallback_handler: T_SchemaFallbackHandler=None,
            **kwargs,
    ) -> 'Schema':
        """
        Create a Schema from a user-defined class object.

        Example:

        >>> class Book:
        ...     name = str
        ...     pages = int
        >>> Schema.from_user_type(Book)
        Schema(
            type='object',
             properties={
                'name': Schema(type='string'),
                'pages': Schema(type='integer', format='int64'),
            }
        )
        """
        pass

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
    ) -> 'Schema':
        for base, params in cls.SIMPLE_TYPE_ARGS.items():
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
