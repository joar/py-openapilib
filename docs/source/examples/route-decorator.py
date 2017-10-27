import json
from typing import Union, GenericMeta, List, get_type_hints
from openapilib import serialize_spec, spec

def api_route(
        summary: str=None,
        description: str=None,
        request_body_type: Union[type, GenericMeta]=None,
        response_type: Union[type, GenericMeta]=None,
        # ...
):
    def inner(func):
        # defaults
        summary_: spec.Skippable[str] = spec.SKIP
        description_: spec.Skippable[str] = spec.SKIP
        response_type_: spec.SchemaSourceType = None
        request_body_type_: spec.SchemaSourceType = None
        tags_: Set[str] = []
        # ...

        # Argument parsing

        if description is None:
            if func.__doc__ is not None:
                description_ = func.__doc__
            else:
                description_ = spec.SKIP

        if summary is not None:
            summary_ = summary
        else:
            if description_ is not spec.SKIP:
                summary_ = description_.strip().splitlines()[0]

        if response_type is not None:
            response_type_ = response_type
        else:
            response_type_ = get_type_hints(func).get('return')

        if request_body_type is not None:
            request_body_type_ = request_body_type

        # Output

        responses = {}

        if response_type_ is not None:
            responses = {
                '200': spec.Response(
                    description=description_,
                    content={
                        'application/json': spec.MediaType(
                            schema=spec.Schema.from_type(
                                response_type_,
                            )
                        )
                    }
                )
            }

        request_body = spec.SKIP

        if request_body_type_ is not None:
            request_body = spec.RequestBody(
                content={
                    'application/json': spec.MediaType(
                        schema=spec.Schema.from_type(
                            request_body_type_,
                        )
                    )
                }
            )

        operation_spec = spec.Operation(
            summary=summary_,
            description=description_,
            request_body=request_body,
            responses=responses,
            tags=tags_
        )

        # Do something with the Operation spec: We'll attach it to the route
        # handler for now
        func.operation_spec = operation_spec
        return func
    return inner


# Our example route handler code
# ------------------------------------------------------------------------------


@api_route(request_body_type=List[int])
def example_handler(request) -> int:
    pass

from openapilib.helpers import LazyPretty

print(
    json.dumps(serialize_spec(example_handler.operation_spec))
)
