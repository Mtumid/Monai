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
"""
Utilities and types for defining networks, these depend on PyTorch.
"""

import warnings

import torch
import torch.nn.functional as f


def one_hot(labels, num_classes):
    """
    For a tensor `labels` of dimensions B1[spatial_dims], return a tensor of dimensions `BN[spatial_dims]`
    for `num_classes` N number of classes.

    Example:

        For every value v = labels[b,1,h,w], the value in the result at [b,v,h,w] will be 1 and all others 0.
        Note that this will include the background label, thus a binary mask should be treated as having 2 classes.
    """
    num_dims = labels.dim()
    if num_dims > 1:
        assert labels.shape[1] == 1, "labels should have a channel with length equals to one."
        labels = torch.squeeze(labels, 1)
    labels = f.one_hot(labels.long(), num_classes)
    new_axes = [0, -1] + list(range(1, num_dims - 1))
    labels = labels.permute(*new_axes)
    if not labels.is_contiguous():
        return labels.contiguous()
    return labels


def slice_channels(tensor, *slicevals):
    slices = [slice(None)] * len(tensor.shape)
    slices[1] = slice(*slicevals)

    return tensor[slices]


def predict_segmentation(logits, mutually_exclusive=False, threshold=0):
    """
    Given the logits from a network, computing the segmentation by thresholding all values above 0
    if multi-labels task, computing the `argmax` along the channel axis if multi-classes task,
    logits has shape `BCHW[D]`.

    Args:
        logits (Tensor): raw data of model output.
        mutually_exclusive (bool): if True, `logits` will be converted into a binary matrix using
            a combination of argmax, which is suitable for multi-classes task. Defaults to False.
        threshold (float): thresholding the prediction values if multi-labels task.
    """
    if not mutually_exclusive:
        return (logits >= threshold).int()
    else:
        if logits.shape[1] == 1:
            warnings.warn("single channel prediction, `mutually_exclusive=True` ignored, use threshold instead.")
            return (logits >= threshold).int()
        return logits.argmax(1, keepdim=True)


def normalize_transform(shape, device=None, dtype=None, align_corners=False):
    """
    Compute an affine matrix according to the input shape.
    The transform normalizes the homogeneous image coordinates to the
    range of `[-1, 1]`.

    Args:
        shape (sequence of int): input spatial shape
        device (torch device): device on which the returned affine will be allocated.
        dtype (torch dtype): data type of the returned affine
        align_corners (bool): if True, consider -1 and 1 to refer to the centers of the
            corner pixels rather than the image corners.
            See also: https://pytorch.org/docs/stable/nn.functional.html#torch.nn.functional.grid_sample
    """
    shape_ = list(shape)[::-1]
    if align_corners:
        norm = torch.as_tensor(shape_ + [1.0], dtype=dtype, device=device)
        norm[:-1] = 2.0 / (norm[:-1] - 1.0)
        norm = torch.diag(norm)
        norm[:-1, -1] = -1.0
    else:
        norm = torch.as_tensor(shape_ + [1.0], dtype=dtype, device=device)
        norm[:-1] = 2.0 / norm[:-1]
        norm = torch.diag(norm)
        norm[:-1, -1] = 1.0 / torch.as_tensor(shape_, dtype=dtype, device=device) - 1.0
    norm = norm.unsqueeze(0)  # adds a batch dim.
    norm.requires_grad = False
    return norm


def to_norm_affine(affine, src_size, dst_size, align_corners=False):
    """
    Given ``affine`` defined for coordinates in the pixel space, compute the corresponding affine
    for the normalized coordinates.

    Args:
        affine (torch Tensor): Nxdxd batched square matrix
        src_size (sequence of int): source image spatial shape
        dst_size (sequence of int): target image spatial shape
        align_corners (bool): if True, consider -1 and 1 to refer to the centers of the
            corner pixels rather than the image corners.
            See also: https://pytorch.org/docs/stable/nn.functional.html#torch.nn.functional.grid_sample
    """
    if not torch.is_tensor(affine):
        raise ValueError("affine must be a tensor")
    if affine.ndim != 3 or affine.shape[1] != affine.shape[2]:
        raise ValueError(f"affine must be Nxdxd, got {tuple(affine.shape)}")
    sr = affine.shape[1] - 1
    if sr != len(src_size) or sr != len(dst_size):
        raise ValueError(
            f"affine suggests a {sr}-D transform, but the sizes are src_size={src_size}, dst_size={dst_size}"
        )

    src_xform = normalize_transform(src_size, affine.device, affine.dtype, align_corners)
    dst_xform = normalize_transform(dst_size, affine.device, affine.dtype, align_corners)
    new_affine = src_xform @ affine @ torch.inverse(dst_xform)
    return new_affine
