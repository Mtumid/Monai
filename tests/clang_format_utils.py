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

# this file is adapted from
# https://github.com/pytorch/pytorch/blob/v1.9.1/tools/clang_format_utils.py.

import os
import platform
import stat
import sys

from monai.apps.utils import download_url

# String representing the host platform (e.g. Linux, Darwin).
HOST_PLATFORM = platform.system()

# MONAI directory root, derived from the location of this file.
MONAI_ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

# This dictionary maps each platform to the S3 object URL for its clang-format binary.
PLATFORM_TO_CF_URL = {
    "Darwin": "https://oss-clang-format.s3.us-east-2.amazonaws.com/mac/clang-format-mojave",
    "Linux": "https://oss-clang-format.s3.us-east-2.amazonaws.com/linux64/clang-format-linux64",
}

# This dictionary maps each platform to a relative path to a file containing its reference hash.
# Refer to: https://github.com/pytorch/pytorch/tree/master/tools/clang_format_hash.
# Note: the hash value may need update when the `clang-format` package is updated in Amazon S3.
PLATFORM_TO_HASH = {
    "Darwin": "acfda23b360824017c86528f6d59769bd4cf5587",
    "Linux": "938869fb71b05f5ba345ab36dfbbc4388f53a550",
}

# Directory and file paths for the clang-format binary.
CLANG_FORMAT_DIR = os.path.join(MONAI_ROOT, ".clang-format-bin")
CLANG_FORMAT_PATH = os.path.join(CLANG_FORMAT_DIR, "clang-format")


def get_and_check_clang_format():
    """
    Download a platform-appropriate clang-format binary if one doesn't already exist at the expected location and verify
    that it is the right binary by checking its SHA1 hash against the expected hash.
    """
    # If the host platform is not in PLATFORM_TO_HASH, it is unsupported.
    if HOST_PLATFORM not in PLATFORM_TO_HASH:
        print(f"Unsupported platform: {HOST_PLATFORM}")
        return False
    if HOST_PLATFORM not in PLATFORM_TO_CF_URL:
        print(f"Unsupported platform: {HOST_PLATFORM}")
        return False

    try:
        download_url(
            PLATFORM_TO_CF_URL[HOST_PLATFORM], CLANG_FORMAT_PATH, PLATFORM_TO_HASH[HOST_PLATFORM], hash_type="sha1"
        )
    except Exception as e:
        print(f"Download {CLANG_FORMAT_PATH} failed: {e}")
        print(f"Please remove {CLANG_FORMAT_PATH} and retry.")
        return False

    # Make sure the binary is executable.
    mode = os.stat(CLANG_FORMAT_PATH).st_mode
    mode |= stat.S_IXUSR
    os.chmod(CLANG_FORMAT_PATH, mode)
    print(f"Using clang-format located at {CLANG_FORMAT_PATH}")

    return True


if __name__ == "__main__":
    ok = get_and_check_clang_format()
    sys.exit(int(not ok))
