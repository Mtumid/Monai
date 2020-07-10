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

from typing import Callable

from monai.utils import exact_version, optional_import

Engine, _ = optional_import("ignite.engine", "0.3.0", exact_version, "Engine")


def stopping_fn_from_metric(metric_name: str) -> Callable:
    """
    Returns a stopping function for ignite.handlers.EarlyStopping using the given metric name.
    """

    def stopping_fn(engine: Engine):
        return engine.state.metrics[metric_name]

    return stopping_fn


def stopping_fn_from_loss() -> Callable:
    """
    Returns a stopping function for ignite.handlers.EarlyStopping using the loss value.
    """

    def stopping_fn(engine: Engine):
        return -engine.state.output

    return stopping_fn
