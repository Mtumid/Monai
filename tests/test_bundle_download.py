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

import json
import os
import subprocess
import tempfile
import unittest

import torch
from parameterized import parameterized

import monai.networks.nets as nets
from monai.apps import check_hash
from monai.bundle import ConfigParser, download, load
from tests.utils import skip_if_windows

TEST_CASE_1 = [
    ["model.pt", "model.ts", "network.json", "test_output.pt", "test_input.pt"],
    "test_bundle",
    "Project-MONAI/MONAI-extra-test-data",
    "a131d39a0af717af32d19e565b434928",
]

TEST_CASE_2 = [
    "test_bundle#network.json",
    "https://github.com/Project-MONAI/MONAI-extra-test-data/releases/download/test_bundle/network.json",
    "a131d39a0af717af32d19e565b434928",
]

TEST_CASE_3 = [
    ["model.pt", "model.ts", "network.json", "test_output.pt", "test_input.pt"],
    "test_bundle",
    "Project-MONAI/MONAI-extra-test-data",
]

TEST_CASE_4 = [
    "test_bundle#model.ts",
    "https://github.com/Project-MONAI/MONAI-extra-test-data/releases/download/test_bundle/model.ts",
    ["test_output.pt", "test_input.pt"],
    "test_bundle",
    "Project-MONAI/MONAI-extra-test-data",
]


@skip_if_windows
class TestDownload(unittest.TestCase):
    @parameterized.expand([TEST_CASE_1])
    def test_download_bundle(self, bundle_files, bundle_name, repo, hash_val):
        # download a whole bundle from github releases
        with tempfile.TemporaryDirectory() as tempdir:
            bundle_dir = os.path.join(tempdir, "test_bundle")
            cmd = ["coverage", "run", "-m", "monai.bundle", "download", "--name", bundle_name, "--source", "github"]
            cmd += ["--bundle_dir", bundle_dir, "--repo", repo, "--progress", "False"]
            subprocess.check_call(cmd)
            for file in bundle_files:
                file_path = os.path.join(bundle_dir, file)
                self.assertTrue(os.path.exists(file_path))
                # check the md5 hash of the json file
                if file == bundle_files[2]:
                    self.assertTrue(check_hash(filepath=file_path, val=hash_val))

    @parameterized.expand([TEST_CASE_2])
    def test_url_download_bundle(self, bundle_name, url, hash_val):
        # download a single file from url, also use `args_file`
        with tempfile.TemporaryDirectory() as tempdir:
            def_args = {"name": bundle_name, "bundle_dir": tempdir, "url": ""}
            def_args_file = os.path.join(tempdir, "def_args.json")
            parser = ConfigParser()
            parser.export_config_file(config=def_args, filepath=def_args_file)
            cmd = ["coverage", "run", "-m", "monai.bundle", "download", "--args_file", def_args_file]
            cmd += ["--url", url]
            subprocess.check_call(cmd)
            file_path = os.path.join(tempdir, "network.json")
            self.assertTrue(os.path.exists(file_path))
            self.assertTrue(check_hash(filepath=file_path, val=hash_val))


class TestLoad(unittest.TestCase):
    @parameterized.expand([TEST_CASE_3])
    def test_load_weights(self, bundle_files, bundle_name, repo):
        # download bundle, and load weights from the downloaded path
        with tempfile.TemporaryDirectory() as tempdir:
            # download bundle
            download(name=bundle_name, repo=repo, bundle_dir=tempdir, progress=False)

            # load weights only
            weights_name = bundle_name + "#" + bundle_files[0]
            weights = load(name=weights_name, bundle_dir=tempdir, progress=False)

            # prepare network
            with open(os.path.join(tempdir, bundle_files[2])) as f:
                net_args = json.load(f)["network_def"]
            model_name = net_args["_target_"]
            del net_args["_target_"]
            model = nets.__dict__[model_name](**net_args)
            model.load_state_dict(weights)
            model.eval()

            # prepare data and test
            input_tensor = torch.load(os.path.join(tempdir, bundle_files[4]))
            output = model.forward(input_tensor)
            expected_output = torch.load(os.path.join(tempdir, bundle_files[3]))
            torch.testing.assert_allclose(output, expected_output)

            # load instantiated model directly and test
            model_2 = load(name=weights_name, bundle_dir=tempdir, progress=False, net_name=model_name, **net_args)
            model_2.eval()
            output_2 = model_2.forward(input_tensor)
            torch.testing.assert_allclose(output_2, expected_output)

    @parameterized.expand([TEST_CASE_4])
    def test_load_ts_module(self, ts_name, url, bundle_files, bundle_name, repo):
        # load ts module from url, and download input and output tensors for testing
        with tempfile.TemporaryDirectory() as tempdir:
            # load ts module
            model_ts = load(name=ts_name, is_ts_model=True, bundle_dir=tempdir, url=url, progress=False)

            # download input and output tensors
            for file in bundle_files:
                download_name = bundle_name + "#" + file
                download(name=download_name, repo=repo, bundle_dir=tempdir, progress=False)

            # prepare and test
            input_tensor = torch.load(os.path.join(tempdir, bundle_files[1]))
            output = model_ts.forward(input_tensor)
            expected_output = torch.load(os.path.join(tempdir, bundle_files[0]))
            torch.testing.assert_allclose(output, expected_output)


if __name__ == "__main__":
    unittest.main()
