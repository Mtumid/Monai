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

import numpy as np
import torch
from parameterized import parameterized

from monai.losses.dice import DiceFocalLoss, DiceLoss
from monai.losses.spatial_mask import MaskedLoss
from monai.utils import set_determinism
from tests.utils import SkipIfBeforePyTorchVersion, test_script_save

device = "cuda" if torch.cuda.is_available() else "cpu"

TEST_CASES = [
    [
        {
            "loss": DiceFocalLoss,
            "focal_weight": torch.tensor([1.0, 1.0, 2.0]),
            "gamma": 0.1,
            "lambda_focal": 0.5,
            "include_background": True,
            "to_onehot_y": True,
            "reduction": "sum",
        },
        [(12.105497, 18.805185), (10.636354, 6.3138)],
    ],
]


class TestMaskedLoss(unittest.TestCase):
    def setUp(self):
        set_determinism(0)

    def tearDown(self):
        set_determinism(None)

    @parameterized.expand(TEST_CASES)
    def test_shape(self, input_param, expected_val):
        size = [3, 3, 5, 5]
        label = torch.randint(low=0, high=2, size=size)
        label = torch.argmax(label, dim=1, keepdim=True)
        pred = torch.randn(size)
        print(label[0, 0, 0])
        result = MaskedLoss(**input_param)(pred, label, None)
        out = result.detach().cpu().numpy()
        checked = np.allclose(out, expected_val[0][0]) or np.allclose(out, expected_val[0][1])
        self.assertTrue(checked)

        mask = torch.randint(low=0, high=2, size=label.shape)
        result = MaskedLoss(**input_param)(pred, label, mask)
        out = result.detach().cpu().numpy()
        checked = np.allclose(out, expected_val[1][0]) or np.allclose(out, expected_val[1][1])
        self.assertTrue(checked)

    def test_ill_opts(self):
        with self.assertRaisesRegex(ValueError, ""):
            MaskedLoss(loss=[])

        dice_loss = DiceLoss(include_background=True, sigmoid=True, smooth_nr=1e-5, smooth_dr=1e-5)
        with self.assertRaisesRegex(ValueError, ""):
            masked = MaskedLoss(loss=dice_loss)
            masked(input=torch.zeros((3, 1, 2, 2)), target=torch.zeros((3, 1, 2, 2)), mask=torch.zeros((3, 3, 2, 2)))
        with self.assertRaisesRegex(ValueError, ""):
            masked = MaskedLoss(loss=dice_loss)
            masked(input=torch.zeros((3, 3, 2, 2)), target=torch.zeros((3, 2, 2, 2)), mask=torch.zeros((3, 3, 2, 2)))

    @SkipIfBeforePyTorchVersion((1, 7, 0))
    def test_script(self):
        input_param, expected_val = TEST_CASES[0]
        size = [3, 3, 5, 5]
        label = torch.randint(low=0, high=2, size=size)
        label = torch.argmax(label, dim=1, keepdim=True)
        pred = torch.randn(size)
        loss = MaskedLoss(**input_param)
        test_script_save(loss, pred, label)


if __name__ == "__main__":
    unittest.main()
