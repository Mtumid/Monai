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

import sys
from typing import Callable, List, Optional, Sequence, Tuple, Union

import numpy as np

from monai.data import Dataset, SmartCacheDataset
from monai.data.image_reader import WSIReader

__all__ = ["PatchWSIDataset", "SmartCachePatchWSIDataset"]


class PatchWSIDataset(Dataset):
    """
    This dataset read whole slide images, extract regions, and crate patches.
    It also reads labels for each patch and privide each patch with its associated class labels.

    Args:
        data: the list of input samples including image, location, and label (see below for more details)
        region_size: the region to be extracted from the whole slide image
        grid_shape: the grid shape on which the patches should be extracted
        patch_size: the patches extracted from the region on the grid
        image_reader_name: the name of library to be used for loading whole slide imaging,
            either CuCIM or OpenSlide (the default is CuCIM)
        transform: transforms to be executed on input data.

    Note:
        The input data has the following form as an example:
        [{"image": "path/to/image1.tiff", "location": [200, 500], "label": [0,0,0,1]}].

        This means from "image1.tiff" extract a region at "location" with the side of "region_size", and
        then extract patches with the size of "patch_size" from a square grid with the shape of "grid_shape".
        Be aware the the "grid_shape" should construct a grid with the same number of element as "labels", so
        for this example the "grid_size" should be (2, 2).

        The output will look like the following:
        [
            {"image": np.array([...], dtype=np.uint8), "label": 0},
            {"image": np.array([...], dtype=np.uint8), "label": 0},
            {"image": np.array([...], dtype=np.uint8), "label": 0},
            {"image": np.array([...], dtype=np.uint8), "label": 1},
        ]

    """

    def __init__(
        self,
        data: List,
        region_size: Union[int, Tuple[int, int]],
        grid_shape: Union[int, Tuple[int, int]],
        patch_size: int,
        image_reader_name: str = "cuCIM",
        transform: Union[Sequence[Callable], Callable] = None,
    ):
        if type(region_size) == int:
            self.region_size = (region_size, region_size)
        else:
            self.region_size = region_size

        if type(grid_shape) == int:
            self.grid_shape = (grid_shape, grid_shape)
        else:
            self.grid_shape = grid_shape

        self.patch_size = patch_size
        self.sub_region_size = (self.region_size[0] / self.grid_shape[0], self.region_size[1] / self.grid_shape[1])

        self.transform = transform
        self.samples = data
        self.image_path_list = list({x["image"] for x in self.samples})

        self.image_reader_name = image_reader_name
        self.image_reader = WSIReader(image_reader_name)
        self.wsi_object_dict = None
        if self.image_reader_name != "openslide":
            # OpenSlide causes memeory issue if we prefetch image objects
            self._fetch_wsi_objects()

    def _fetch_wsi_objects(self):
        self.wsi_object_dict = {}
        for image_path in self.image_path_list:
            self.wsi_object_dict[image_path] = self.image_reader.read(image_path)

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, index):
        sample = self.samples[index]
        if self.image_reader_name == "openslide":
            img_obj = self.image_reader.read(sample["image"])
        else:
            img_obj = self.wsi_object_dict[sample["image"]]
        images, _ = self.image_reader.get_data(
            img=img_obj,
            location=sample["location"],
            size=self.region_size,
            grid_shape=self.grid_shape,
            patch_size=self.patch_size,
        )
        labels = np.array(sample["label"], dtype=np.float32)[:, np.newaxis, np.newaxis]
        patches = [{"image": images[i], "label": labels[i]} for i in range(len(sample["label"]))]
        if self.transform:
            patches = self.transform(patches)
        return patches


class SmartCachePatchWSIDataset(SmartCacheDataset):
    """
    Add SmartCache functionality to PatchWSIDataset
    """

    def __init__(
        self,
        data: List,
        region_size: Union[int, Tuple[int, int]],
        grid_shape: Union[int, Tuple[int, int]],
        patch_size: int,
        image_reader_name: str = "cuCIM",
        transform: Union[Sequence[Callable], Callable] = None,
        replace_rate: float = 0.5,
        cache_num: int = sys.maxsize,
        cache_rate: float = 1.0,
        num_init_workers: Optional[int] = None,
        num_replace_workers: Optional[int] = None,
    ):
        extractor = PatchWSIDataset(data, region_size, grid_shape, patch_size, image_reader_name)
        super().__init__(
            data=extractor,
            transform=transform,
            replace_rate=replace_rate,
            cache_num=cache_num,
            cache_rate=cache_rate,
            num_init_workers=num_init_workers,
            num_replace_workers=num_replace_workers,
        )
