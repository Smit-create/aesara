from functools import singledispatch

import numba

from aesara.graph.fg import FunctionGraph
from aesara.link.utils import fgraph_to_python
from aesara.scalar.basic import Composite, ScalarOp
from aesara.tensor.elemwise import Elemwise


@singledispatch
def numba_typify(data, dtype=None, **kwargs):
    return data


@singledispatch
def numba_funcify(op, **kwargs):
    """Create a Numba compatible function from an Aesara `Op`."""
    raise NotImplementedError(f"No Numba conversion for the given `Op`: {op}")


@numba_funcify.register(FunctionGraph)
def numba_funcify_FunctionGraph(
    fgraph,
    order=None,
    input_storage=None,
    output_storage=None,
    storage_map=None,
    **kwargs,
):
    return fgraph_to_python(
        fgraph,
        numba_funcify,
        numba_typify,
        order,
        input_storage,
        output_storage,
        storage_map,
        fgraph_name="numba_funcified_fgraph",
        **kwargs,
    )


@numba_funcify.register(ScalarOp)
def numba_funcify_ScalarOp(op, **kwargs):
    import numpy as np

    numpy_func = getattr(np, op.nfunc_spec[0])

    @numba.njit
    def scalar_func(*args):
        result = args[0]
        for arg in args[1:]:
            result = numpy_func(arg, result)
        return result

    return scalar_func


@numba_funcify.register(Elemwise)
def numba_funcify_Elemwise(op, **kwargs):

    scalar_op = op.scalar_op
    # TODO:Vectorize this
    return numba_funcify(scalar_op)


@numba_funcify.register(Composite)
def numba_funcify_Composite(op, vectorize=True, **kwargs):
    numba_impl = numba.njit(numba_funcify(op.fgraph))

    @numba.njit
    def composite(*args):
        return numba_impl(*args)[0]

    return composite