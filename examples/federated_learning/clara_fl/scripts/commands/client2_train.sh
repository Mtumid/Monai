#!/usr/bin/env bash
export CUDA_VISIBLE_DEVICES=1
export PYTHONPATH="/workspace/data/medical/Clara/federated-learning/src"
export MMAR_ROOT="/workspace/data/medical/MONAI/examples/federated_learning/clara_fl/scripts"

CLIENT_FILE=config/config_fed_client2.json

python3 -u -m examples.federated_learning.clara_fl.client.admin_fed_local_train \
    -m $MMAR_ROOT \
    -s $CLIENT_FILE \
    --set \
    secure_train=true \
    uid=2
