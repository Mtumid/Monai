# Copyright 2020 MONAI Consortium
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

import numpy as np
import skimage
from parameterized import parameterized
from tests.utils import NumpyImageTestCase2D

from monai.transforms import Resized


class TestResized(NumpyImageTestCase2D):
    def test_invalid_inputs(self):
        with self.assertRaises(NotImplementedError):
            resize = Resized(keys="img", spatial_size=(128, 128, 3), interp_order="order")
            resize({"img": self.imt[0]})

        with self.assertRaises(ValueError):
            resize = Resized(keys="img", spatial_size=(128,), interp_order="order")
            resize({"img": self.imt[0]})

    @parameterized.expand([((64, 64), "area"), ((32, 32, 32), "area"), ((256, 256), "bilinear")])
    def test_correct_results(self, spatial_size, interp_order):
        resize = Resized("img", spatial_size, interp_order)
        _order = 0
        if interp_order.endswith("linear"):
            _order = 1
        expected = list()
        for channel in self.imt[0]:
            expected.append(
                skimage.transform.resize(
                    channel, spatial_size, order=_order, clip=False, preserve_range=False, anti_aliasing=False,
                )
            )
        expected = np.stack(expected).astype(np.float32)
        out = resize({"img": self.imt[0]})["img"]
        np.testing.assert_allclose(out, expected, atol=0.9)


if __name__ == "__main__":
    unittest.main()
