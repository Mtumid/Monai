# Copyright 2020 - 2021 MONAI Consortium
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import unittest
from copy import deepcopy

from parameterized import parameterized

from monai.transforms import InvertibleTransform, OneOf, TraceableTransform, Transform
from monai.transforms.compose import Compose
from monai.transforms.transform import MapTransform
from monai.utils.enums import TraceKeys


class X(Transform):
    def __call__(self, x):
        return x


class Y(Transform):
    def __call__(self, x):
        return x


class A(Transform):
    def __call__(self, x):
        return x + 1


class B(Transform):
    def __call__(self, x):
        return x + 2


class C(Transform):
    def __call__(self, x):
        return x + 3


class MapBase(MapTransform):
    def __init__(self, keys):
        super().__init__(keys)
        self.fwd_fn, self.inv_fn = None, None

    def __call__(self, data):
        d = deepcopy(dict(data))
        for key in self.key_iterator(d):
            d[key] = self.fwd_fn(d[key])
        return d


class NonInv(MapBase):
    def __init__(self, keys):
        super().__init__(keys)
        self.fwd_fn = lambda x: x * 2


class Inv(MapBase, InvertibleTransform):
    def __call__(self, data):
        d = deepcopy(dict(data))
        for key in self.key_iterator(d):
            d[key] = self.fwd_fn(d[key])
            self.push_transform(d, key)
        return d

    def inverse(self, data):
        d = deepcopy(dict(data))
        for key in self.key_iterator(d):
            d[key] = self.inv_fn(d[key])
            self.pop_transform(d, key)
        return d


class InvA(Inv):
    def __init__(self, keys):
        super().__init__(keys)
        self.fwd_fn = lambda x: x + 1
        self.inv_fn = lambda x: x - 1


class InvB(Inv):
    def __init__(self, keys):
        super().__init__(keys)
        self.fwd_fn = lambda x: x + 100
        self.inv_fn = lambda x: x - 100


TESTS = [((X(), Y(), X()), (1, 2, 1), (0.25, 0.5, 0.25))]

KEYS = ["x", "y"]
TEST_INVERSES = [
    (OneOf((InvA(KEYS), InvB(KEYS))), True),
    (OneOf((OneOf((InvA(KEYS), InvB(KEYS))), OneOf((InvB(KEYS), InvA(KEYS))))), True),
    (OneOf((Compose((InvA(KEYS), InvB(KEYS))), Compose((InvB(KEYS), InvA(KEYS))))), True),
    (OneOf((NonInv(KEYS), NonInv(KEYS))), False),
]


class TestOneOf(unittest.TestCase):
    @parameterized.expand(TESTS)
    def test_normalize_weights(self, transforms, input_weights, expected_weights):
        tr = OneOf(transforms, input_weights)
        self.assertTupleEqual(tr.weights, expected_weights)

    def test_no_weights_arg(self):
        p = OneOf((X(), Y(), X(), Y()))
        expected_weights = (0.25,) * 4
        self.assertTupleEqual(p.weights, expected_weights)

    def test_len_and_flatten(self):
        p1 = OneOf((X(), Y()), (1, 3))  # 0.25, 0.75
        p2 = OneOf((Y(), Y()), (2, 2))  # 0.5. 0.5
        p = OneOf((p1, p2, X()), (1, 2, 1))  # 0.25, 0.5, 0.25
        expected_order = (X, Y, Y, Y, X)
        expected_weights = (0.25 * 0.25, 0.25 * 0.75, 0.5 * 0.5, 0.5 * 0.5, 0.25)
        self.assertEqual(len(p), len(expected_order))
        self.assertTupleEqual(p.flatten().weights, expected_weights)

    def test_compose_flatten_does_not_affect_one_of(self):
        p = Compose([A(), B(), OneOf([C(), Inv(KEYS), Compose([X(), Y()])])])
        f = p.flatten()
        # in this case the flattened transform should be the same.

        def _match(a, b):
            self.assertEqual(type(a), type(b))
            for a_, b_ in zip(a.transforms, b.transforms):
                self.assertEqual(type(a_), type(b_))
                if isinstance(a_, (Compose, OneOf)):
                    _match(a_, b_)

        _match(p, f)

    @parameterized.expand(TEST_INVERSES)
    def test_inverse(self, transform, should_be_ok):
        data = {k: (i + 1) * 10.0 for i, k in enumerate(KEYS)}
        fwd_data = transform(data)
        if not should_be_ok:
            with self.assertRaises(RuntimeError):
                transform.inverse(fwd_data)
            return

        for k in KEYS:
            t = fwd_data[TraceableTransform.transform_key(k)][-1]
            # make sure the OneOf index was stored
            self.assertEqual(t[TraceKeys.CLASS_NAME], OneOf.__name__)
            # make sure index exists and is in bounds
            self.assertTrue(0 <= t[TraceKeys.EXTRA_INFO]["index"] < len(transform))

        # call the inverse
        fwd_inv_data = transform.inverse(fwd_data)

        for k in KEYS:
            # check transform was removed
            self.assertTrue(
                len(fwd_inv_data[TraceableTransform.transform_key(k)])
                < len(fwd_data[TraceableTransform.transform_key(k)])
            )
            # check data is same as original (and different from forward)
            self.assertEqual(fwd_inv_data[k], data[k])
            self.assertNotEqual(fwd_inv_data[k], fwd_data[k])

    def test_one_of(self):
        p = OneOf((A(), B(), C()), (1, 2, 1))
        counts = [0] * 3
        for _i in range(10000):
            out = p(1.0)
            counts[int(out - 2)] += 1
        self.assertAlmostEqual(counts[0] / 10000, 0.25, delta=1.0)
        self.assertAlmostEqual(counts[1] / 10000, 0.50, delta=1.0)
        self.assertAlmostEqual(counts[2] / 10000, 0.25, delta=1.0)


if __name__ == "__main__":
    unittest.main()
