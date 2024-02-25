#%%
import jax
from functools import partial
import numpy as np
import scipy.fft
from jax.test_util import check_grads

import jax_linop

jax.config.update("jax_enable_x64", True)

from jax import numpy as jnp
import pickle



def mlin(out, args, kwargs_dump):
    kwargs = pickle.loads(np.ndarray.tobytes(kwargs_dump))
    # print(kwargs)
    out[0][()] = args[0] * args[1]
    out[1][()] = args[0] * args[1]

def mlin_T1(out, args, kwargs_dump):
    kwargs = pickle.loads(np.ndarray.tobytes(kwargs_dump))
    out[0][()] = args[0] * args[1] + args[0]*args[2]


def mlin_T2(out, args, kwargs_dump):
    kwargs = pickle.loads(np.ndarray.tobytes(kwargs_dump))
    out[0][()] = args[0] * args[1] + args[0]*args[2]


def mlin_abstract(*args, **kwargs):
    # Returns `shape` and `dtype` of output as well as the added batch_axes of the `output``
    out_axes = kwargs.pop("batch_axes", ())
    assert args[0].shape == args[1].shape
    return ((args[0].shape, args[0].dtype, out_axes)
    , (args[0].shape, args[0].dtype, out_axes))

def mlin_abstract_T1(*args, **kwargs):
    out_axes = kwargs.pop("batch_axes", ())
    assert args[0].shape == args[1].shape
    return ((args[0].shape, args[0].dtype, out_axes),)


def mlin_abstract_T2(*args, **kwargs):
    out_axes = kwargs.pop("batch_axes", ())
    assert args[0].shape == args[1].shape
    return ((args[0].shape, args[0].dtype, out_axes),)


# TODO: maybe give the user the possibility to provide more functions, such that
# more transforms can be computed
funcs = (
    (mlin_T1, mlin_T2),
    (mlin_abstract_T1, mlin_abstract_T2),
    )

mlin_jax = jax_linop.get_linear_call(
    mlin, None, mlin_abstract, None, funcs, 'mlin', arg_fixed=(True, False), func_can_batch=True
)




inp1 = 4 + jnp.zeros((2, 2))
inp2 = 1 + jnp.zeros((2, 2))


from functools import partial
mlin_jax_pt = partial(mlin_jax, inp1, axes=(3,4))
# mlin_jax_pt = partial(mlin_jax, axes=(3,4))
mlin_jax_pt(inp2)
check_grads(mlin_jax_pt, (inp2,), order=2, modes=["fwd"], eps=1.)
# check_grads(partial(mlin_jax_pt, axes=(3, 4)), inp2, order=2, modes=["fwd"], eps=1.)

# from jax.tree_util import Partial
# mlin_jax_pt = Partial(mlin_jax, inp1)
# check_grads(partial(mlin_jax_pt, axes=(3, 4)), inp2, order=2, modes=["fwd"], eps=1.)


raise SystemExit()
inp = (4 + jnp.zeros((2, 2)), 1 + jnp.zeros((2, 2)))

check_grads(partial(mlin_jax, axes=(3, 4)), inp, order=2, modes=["fwd"], eps=1.)

# NOTE: for this the transposed of the transposed would needed to be implemented
# check_grads(partial(mlin_jax, axes=(3, 4)), inp, order=2, modes=["rev"], eps=1.)



inp2 = (7 + jnp.zeros((2, 2)), -3 + jnp.zeros((2, 2)))
inp3 = (10 + jnp.zeros((2, 2)), 5 + jnp.zeros((2, 2)))

primals, f_vjp = jax.vjp(mlin_jax, *inp)
res_vjp = f_vjp(mlin_jax(*inp))
res_jvp = jax.jvp(mlin_jax, inp2, inp3)

def mlin_purejax(x,y):
    return [x*y, x*y]


primals, njf_vjp = jax.vjp(mlin_purejax, *inp)
res_vjp_jax = njf_vjp(mlin_purejax(*inp))
res_jvp_jax = jax.jvp(mlin_purejax, inp2, inp3)

np.testing.assert_allclose(res_vjp, res_vjp_jax)
np.testing.assert_allclose(res_jvp, res_jvp_jax)


# %%
