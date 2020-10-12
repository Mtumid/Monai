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
from parameterized import parameterized

from monai.transforms import RandGaussianSharpend

TEST_CASE_1 = [
    {"keys": "img", "prob": 1.0},
    {"img": np.array([[[1, 1, 1], [2, 2, 2], [3, 3, 3]], [[4, 4, 4], [5, 5, 5], [6, 6, 6]]])},
    np.array(
        [
            [[5.2919216, 5.5854445, 5.29192], [11.3982, 12.62332, 11.398202], [14.870525, 17.323769, 14.870527]],
            [[20.413757, 22.767355, 20.413757], [28.495504, 31.558315, 28.495499], [29.99236, 34.505676, 29.992361]],
        ]
    ),
]

TEST_CASE_2 = [
    {
        "keys": "img",
        "sigma1_x": (0.5, 0.75),
        "sigma1_y": (0.5, 0.75),
        "sigma1_z": (0.5, 0.75),
        "sigma2_x": 0.4,
        "sigma2_y": 0.4,
        "sigma2_z": 0.4,
        "prob": 1.0,
    },
    {"img": np.array([[[1, 1, 1], [2, 2, 2], [3, 3, 3]], [[4, 4, 4], [5, 5, 5], [6, 6, 6]]])},
    np.array(
        [
            [[4.1071496, 3.597953, 4.1071477], [10.062014, 9.825114, 10.0620165], [14.698058, 15.818766, 14.698058]],
            [[18.211048, 18.16049, 18.211048], [25.155039, 24.56279, 25.155039], [28.801964, 30.381308, 28.801964]],
        ]
    ),
]

TEST_CASE_3 = [
    {
        "keys": "img",
        "sigma1_x": (0.5, 0.75),
        "sigma1_y": (0.5, 0.75),
        "sigma1_z": (0.5, 0.75),
        "sigma2_x": (0.5, 0.75),
        "sigma2_y": (0.5, 0.75),
        "sigma2_z": (0.5, 0.75),
        "prob": 1.0,
    },
    {"img": np.array([[[1, 1, 1], [2, 2, 2], [3, 3, 3]], [[4, 4, 4], [5, 5, 5], [6, 6, 6]]])},
    np.array(
        [
            [[4.81077, 4.4237204, 4.81077], [12.061236, 12.298177, 12.061236], [17.362553, 19.201174, 17.362553]],
            [[21.440754, 22.142393, 21.440754], [30.15308, 30.745445, 30.153086], [33.99255, 36.919838, 33.99255]],
        ]
    ),
]

TEST_CASE_4 = [
    {
        "keys": "img",
        "sigma1_x": (0.5, 0.75),
        "sigma1_y": (0.5, 0.75),
        "sigma1_z": (0.5, 0.75),
        "sigma2_x": (0.5, 0.75),
        "sigma2_y": (0.5, 0.75),
        "sigma2_z": (0.5, 0.75),
        "approx": "refined",
        "prob": 1.0,
    },
    {"img": np.array([[[1, 1, 1], [2, 2, 2], [3, 3, 3]], [[4, 4, 4], [5, 5, 5], [6, 6, 6]]])},
    np.array(
        [
            [[5.415007, 4.9318314, 5.415007], [12.503677, 12.35288, 12.5036745], [18.72623, 19.844906, 18.72623]],
            [[23.520931, 23.51439, 23.520939], [31.259188, 30.882202, 31.25918], [36.83216, 38.427456, 36.83216]],
        ]
    ),
]


class TestRandGaussianSharpend(unittest.TestCase):
    @parameterized.expand([TEST_CASE_1, TEST_CASE_2, TEST_CASE_3, TEST_CASE_4])
    def test_value(self, argments, image, expected_data):
        converter = RandGaussianSharpend(**argments)
        converter.set_random_state(seed=0)
        result = converter(image)
        np.testing.assert_allclose(result["img"], expected_data, rtol=1e-4)


if __name__ == "__main__":
    unittest.main()
