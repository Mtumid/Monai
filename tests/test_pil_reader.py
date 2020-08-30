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

import os
import tempfile
import unittest

import numpy as np
from parameterized import parameterized
from PIL import Image

from monai.data import PILReader

TEST_CASE_1 = [(128, 128), ["test_image.png"], (128, 128), (128, 128)]

TEST_CASE_2 = [(128, 128, 3), ["test_image.png"], (128, 128, 3), (128, 128)]

TEST_CASE_3 = [(128, 128), ["test_image1.png", "test_image2.png", "test_image3.png"], (3, 128, 128), (128, 128)]

TEST_CASE_4 = [(128, 128, 3), ["test_image.jpg"], (128, 128, 3), (128, 128)]

TEST_CASE_5 = [(128, 128, 3), ["test_image.bmp"], (128, 128, 3), (128, 128)]


class TestPNGReader(unittest.TestCase):
    @parameterized.expand([TEST_CASE_1, TEST_CASE_2, TEST_CASE_3, TEST_CASE_4, TEST_CASE_5])
    def test_shape(self, data_shape, filenames, expected_shape, meta_shape):
        test_image = np.random.randint(0, 256, size=data_shape)
        with tempfile.TemporaryDirectory() as tempdir:
            for i, name in enumerate(filenames):
                filenames[i] = os.path.join(tempdir, name)
                Image.fromarray(test_image.astype("uint8")).save(filenames[i])
            reader = PILReader()
            reader.read(filenames)
            result = reader.get_data()
            # load image by PIL and compare the result
            test_image = np.asarray(Image.open(filenames[0]))

        self.assertTupleEqual(tuple(result[1]["spatial_shape"]), meta_shape)
        self.assertTupleEqual(result[0].shape, expected_shape)
        if result[0].shape == test_image.shape:
            np.testing.assert_allclose(result[0], test_image)
        else:
            np.testing.assert_allclose(result[0], np.tile(test_image, [result[0].shape[0], 1, 1]))


if __name__ == "__main__":
    unittest.main()
