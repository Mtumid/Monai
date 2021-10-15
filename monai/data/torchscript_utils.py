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

import datetime
import json
import os
from typing import IO, Any, Mapping, Optional, Sequence, Tuple, Union

import torch

from monai.config import get_config_values
from monai.utils import JITMetadataKeys

METADATA_FILENAME = "metadata.json"


def save_net_with_metadata(
    jit_obj: torch.nn.Module,
    filename_prefix_or_stream: Union[str, IO[Any]],
    include_config_vals: bool = True,
    append_timestamp: bool = False,
    meta_values: Optional[Mapping[str, Any]] = None,
    more_extra_files: Optional[Mapping[str, bytes]] = None,
) -> None:
    """
    Save the JIT object (script or trace produced object) `jit_obj` to the given file or stream with metadata
    included as a JSON file. The Torchscript format is a zip file which can contain extra file data which is used
    here as a mechanism for storing metadata about the network being saved. The data in `meta_values` should be
    compatible with conversion to JSON using the standard library function `dumps`. The intent is this metadata will
    include information about the network applicable to some use case, such as describing the input and output format,
    a network name and version, a plain language description of what the network does, and other relevant scientific
    information. Clients can use this information to determine automatically how to use the network, and users can
    read what the network does and keep track of versions.

    Examples::

        net = torch.jit.script(monai.networks.nets.UNet(2, 1, 1, [8, 16], [2]))

        meta = {
            "name": "Test UNet",
            "used_for": "demonstration purposes",
            "input_dims": 2,
            "output_dims": 2
        }

        # save the Torchscript bundle with the above dictionary stored as an extra file
        save_net_with_metadata(m, "test", meta_values=meta)

        # load the network back, `loaded_meta` has same data as `meta` plus version information
        loaded_net, loaded_meta, _ = load_net_with_metadata("test.pt")


    Args:
        jit_obj: object to save, should be generated by `script` or `trace`.
        filename_prefix_or_stream: filename or file-like stream object, if filename has no extension it becomes .pt.
        include_config_vals: if True, MONAI, Pytorch, and Numpy versions are included in metadata.
        append_timestamp: if True, a timestamp for "now" is appended to the file's name before the extension.
        meta_values: metadata values to store with the object, not limited just to keys in `JITMetadataKeys`.
        more_extra_files: other extra file data items to include in bundle.
    """

    now = datetime.datetime.now()
    metadict = {}

    if include_config_vals:
        metadict.update(get_config_values())
        metadict[JITMetadataKeys.TIMESTAMP.value] = now.astimezone().isoformat()

    if meta_values is not None:
        metadict.update(meta_values)

    json_data = json.dumps(metadict)

    extra_files = {METADATA_FILENAME: json_data.encode()}

    if more_extra_files is not None:
        extra_files.update(more_extra_files)

    if isinstance(filename_prefix_or_stream, str):
        filename_no_ext, ext = os.path.splitext(filename_prefix_or_stream)
        if ext == "":
            ext = ".pt"

        if append_timestamp:
            filename_prefix_or_stream = now.strftime(f"{filename_no_ext}_%Y%m%d%H%M%S{ext}")
        else:
            filename_prefix_or_stream = filename_no_ext + ext

    torch.jit.save(jit_obj, filename_prefix_or_stream, extra_files)


def load_net_with_metadata(
    filename_prefix_or_stream: Union[str, IO[Any]],
    map_location: Optional[torch.device] = None,
    more_extra_files: Sequence[str] = (),
) -> Tuple[torch.nn.Module, dict, dict]:
    """
    Load the module object from the given Torchscript filename or stream, and convert the stored JSON metadata
    back to a dict object. This will produce an empty dict if the metadata file is not present.

    Args:
        filename_prefix_or_stream: filename or file-like stream object.
        map_location: network map location as in `torch.jit.load`.
        more_extra_files: other extra file data names to load from bundle.
    Returns:
        Triple containing loaded object, metadata dict, and extra files dict containing other file data if present
    """
    extra_files = {f: "" for f in more_extra_files}
    extra_files[METADATA_FILENAME] = ""

    jit_obj = torch.jit.load(filename_prefix_or_stream, map_location, extra_files)
    json_data = json.loads(extra_files.pop(METADATA_FILENAME, "{}"))

    return jit_obj, json_data, extra_files
