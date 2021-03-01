from monai.utils.module import optional_import
from typing import List, Tuple
from unittest.case import skipUnless
from monai.data import Dataset, DataLoader
from monai.transforms import LoadImaged, LoadImage
from monai.data import create_test_image_2d
import numpy as np
import unittest
import tempfile
from parameterized import parameterized

nib, has_nib = optional_import("nibabel")

TESTS: List[Tuple] = []
for endianness in ["<", ">"]:
    for use_array in [True, False]:
        for image_only in [True, False]:
            TESTS.append((endianness, use_array, image_only))

class TestNiftiEndianness(unittest.TestCase):
    def setUp(self):
        self.im, _ = create_test_image_2d(100, 100)
        self.fname = tempfile.NamedTemporaryFile(suffix=".nii.gz").name

    @skipUnless(has_nib, "Requires NiBabel")
    @parameterized.expand(TESTS)
    def test_value(self, endianness, use_array, image_only):

        hdr = nib.Nifti1Header(endianness=endianness)
        nii = nib.Nifti1Image(self.im, np.eye(4), header=hdr)
        nib.save(nii, self.fname)

        data = [self.fname] if use_array else [{"image": self.fname}]
        tr = LoadImage(image_only=image_only) if use_array else LoadImaged("image", image_only=image_only)
        check_ds = Dataset(data, tr)
        check_loader = DataLoader(check_ds, batch_size=1)
        _ = next(iter(check_loader))

if __name__ == "__main__":
    unittest.main()
