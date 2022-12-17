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

import os
import sys
import tempfile
import unittest

import torch
from parameterized import parameterized

from monai.apps import check_hash
from monai.apps.mmars import MODEL_DESC, load_from_mmar
from monai.bundle import download
from monai.bundle.scripts import _remove_ngc_prefix
from monai.config import print_debug_info
from monai.networks.utils import copy_model_state
from tests.utils import skip_if_downloading_fails, skip_if_quick, skip_if_windows

TEST_CASE_NGC_1 = ["monai_spleen_ct_segmentation", "0.3.7", True, "models/model.pt", "b418a2dc8672ce2fd98dc255036e7a3d"]


@skip_if_windows
class TestNgcBundleDownload(unittest.TestCase):
    @parameterized.expand([TEST_CASE_NGC_1])
    @skip_if_quick
    def test_ngc_download_bundle(self, bundle_name, version, remove_ngc_prefix, file_path, hash_val):
        with skip_if_downloading_fails():
            with tempfile.TemporaryDirectory() as tempdir:
                download(
                    name=bundle_name,
                    source="ngc",
                    version=version,
                    bundle_dir=tempdir,
                    remove_ngc_prefix=remove_ngc_prefix,
                )
                if remove_ngc_prefix:
                    bundle_name = _remove_ngc_prefix(bundle_name)
                full_file_path = os.path.join(tempdir, bundle_name, file_path)
                self.assertTrue(os.path.exists(full_file_path))
                self.assertTrue(check_hash(filepath=full_file_path, val=hash_val))


@unittest.skip("deprecating mmar tests")
class TestAllDownloadingMMAR(unittest.TestCase):
    def setUp(self):
        print_debug_info()
        self.test_dir = "./"

    @parameterized.expand((item,) for item in MODEL_DESC)
    def test_loading_mmar(self, item):
        if item["name"] == "clara_pt_self_supervised_learning_segmentation":  # test the byow model
            default_model_file = os.path.join("ssl_models_2gpu", "best_metric_model.pt")
            pretrained_weights = load_from_mmar(
                item=item["name"],
                mmar_dir="./",
                map_location="cpu",
                api=True,
                model_file=default_model_file,
                weights_only=True,
            )
            pretrained_weights = {k.split(".", 1)[1]: v for k, v in pretrained_weights["state_dict"].items()}
            sys.path.append(os.path.join(f"{item['name']}", "custom"))  # custom model folder
            from vit_network import ViTAutoEnc  # pylint: disable=E0401

            model = ViTAutoEnc(
                in_channels=1,
                img_size=(96, 96, 96),
                patch_size=(16, 16, 16),
                pos_embed="conv",
                hidden_size=768,
                mlp_dim=3072,
            )
            _, loaded, not_loaded = copy_model_state(model, pretrained_weights)
            self.assertTrue(len(loaded) > 0 and len(not_loaded) == 0)
            return
        if item["name"] == "clara_pt_fed_learning_brain_tumor_mri_segmentation":
            default_model_file = os.path.join("models", "server", "best_FL_global_model.pt")
        else:
            default_model_file = None
        pretrained_model = load_from_mmar(
            item=item["name"], mmar_dir="./", map_location="cpu", api=True, model_file=default_model_file
        )
        self.assertTrue(isinstance(pretrained_model, torch.nn.Module))

    def tearDown(self):
        print(os.listdir(self.test_dir))


if __name__ == "__main__":
    unittest.main()
