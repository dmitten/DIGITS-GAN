# Copyright (c) 2016, NVIDIA CORPORATION.  All rights reserved.
from __future__ import absolute_import

import os

import numpy as np

from digits.utils import constants, override, image, subclass
from digits.extensions.data.interface import DataIngestionInterface
from .forms import DatasetForm, InferenceForm


DATASET_TEMPLATE = "templates/dataset_template.html"
INFERENCE_TEMPLATE = "templates/inference_template.html"


def one_hot(val, depth):
    x = np.zeros(depth)
    x[val] = 1
    return x

def slerp(val, low, high):
    """Spherical interpolation. val has a range of 0 to 1."""
    if val <= 0:
        return low
    elif val >= 1:
        return high
    omega = np.arccos(np.dot(low/np.linalg.norm(low), high/np.linalg.norm(high)))
    so = np.sin(omega)
    return np.sin((1.0-val)*omega) / so * low + np.sin(val*omega)/so * high


@subclass
class DataIngestion(DataIngestionInterface):
    """
    A data ingestion extension for GANs
    """

    def __init__(self, is_inference_db=False, **kwargs):
        super(DataIngestion, self).__init__(**kwargs)

        self.userdata['is_inference_db'] = is_inference_db

        self.z_dim = 100
        self.y_dim = 10
        self.input_dim = self.z_dim + self.y_dim

    @override
    def encode_entry(self, entry):
        if not self.userdata['is_inference_db']:
            raise NotImplementedError
        else:
            if self.userdata['task_id'] in ['style', 'class', 'genimg']:
                feature = entry
                label = np.array([0])
            elif self.userdata['task_id'] == 'genz':
                raise NotImplementedError
        return feature, label

    def encode_PIL_Image(self, image):
        # convert to numpy array
        image = np.array(image)
        # add channel axis if input is grayscale image
        if image.ndim == 2:
            image = image[..., np.newaxis]
        elif image.ndim != 3:
            raise ValueError("Unhandled number of channels: %d" % image.ndim)
        # transpose to CHW
        image = image.transpose(2, 0, 1)
        return image

    @staticmethod
    @override
    def get_category():
        return "Images"

    @staticmethod
    @override
    def get_id():
        return "image-gan"

    @staticmethod
    @override
    def get_dataset_form():
        return DatasetForm()

    @staticmethod
    @override
    def get_dataset_template(form):
        """
        parameters:
        - form: form returned by get_dataset_form(). This may be populated
           with values if the job was cloned
        return:
        - (template, context) tuple
          - template is a Jinja template to use for rendering dataset creation
          options
          - context is a dictionary of context variables to use for rendering
          the form
        """
        extension_dir = os.path.dirname(os.path.abspath(__file__))
        template = open(os.path.join(extension_dir, DATASET_TEMPLATE), "r").read()
        context = {'form': form}
        return (template, context)

    @override
    def get_inference_form(self):
        return InferenceForm()

    @staticmethod
    @override
    def get_inference_template(form):
        extension_dir = os.path.dirname(os.path.abspath(__file__))
        template = open(os.path.join(extension_dir, INFERENCE_TEMPLATE), "r").read()
        context = {'form': form}
        return (template, context)

    @staticmethod
    @override
    def get_title():
        return "GAN"

    @override
    def itemize_entries(self, stage):
        entries = []
        if not self.userdata['is_inference_db']:
            raise NotImplementedError
        elif stage == constants.TEST_DB:
            if self.userdata['task_id'] == 'style':
                if self.userdata['style_z1_vector']:
                    z1 = np.array([float(v) for v in self.userdata['style_z1_vector'].split()])
                else:
                    z1 = np.random.normal(size=(100,))
                if self.userdata['style_z2_vector']:
                    z2 = np.array([float(v) for v in self.userdata['style_z2_vector'].split()])
                else:
                    z2 = np.random.normal(size=(100,))
                for val in np.linspace(0, 1, self.userdata['row_count']):
                    for c in range(10):
                        z_ = slerp(val, z1, z2)
                        feature = np.append(z_, one_hot(c, self.y_dim)).reshape((1, 1, self.input_dim))
                        entries.append(feature)
            elif self.userdata['task_id'] == 'class':
                if self.userdata['class_z_vector']:
                    z = np.array([float(v) for v in self.userdata['class_z_vector'].split()])
                else:
                    z = np.random.normal(size=(100,))
                classes = np.random.random_integers(low=0, high=9, size=2)
                for val in np.linspace(0, 1, self.userdata['row_count']):
                    for i in range(10):
                        c_0 = i
                        c_1 = (i + 1) % 10
                        feature_0 = np.append(z, one_hot(c_0, self.y_dim))
                        feature_1 = np.append(z, one_hot(c_1, self.y_dim))
                        feature = slerp(val, feature_0, feature_1).reshape((1, 1, self.input_dim))
                        entries.append(feature)
            elif self.userdata['task_id'] == 'genimg':
                c = int(self.userdata['genimg_class_id'])
                if self.userdata['genimg_z_vector']:
                    z = np.array([float(v) for v in self.userdata['genimg_z_vector'].split()])
                else:
                    z = np.random.normal(size=(100,))
                feature = np.append(z, one_hot(c, self.y_dim)).reshape((1, 1, self.input_dim))
                print(feature)
                entries.append(feature)
            else:
                raise ValueError("Unknown task: %s" % self.userdata['task_id'])
        return entries