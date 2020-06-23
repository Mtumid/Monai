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

import time
from argparse import ArgumentParser
import os

import numpy as np
import torch
from monai.transforms import AddChannelDict, Compose
from monai.losses import DiceLoss
from monai.metrics import compute_meandice
from monai.data import Dataset
from torchgpipe import GPipe
from torchgpipe.balance import balance_by_size

from unet_pipe import UNet, flatten_sequential
from data_utils import get_filenames, load_data_and_mask

N_CLASSES = 10
TRAIN_PATH = "./data/HNPETCTclean/"
VAL_PATH = "./data/HNCetuximabclean/"

torch.backends.cudnn.enabled = True


class ImageLabelDataset:
    """
    Load image and multi-class labels based on the predefined folder structure.
    """

    def __init__(self, path, n_class=10):
        self.path = path
        self.data = sorted(os.listdir(path))
        self.n_class = n_class

    def __getitem__(self, index):
        data = os.path.join(self.path, self.data[index])
        train_data, train_masks_data = get_filenames(data)
        data = load_data_and_mask(train_data, train_masks_data)  # read into a data dict
        # loading image
        data["image"] = data["image"].astype(np.float32)
        # loading labels
        class_shape = (1,) + data["image"].shape
        mask0 = np.zeros(class_shape)
        mask_list = []
        flagvect = np.ones((self.n_class,), np.float32)
        for i, mask in enumerate(data["label"]):
            if mask is None:
                mask = np.zeros(class_shape)
                flagvect[0] = 0
                flagvect[i + 1] = 0
            mask0 = np.logical_or(mask0, mask)
            mask_list.append(mask.reshape(class_shape))
        mask0 = 1 - mask0
        data["label"] = np.concatenate([mask0] + mask_list, axis=0).astype(np.uint8)
        # setting flags
        data["with_complete_groundtruth"] = flagvect  # flagvec is a boolean indicator for complete annotation
        return data

    def __len__(self):
        return len(self.data)


def train(n_feat, crop_size, bs, ep, pretrain=None):
    crop_size = [int(cz) for cz in crop_size.split(",")]
    print(f"input image crop_size: {crop_size}")

    # starting training set loader
    train_transform = Compose([AddChannelDict(keys="image")])
    train_dataset = Dataset(ImageLabelDataset(path=TRAIN_PATH, n_class=N_CLASSES), transform=train_transform)
    train_dataloader = torch.utils.data.DataLoader(train_dataset, num_workers=6, batch_size=bs, shuffle=True)
    print(train_dataset[0]["image"].shape)

    # starting validation set loader
    val_dataset = Dataset(ImageLabelDataset(VAL_PATH, n_class=N_CLASSES), transform=train_transform)
    val_dataloader = torch.utils.data.DataLoader(val_dataset, num_workers=6, batch_size=1)
    print(val_dataset[0]["image"].shape)
    print(f"training images: {len(train_dataloader)}, validation images: {len(val_dataloader)}")

    model = UNet(spatial_dims=3, in_channels=1, out_channels=N_CLASSES, n_feat=n_feat)
    model = flatten_sequential(model)
    model = model.cuda()
    lossweight = torch.from_numpy(np.array([2.22, 1.31, 1.99, 1.13, 1.93, 1.93, 1.0, 1.0, 1.90, 1.98], np.float32))

    optimizer = torch.optim.RMSprop(model.parameters(), lr=5e-4)
    # config GPipe
    data_dict = train_dataset[0]
    x = data_dict["image"]
    x = torch.from_numpy(np.expand_dims(x, 0)).float()  # adds a batch dim
    x = torch.autograd.Variable(x.cuda())
    partitions = torch.cuda.device_count()
    print(f"partition: {partitions}, input: {x.size()}")
    balance = balance_by_size(partitions, model, x)
    model = GPipe(model, balance, chunks=4, checkpoint="always")
    loss_func = DiceLoss(softmax=True, reduction="none")

    if pretrain:
        pretrained_dict = torch.load(pretrain)["weight"]
        model_dict = model.state_dict()
        pretrained_dict = {k: v for k, v in pretrained_dict.items() if k in model_dict}
        model_dict.update(pretrained_dict)
        model.load_state_dict(pretrained_dict)

    b_time = time.time()
    for epoch in range(ep):
        model.train()
        trainloss = 0
        for data_dict in train_dataloader:
            x_train = data_dict["image"]
            y_train = data_dict["label"]
            flagvec = data_dict["with_complete_groundtruth"]

            x_train = torch.autograd.Variable(x_train.cuda())
            y_train = torch.autograd.Variable(y_train.cuda().float())
            optimizer.zero_grad()
            o = model(x_train).to(0, non_blocking=True).float()

            # loss = tversky_loss_wmask(o, y_train, flagvec * torch.from_numpy(lossweight))
            # loss += 0.1 * focal(o, y_train, flagvec * torch.from_numpy(lossweight))
            loss = (loss_func(o, y_train.to(o)) * flagvec.to(o) * lossweight.to(o)).mean()
            loss.backward()
            optimizer.step()
            trainloss += loss.item()
        print("epoch %i TRAIN loss %.4f" % (epoch, trainloss / len(train_dataloader)))

        if epoch % 10 == 0:
            model.eval()
            # check validation dice
            testloss = [0 for _ in range(N_CLASSES - 1)]
            ntest = [0 for _ in range(N_CLASSES - 1)]
            for data_dict in val_dataloader:
                x_test = data_dict["image"]
                y_test = data_dict["label"]
                with torch.no_grad():
                    x_test = torch.autograd.Variable(x_test.cuda())
                o = model(x_test).to(0, non_blocking=True)
                loss = compute_meandice(o, y_test.to(o), mutually_exclusive=True, include_background=False)
                testloss = [l.item() + tl if l == l else tl for l, tl in zip(loss[0], testloss)]
                ntest = [n + 1 if l == l else n for l, n in zip(loss[0], ntest)]
            testloss = [l / n for l, n in zip(testloss, ntest)]
            print("validation scores %.4f, %.4f, %.4f, %.4f, %.4f, %.4f, %.4f, %.4f, %.4f" % tuple(testloss))

    print("total time", time.time() - b_time)


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--n_feat", type=int, default=32, dest="n_feat")
    parser.add_argument("--crop_size", type=str, default="-1,-1,-1", dest="crop_size")
    parser.add_argument("--bs", type=int, default=1, dest="bs")  # batch size
    parser.add_argument("--ep", type=int, default=150, dest="ep")  # 150
    parser.add_argument("--pretrain", type=str, default=None, dest="pretrain")
    args = parser.parse_args()

    train(**vars(args))
