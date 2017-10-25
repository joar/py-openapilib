================================================================================
Examples
================================================================================

Hand-written :any:`Operation` spec
================================================================================

request handler decorator
================================================================================

The ``api_handler`` decorator creates an :any:`Operation` spec based on args
with fallbacks based on information available on the route handler function
itself.

-   ``Response`` ``schema`` from the "return" type annotation.
-   ``summary`` from the first line of ``func.__doc__``
-   ``description`` from ``func.__doc__``

.. literalinclude:: examples/route-decorator.py

