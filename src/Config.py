# Dependency: Utils
from __future__ import division
from __future__ import print_function

import argparse, sys, json
import keras
import numpy as np
import os.path as osp
import tensorflow as tf
from keras import backend as K
from keras.callbacks import ReduceLROnPlateau, CSVLogger, EarlyStopping
from keras.datasets import cifar10, mnist, cifar100
from math import log
import Utils
from Utils import root_dir, load_data_svhn
import os


class MyConfig(object):
    # for all model
    tf_graph = tf.get_default_graph()
    _sess_config = tf.ConfigProto(allow_soft_placement=True)
    _sess_config.gpu_options.allow_growth = True
    sess = tf.Session(config=_sess_config, graph=tf_graph)
    K.set_session(sess)
    K.set_image_data_format("channels_last")
    # # for all model, but determined when init the first config
    cache_data = None

    def __init__(self, epochs=100, verbose=1, limit_data=False, name='default_name', evoluation_time=1, clean=True,
                 dataset_type='cifar10', max_pooling_cnt=0, debug=False):
        # for all model:
        self.dataset_type = dataset_type
        self.limit_data = limit_data
        if dataset_type == 'cifar10' or dataset_type == 'svhn' or dataset_type == 'cifar100':
            self.input_shape = (32, 32, 3)
        else:
            self.input_shape = (28, 28, 1)
        self.nb_class = 10
        self.dataset = None
        if limit_data:
            self.load_data(9999, type=self.dataset_type)
        else:
            self.load_data(1, type=self.dataset_type)

        # for ga:
        self.evoluation_time = evoluation_time

        # for single model
        self.set_name(name, clean=clean)
        self.batch_size = 256
        self.epochs = epochs
        self.verbose = verbose
        self.lr_reducer = ReduceLROnPlateau(monitor='val_loss', factor=np.sqrt(0.1), cooldown=0, patience=10,
                                            min_lr=0.5e-7)
        self.early_stopper = EarlyStopping(monitor='val_acc', min_delta=0.001, patience=5)
        self.csv_logger = None
        self.set_logger_path(self.name + '.csv')
        self.debug = debug
        self.max_pooling_limit = int(log(min(self.input_shape[0], self.input_shape[1]), 2)) - 2
        self.max_pooling_cnt = max_pooling_cnt

        self.model_max_conv_width = 1024
        self.model_min_conv_width = 128
        self.model_max_depth = 20
        self.kernel_regularizer_l2 = 0.0

    def set_logger_path(self, name):
        self.csv_logger = CSVLogger(osp.join(self.output_path, name))

    def to_json(self):
        d = dict(name=self.name,
                 epochs=self.epochs,
                 verbose=self.verbose)
        with open(osp.join(self.output_path, 'config.json')) as f:
            json.dumps(f, d)
        return

    def copy(self, name='diff_name'):
        new_config = MyConfig(self.epochs, self.verbose, limit_data=self.limit_data, name=name,
                              evoluation_time=self.evoluation_time, dataset_type=self.dataset_type,
                              max_pooling_cnt=self.max_pooling_cnt)
        return new_config

    def set_name(self, name, clean=True):
        self.name = name
        self.tf_log_path = osp.join(root_dir, 'output/tf_tmp/', name)
        self.output_path = osp.join(root_dir, 'output/', name)
        self.model_path = osp.join(root_dir, 'output/', name, name + '.h5')
        if clean:
            Utils.mkdir_p(self.tf_log_path)
            Utils.mkdir_p(self.output_path)

    def _preprocess_input(self, x, mean_image=None):
        x = x.reshape((-1,) + self.input_shape)
        x = x.astype("float32")
        if mean_image is None:
            mean_image = np.mean(x, axis=0)
        x -= mean_image
        x /= 128.
        return x, mean_image

    def _preprocess_output(self, y):
        return keras.utils.np_utils.to_categorical(y, self.nb_class)

    @staticmethod
    def _limit_data(x, div):
        div = min(float(div), x.shape[0] - 1)
        return x[:int(x.shape[0] / div), ...]

    def load_data(self, limit_data, type='cifar10'):
        if MyConfig.cache_data is None:
            if type == 'cifar10':
                (train_x, train_y), (test_x, test_y) = cifar10.load_data()
            elif type == 'mnist':
                (train_x, train_y), (test_x, test_y) = mnist.load_data()
            elif type == 'cifar100':
                (train_x, train_y), (test_x, test_y) = cifar100.load_data(label_mode='fine')
            elif type == 'svhn':
                (train_x, train_y), (test_x, test_y) = load_data_svhn()

            train_x, mean_img = self._preprocess_input(train_x, None)
            test_x, _ = self._preprocess_input(test_x, mean_img)

            train_y, test_y = map(self._preprocess_output, [train_y, test_y])

            res = {'train_x': train_x, 'train_y': train_y, 'test_x': test_x, 'test_y': test_y}

            for key, val in res.iteritems():
                res[key] = MyConfig._limit_data(val, limit_data)
            MyConfig.cache_data = res
            print('load data: x shape {}, y shape {}'.format(res['train_x'].shape,
                                                             res['train_y'].shape))
        self.dataset = MyConfig.cache_data


if __name__ == '__main__':
    config = MyConfig(epochs=1, verbose=2, limit_data=False, name='ga', evoluation_time=3, dataset_type='mnist')
