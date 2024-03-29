/* SPDX-License-Identifier: BSD-3-Clause */

/*
 *  Jax_linop is being developed at the Max-Planck-Institut fuer Astrophysik
 */

/*
 *  Copyright (C) 2023, 2024 Max-Planck-Society
 *  Authors: Martin Reinecke, Jakob Roth, Gordian Edenhofer 
 */

#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>

#include <vector>
#include <map>

namespace detail_pymodule_jax {

namespace py = pybind11;
using namespace std;

// https://en.cppreference.com/w/cpp/numeric/bit_cast
template <class To, class From>
typename std::enable_if<sizeof(To) == sizeof(From) && std::is_trivially_copyable<From>::value &&
                            std::is_trivially_copyable<To>::value,
                        To>::type
bit_cast(const From& src) noexcept
  {
  static_assert(
      std::is_trivially_constructible<To>::value,
      "This implementation additionally requires destination type to be trivially constructible");

  To dst;
  memcpy(&dst, &src, sizeof(To));
  return dst;
  }

template <typename T>
pybind11::capsule EncapsulateFunction(T* fn)
  { return pybind11::capsule(bit_cast<void*>(fn), "xla._CUSTOM_CALL_TARGET"); }

void pycall(void *out, void **in)
  {
  py::gil_scoped_acquire get_GIL;

  static const map<uint8_t, py::object> tcdict = {
    { 3, py::dtype::of<float>()},
    { 7, py::dtype::of<double>()},
    {67, py::dtype::of<complex<float>>()},
    {71, py::dtype::of<complex<double>>()}};

  // the "opid" in in[1] is not used; it is only passed to guarantee uniqueness
  // of the passed parameters for every distinvt operator, so that JAX knows
  // when and when not to recompile.

  // Getting the "state" dictionary from the passed ID
  py::handle hnd(*reinterpret_cast<PyObject **>(in[2]));
  auto obj = py::reinterpret_borrow<py::object>(hnd);
  const py::dict state(obj);

  size_t idx = 3;
  // Getting type, rank, and shape of the input
  auto dtin = tcdict.at(uint8_t(*reinterpret_cast<int64_t *>(in[idx++])));
  size_t ndim_in = *reinterpret_cast<uint64_t *>(in[idx++]);
  vector<size_t> shape_in;
  for (size_t i=0; i<ndim_in; ++i)
    shape_in.push_back(*reinterpret_cast<uint64_t *>(in[idx++]));
  // Getting type, rank, and shape of the output
  auto dtout = tcdict.at(uint8_t(*reinterpret_cast<int64_t *>(in[idx++])));
  size_t ndim_out = *reinterpret_cast<uint64_t *>(in[idx++]);
  vector<size_t> shape_out;
  for (size_t i=0; i<ndim_out; ++i)
    shape_out.push_back(*reinterpret_cast<uint64_t *>(in[idx++]));

  // Building "pseudo" numpy.ndarays on top of the provided memory regions.
  // This should be completely fine, as long as the called function does not
  // keep any references to them.
  py::str dummy;
  py::array pyin (dtin, shape_in, in[0], dummy);
//  MR_assert(!pyin.owndata(), "owndata should be false");
  pyin.attr("flags").attr("writeable")=false;
//  MR_assert(!pyin.writeable(), "input array should not be writeable");
  py::array pyout (dtout, shape_out, out, dummy);
//  MR_assert(!pyout.owndata(), "owndata should be false");
//  MR_assert(pyout.writeable(), "output data must be writable");

  // Execute the Python function implementing the linear operation
  state["_func"](pyin, pyout, state);
  }

pybind11::dict Registrations()
  {
  pybind11::dict dict;
  dict["cpu_pycall"] = EncapsulateFunction(pycall);
  return dict;
  }

}

PYBIND11_MODULE(_jax_linop, m) {
  m.def("registrations", detail_pymodule_jax::Registrations);
}

