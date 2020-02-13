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

import os
import sys
import tempfile
from glob import glob
import logging

import nibabel as nib
import numpy as np
import torch
import monai.data.transforms.compose as transforms
from torch.utils.tensorboard import SummaryWriter
from ignite.engine import Events, create_supervised_trainer, create_supervised_evaluator
from ignite.handlers import ModelCheckpoint, EarlyStopping
from torch.utils.data import DataLoader

from monai import application, networks, utils
from monai.data.readers import NiftiDataset
from monai.data.transforms import (AddChannel, Rescale, ToTensor, UniformRandomPatch)
from monai.application.handlers.stats_handler import StatsHandler
from monai.networks.metrics.mean_dice import MeanDice
from monai.utils.stopperutils import stopping_fn_from_metric

# assumes the framework is found here, change as necessary
sys.path.append("..")

application.config.print_config()


def create_test_image_3d(height, width, depth, num_objs=12, rad_max=30, noise_max=0.0, num_seg_classes=5):
    '''Return a noisy 3D image and segmentation.'''
    image = np.zeros((width, height, depth))

    for i in range(num_objs):
        x = np.random.randint(rad_max, width - rad_max)
        y = np.random.randint(rad_max, height - rad_max)
        z = np.random.randint(rad_max, depth - rad_max)
        rad = np.random.randint(5, rad_max)
        spy, spx, spz = np.ogrid[-x:width - x, -y:height - y, -z:depth - z]
        circle = (spx * spx + spy * spy + spz * spz) <= rad * rad

        if num_seg_classes > 1:
            image[circle] = np.ceil(np.random.random() * num_seg_classes)
        else:
            image[circle] = np.random.random() * 0.5 + 0.5

    labels = np.ceil(image).astype(np.int32)

    norm = np.random.uniform(0, num_seg_classes * noise_max, size=image.shape)
    noisyimage = utils.arrayutils.rescale_array(np.maximum(image, norm))

    return noisyimage, labels

# Create a temporary directory and 50 random image, mask paris
tempdir = tempfile.mkdtemp()

for i in range(50):
    im, seg = create_test_image_3d(256, 256, 256)

    n = nib.Nifti1Image(im, np.eye(4))
    nib.save(n, os.path.join(tempdir, 'im%i.nii.gz' % i))

    n = nib.Nifti1Image(seg, np.eye(4))
    nib.save(n, os.path.join(tempdir, 'seg%i.nii.gz' % i))

images = sorted(glob(os.path.join(tempdir, 'im*.nii.gz')))
segs = sorted(glob(os.path.join(tempdir, 'seg*.nii.gz')))

# Define transforms for image and segmentation
imtrans = transforms.Compose([Rescale(), AddChannel(), UniformRandomPatch((64, 64, 64)), ToTensor()])
segtrans = transforms.Compose([AddChannel(), UniformRandomPatch((64, 64, 64)), ToTensor()])

# Define nifti dataset, dataloader.
ds = NiftiDataset(images, segs, imtrans, segtrans)
loader = DataLoader(ds, batch_size=10, num_workers=2, pin_memory=torch.cuda.is_available())
im, seg = utils.mathutils.first(loader)
print(im.shape, seg.shape)


lr = 1e-3
train_epochs = 30

# Create UNet, DiceLoss and Adam optimizer.
net = networks.nets.UNet(
    dimensions=3,
    in_channels=1,
    num_classes=1,
    channels=(16, 32, 64, 128, 256),
    strides=(2, 2, 2, 2),
    num_res_units=2,
)

loss = networks.losses.DiceLoss(do_sigmoid=True)
opt = torch.optim.Adam(net.parameters(), lr)

train_epochs = 3

# Since network outputs logits and segmentation, we need a custom function.
def _loss_fn(i, j):
    return loss(i[0], j)

# Create trainer
device = torch.device("cuda:0")
trainer = create_supervised_trainer(net, opt, _loss_fn, device, False,
                                    output_transform=lambda x, y, y_pred, loss: [y_pred, loss.item(), y])

checkpoint_handler = ModelCheckpoint('./', 'net', n_saved=10, require_empty=False)
trainer.add_event_handler(event_name=Events.EPOCH_COMPLETED, handler=checkpoint_handler, to_save={'net': net})

dice_metric = MeanDice(add_sigmoid=True, output_transform=lambda output: (output[0][0], output[2]))
dice_metric.attach(trainer, "Training Dice")

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
stats_logger = StatsHandler()
stats_logger.attach(trainer)


@trainer.on(Events.EPOCH_COMPLETED)
def log_training_loss(engine):
    # log loss to tensorboard with second item of engine.state.output, loss.item() from output_transform
    writer.add_scalar('Loss/train', engine.state.output[1], engine.state.epoch)

    # tensor of ones to use where for converting labels to zero and ones
    ones = torch.ones(engine.state.batch[1][0].shape, dtype=torch.int32)
    first_output_tensor = engine.state.output[0][1][0].detach().cpu()
    # log model output to tensorboard, as three dimensional tensor with no channels dimension
    utils.img2tensorboardutils.add_animated_gif_no_channels(writer, "first_output_final_batch", first_output_tensor, 64,
                                                            255, engine.state.epoch)
    # get label tensor and convert to single class
    first_label_tensor = torch.where(engine.state.batch[1][0] > 0, ones, engine.state.batch[1][0])
    # log label tensor to tensorboard, there is a channel dimension when getting label from batch
    utils.img2tensorboardutils.add_animated_gif(writer, "first_label_final_batch", first_label_tensor, 64,
                                                255, engine.state.epoch)
    second_output_tensor = engine.state.output[0][1][1].detach().cpu()
    utils.img2tensorboardutils.add_animated_gif_no_channels(writer, "second_output_final_batch", second_output_tensor, 64,
                                                            255, engine.state.epoch)
    second_label_tensor = torch.where(engine.state.batch[1][1] > 0, ones, engine.state.batch[1][1])
    utils.img2tensorboardutils.add_animated_gif(writer, "second_label_final_batch", second_label_tensor, 64,
                                                255, engine.state.epoch)
    third_output_tensor = engine.state.output[0][1][2].detach().cpu()
    utils.img2tensorboardutils.add_animated_gif_no_channels(writer, "third_output_final_batch", third_output_tensor, 64,
                                                            255, engine.state.epoch)
    third_label_tensor = torch.where(engine.state.batch[1][2] > 0, ones, engine.state.batch[1][2])
    utils.img2tensorboardutils.add_animated_gif(writer, "third_label_final_batch", third_label_tensor, 64,
                                                255, engine.state.epoch)
    engine.logger.info("Epoch[%s] Loss: %s", engine.state.epoch, engine.state.output[1])


loader = DataLoader(ds, batch_size=20, num_workers=8, pin_memory=torch.cuda.is_available())
val_loader = DataLoader(ds, batch_size=20, num_workers=8, pin_memory=torch.cuda.is_available())
writer = SummaryWriter()

# Define mean dice metric and Evaluator.
validation_every_n_epochs = 1

val_metrics = {'Mean Dice': MeanDice(add_sigmoid=True)}
evaluator = create_supervised_evaluator(net, val_metrics, device, True,
                                        output_transform=lambda x, y, y_pred: (y_pred[0], y))

val_stats_handler = StatsHandler()
val_stats_handler.attach(evaluator)

# Add early stopping handler to evaluator.
early_stopper = EarlyStopping(patience=4, 
                              score_function=stopping_fn_from_metric('Mean Dice'),
                              trainer=trainer)
evaluator.add_event_handler(event_name=Events.EPOCH_COMPLETED, handler=early_stopper)

@trainer.on(Events.EPOCH_COMPLETED(every=validation_every_n_epochs))
def run_validation(engine):
    evaluator.run(val_loader)


state = trainer.run(loader, train_epochs)
