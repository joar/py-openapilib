"""
OpenAPI 3 Specification Object Model

:mod:`openapilib.spec` contains classes, each class representing an object in
the
`OpenAPI 3 Specification
<https://github.com/OAI/OpenAPI-Specification/blob/master/versions/3.0.0.md>`_

Raw example:

>>> from openapilib import serialize_spec, spec
>>> from openapilib.helpers import pretty_json
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
>>> print(pretty_json(serialize_spec(api_spec)))
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
from .serialization import serialize_spec
from .version import __version__ as VERSION

__all__ = [
    'VERSION',
    'serialize_spec',
]
