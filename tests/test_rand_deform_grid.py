# Copyright (c) MONAI Consortium
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import unittest

import numpy as np
from parameterized import parameterized

from monai.transforms import RandDeformGrid
from tests.utils import assert_allclose

TEST_CASES = [
    [
        dict(spacing=(1, 2), magnitude_range=(1.0, 2.0), device=None),
        {"spatial_size": (3, 3)},
        np.array(
            [
                [
                    [-3.45774551, -0.6608006, -1.62002671, -4.02259806, -2.77692349],
                    [1.21748926, -4.25845712, -1.57592837, 0.69985342, -2.16382767],
                    [-0.91158377, -0.12717178, 2.00258405, -0.85789449, -0.59616292],
                    [0.41676882, 3.96204313, 3.93633727, 2.34820726, 1.51855713],
                    [2.99011186, 4.00170105, 0.74339613, 3.57886072, 0.31633439],
                ],
                [
                    [-4.85634965, -0.78197195, -1.91838077, 1.81192079, 2.84286669],
                    [-4.34323645, -5.75784424, -2.37875058, 1.06023016, 5.24536301],
                    [-4.23315172, -1.99617861, 0.92412057, 0.81899041, 4.38084451],
                    [-5.08141703, -4.31985211, -0.52488611, 2.77048576, 4.45464513],
                    [-4.01588556, 1.21238156, 0.55444352, 3.31421131, 7.00529793],
                ],
                [
                    [1.0, 1.0, 1.0, 1.0, 1.0],
                    [1.0, 1.0, 1.0, 1.0, 1.0],
                    [1.0, 1.0, 1.0, 1.0, 1.0],
                    [1.0, 1.0, 1.0, 1.0, 1.0],
                    [1.0, 1.0, 1.0, 1.0, 1.0],
                ],
            ]
        ),
    ],
    [
        dict(spacing=(1, 2, 2), magnitude_range=(1.0, 3.0), device=None),
        {"spatial_size": (1, 2, 2)},
        np.array(
            [
                [
                    [
                        [-2.81748977, 0.66968869, -0.52625642, -3.52173734],
                        [-1.96865364, 1.76472402, -5.06258324, -1.71805669],
                        [1.11934537, -2.45103851, -2.13654555, -1.15855539],
                        [1.49678424, -2.06960677, -1.74328475, -1.7271617],
                    ],
                    [
                        [3.69301983, 3.66097025, 1.68091953, 0.6465273],
                        [1.23445289, 2.49568333, -1.56671014, 1.96849393],
                        [-2.09916271, -1.06768069, 1.51861453, -2.39180117],
                        [-0.23449363, -1.44269211, -0.42794076, -4.68520972],
                    ],
                    [
                        [-1.96578162, -0.17168741, 2.55269525, 0.70931081],
                        [1.00476444, 2.15217619, -0.47246061, 1.4748298],
                        [-0.34829048, -1.89234811, 0.34558185, 1.9606272],
                        [1.56684302, 0.98019418, 5.00513708, 1.69126978],
                    ],
                ],
                [
                    [
                        [-1.36146598, 0.7469491, -5.16647064, -4.73906938],
                        [1.91920577, -2.33606298, -0.95030633, 0.7901769],
                        [2.49116076, 3.93791246, 3.50390686, 2.79030531],
                        [1.70638302, 4.33070564, 3.52613304, 0.77965554],
                    ],
                    [
                        [-0.62725323, -1.64857887, -2.92384357, -3.39022706],
                        [-3.00611521, -0.66597021, -0.21577072, -2.39146379],
                        [2.94568388, -0.83686357, -2.55435186, 2.74064119],
                        [2.3247117, 2.78900974, 1.59788581, 0.31140512],
                    ],
                    [
                        [-0.89856598, -4.15325814, -0.21934502, -1.64845891],
                        [-1.52694693, -2.81794479, -2.22623861, -3.0299247],
                        [4.49410486, 1.27529645, 2.92559679, -1.12171559],
                        [3.30307684, 4.97189727, 2.43914751, 4.7262225],
                    ],
                ],
                [
                    [
                        [-4.81571068, -3.28263239, 1.635167, 2.36520831],
                        [-1.92511521, -4.311247, 2.19242556, 7.34990574],
                        [-3.04122716, -0.94284154, 1.30058968, -0.11719455],
                        [-2.28657395, -3.68766906, 0.28400757, 5.08072864],
                    ],
                    [
                        [-4.2308508, -0.16084264, 2.69545963, 3.4666492],
                        [-5.29514976, -1.55660775, 4.28031473, -0.39019547],
                        [-3.4617024, -1.92430221, 1.20214712, 4.25261228],
                        [-0.30683774, -1.4524049, 2.35996724, 3.83663135],
                    ],
                    [
                        [-2.20587965, -1.94408353, -0.66964855, 1.15838178],
                        [-4.26637632, -0.46145396, 2.27393031, 3.5415298],
                        [-3.91902371, 2.02343374, 3.54278271, 2.40735681],
                        [-4.3785335, -0.78200288, 3.12162619, 3.55709275],
                    ],
                ],
                [
                    [[1.0, 1.0, 1.0, 1.0], [1.0, 1.0, 1.0, 1.0], [1.0, 1.0, 1.0, 1.0], [1.0, 1.0, 1.0, 1.0]],
                    [[1.0, 1.0, 1.0, 1.0], [1.0, 1.0, 1.0, 1.0], [1.0, 1.0, 1.0, 1.0], [1.0, 1.0, 1.0, 1.0]],
                    [[1.0, 1.0, 1.0, 1.0], [1.0, 1.0, 1.0, 1.0], [1.0, 1.0, 1.0, 1.0], [1.0, 1.0, 1.0, 1.0]],
                ],
            ]
        ),
    ],
]


class TestRandDeformGrid(unittest.TestCase):
    @parameterized.expand(TEST_CASES)
    def test_rand_deform_grid(self, input_param, input_data, expected_val):
        g = RandDeformGrid(**input_param)
        g.set_random_generator(123)
        result = g(**input_data)
        assert_allclose(result, expected_val, type_test=False, rtol=1e-3, atol=1e-3)


if __name__ == "__main__":
    unittest.main()
