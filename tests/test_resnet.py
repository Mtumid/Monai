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
from typing import TYPE_CHECKING
import os
import re
import copy

import torch
from parameterized import parameterized

from monai.networks import eval_mode
from monai.networks.nets import ResNet, resnet10, resnet18, resnet34, resnet50, resnet101, resnet152, resnet200
from monai.networks.nets.resnet import ResNetBlock
from monai.utils import optional_import
from monai.networks.utils import get_pretrained_resnet_medicalnet
from tests.utils import test_script_save, equal_state_dict

if TYPE_CHECKING:
    import torchvision

    has_torchvision = True
else:
    torchvision, has_torchvision = optional_import("torchvision")

# from torchvision.models import ResNet50_Weights, resnet50

device = "cuda" if torch.cuda.is_available() else "cpu"

TEST_CASE_1 = [  # 3D, batch 3, 2 input channel
    {
        "pretrained": False,
        "spatial_dims": 3,
        "n_input_channels": 2,
        "num_classes": 3,
        "conv1_t_size": 7,
        "conv1_t_stride": (2, 2, 2),
    },
    (3, 2, 32, 64, 48),
    (3, 3),
]

TEST_CASE_2 = [  # 2D, batch 2, 1 input channel
    {
        "pretrained": False,
        "spatial_dims": 2,
        "n_input_channels": 1,
        "num_classes": 3,
        "conv1_t_size": [7, 7],
        "conv1_t_stride": [2, 2],
    },
    (2, 1, 32, 64),
    (2, 3),
]

TEST_CASE_2_A = [  # 2D, batch 2, 1 input channel, shortcut type A
    {
        "pretrained": False,
        "spatial_dims": 2,
        "n_input_channels": 1,
        "num_classes": 3,
        "shortcut_type": "A",
        "conv1_t_size": (7, 7),
        "conv1_t_stride": 2,
    },
    (2, 1, 32, 64),
    (2, 3),
]

TEST_CASE_3 = [  # 1D, batch 1, 2 input channels
    {
        "pretrained": False,
        "spatial_dims": 1,
        "n_input_channels": 2,
        "num_classes": 3,
        "conv1_t_size": [3],
        "conv1_t_stride": 1,
    },
    (1, 2, 32),
    (1, 3),
]

TEST_CASE_3_A = [  # 1D, batch 1, 2 input channels
    {"pretrained": False, "spatial_dims": 1, "n_input_channels": 2, "num_classes": 3, "shortcut_type": "A"},
    (1, 2, 32),
    (1, 3),
]

TEST_CASE_4 = [  # 2D, batch 2, 1 input channel
    {"pretrained": False, "spatial_dims": 2, "n_input_channels": 1, "num_classes": 3, "feed_forward": False},
    (2, 1, 32, 64),
    ((2, 512), (2, 2048)),
]

TEST_CASE_5 = [  # 1D, batch 1, 2 input channels
    {
        "block": "basic",
        "layers": [1, 1, 1, 1],
        "block_inplanes": [64, 128, 256, 512],
        "spatial_dims": 1,
        "n_input_channels": 2,
        "num_classes": 3,
        "conv1_t_size": [3],
        "conv1_t_stride": 1,
    },
    (1, 2, 32),
    (1, 3),
]

TEST_CASE_5_A = [  # 1D, batch 1, 2 input channels
    {
        "block": ResNetBlock,
        "layers": [1, 1, 1, 1],
        "block_inplanes": [64, 128, 256, 512],
        "spatial_dims": 1,
        "n_input_channels": 2,
        "num_classes": 3,
        "conv1_t_size": [3],
        "conv1_t_stride": 1,
    },
    (1, 2, 32),
    (1, 3),
]

TEST_CASE_6 = [  # 1D, batch 1, 2 input channels
    {
        "block": "bottleneck",
        "layers": [3, 4, 6, 3],
        "block_inplanes": [64, 128, 256, 512],
        "spatial_dims": 1,
        "n_input_channels": 2,
        "num_classes": 3,
        "conv1_t_size": [3],
        "conv1_t_stride": 1,
    },
    (1, 2, 32),
    (1, 3),
]

TEST_CASE_7 = [  # 1D, batch 1, 2 input channels, bias_downsample
    {
        "block": "bottleneck",
        "layers": [3, 4, 6, 3],
        "block_inplanes": [64, 128, 256, 512],
        "spatial_dims": 1,
        "n_input_channels": 2,
        "num_classes": 3,
        "conv1_t_size": [3],
        "conv1_t_stride": 1,
        "bias_downsample": False,  # set to False if pretrained=True (PR #5477)
    },
    (1, 2, 32),
    (1, 3),
]

TEST_CASES = []
PRETRAINED_TEST_CASES = []
for case in [TEST_CASE_1, TEST_CASE_2, TEST_CASE_3, TEST_CASE_2_A, TEST_CASE_3_A]:
    for model in [resnet10, resnet18, resnet34, resnet50, resnet101, resnet152, resnet200]:
        TEST_CASES.append([model, *case])
        PRETRAINED_TEST_CASES.append([model, *case])
for case in [TEST_CASE_5, TEST_CASE_5_A, TEST_CASE_6, TEST_CASE_7]:
    TEST_CASES.append([ResNet, *case])

TEST_SCRIPT_CASES = [
    [model, *TEST_CASE_1] for model in [resnet10, resnet18, resnet34, resnet50, resnet101, resnet152, resnet200]
]


class TestResNet(unittest.TestCase):
    @parameterized.expand(TEST_CASES)
    def test_resnet_shape(self, model, input_param, input_shape, expected_shape):
        net = model(**input_param).to(device)
        with eval_mode(net):
            result = net.forward(torch.randn(input_shape).to(device))
            if input_param.get("feed_forward", True):
                self.assertEqual(result.shape, expected_shape)
            else:
                self.assertTrue(result.shape in expected_shape)

    @parameterized.expand(PRETRAINED_TEST_CASES)
    def test_resnet_pretrained(self, model, input_param, input_shape, expected_shape):
        net = model(**input_param).to(device)
        tmp_ckpt_filename = "monai_unittest_tmp_ckpt.pth"
        # Save ckpt
        torch.save(net.state_dict(), tmp_ckpt_filename)

        cp_input_param = copy.copy(input_param)
        # Custom pretrained weights
        cp_input_param["pretrained"] = tmp_ckpt_filename
        pretrained_net = model(**cp_input_param)
        assert (equal_state_dict(net.state_dict(), pretrained_net.state_dict()))

        # True flag
        cp_input_param["pretrained"] = True
        resnet_depth = int(re.search(r"resnet(\d+)", model.__name__).group(1))

        # Duplicate. see monai/networks/nets/resnet.py
        def get_medicalnet_pretrained_resnet_args(resnet_depth: int) :
            """
            Return correct shortcut_type and bias_downsample for pretrained MedicalNet weights according to rensnet depth
            """
            # After testing
            # False: 10, 50, 101, 152, 200
            # Any: 18, 34
            bias_downsample = -1 if resnet_depth in [18, 34] else 0  # 18, 10, 34
            shortcut_type = "A" if resnet_depth in [18, 34] else "B"
            return bias_downsample, shortcut_type

        bias_downsample, shortcut_type = get_medicalnet_pretrained_resnet_args(resnet_depth)

        # With orig. test cases
        if (input_param.get("spatial_dims", 3) == 3 and
            input_param.get("n_input_channels", 3)==1 and
            input_param.get("feed_forward", True) is False and
            input_param.get("shortcut_type", "B") == shortcut_type and
            (input_param.get("bias_downsample", True) == bool(bias_downsample) if bias_downsample != -1 else True)
            ):
            model(**cp_input_param)
        else:
            with self.assertRaises(NotImplementedError):
                model(**cp_input_param)

        # forcing MedicalNet pretrained download for 3D tests cases
        cp_input_param["n_input_channels"] = 1
        cp_input_param["feed_forward"] = False
        cp_input_param["shortcut_type"] = shortcut_type
        cp_input_param["bias_downsample"] = bool(bias_downsample) if bias_downsample!=-1 else True
        if cp_input_param.get("spatial_dims", 3)==3:
            pretrained_net = model(**cp_input_param).to(device)
            medicalnet_state_dict = get_pretrained_resnet_medicalnet(resnet_depth, device = device)
            medicalnet_state_dict = {key.replace("module.", ""): value for key, value in medicalnet_state_dict.items()}
            assert(equal_state_dict(pretrained_net.state_dict(), medicalnet_state_dict))

        # clean
        os.remove(tmp_ckpt_filename)

    @parameterized.expand(TEST_SCRIPT_CASES)
    def test_script(self, model, input_param, input_shape, expected_shape):
        net = model(**input_param)
        test_data = torch.randn(input_shape)
        test_script_save(net, test_data)


if __name__ == "__main__":
    unittest.main()
