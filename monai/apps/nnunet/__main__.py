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

from monai.apps.nnunet.nnunet_runner import nnUNetRunner

"""
Examples:
    - User can use the one-liner to start the nnU-Net workflow

    .. code-block:: bash

        python -m monai.apps.nnunet nnUNetRunner run --input "./input.yaml"

    - single-gpu training for all 20 models

    .. code-block:: bash

        python -m monai.apps.nnunet nnUNetRunner train --input "./input.yaml"

    - single-gpu training for a single model

    .. code-block:: bash

        python -m monai.apps.nnunet nnUNetRunner train_single_model --input "./input.yaml" \
            --config "3d_fullres" \
            --fold 0 \
            --trainer_class_name "nnUNetTrainer_5epochs" \
            --export_validation_probabilities true

    - multi-gpu training for all 20 models

    .. code-block:: bash

        export CUDA_VISIBLE_DEVICES=0,1 # optional
        python -m monai.apps.nnunet nnUNetRunner train --input "./input.yaml" --num_gpus 2

    - multi-gpu training for a single model

    .. code-block:: bash

        export CUDA_VISIBLE_DEVICES=0,1 # optional
        python -m monai.apps.nnunet nnUNetRunner train_single_model --input "./input.yaml" \
            --config "3d_fullres" \
            --fold 0 \
            --trainer_class_name "nnUNetTrainer_5epochs" \
            --export_validation_probabilities true \
            --num_gpus 2
"""

if __name__ == "__main__":
    from monai.utils import optional_import

    fire, _ = optional_import("fire")
    fire.Fire({"nnUNetRunner": nnUNetRunner})