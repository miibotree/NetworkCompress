from Log import logger
from Init import root_dir
from Config import  Config

import keras
from keras.callbacks import ReduceLROnPlateau, CSVLogger, EarlyStopping
from keras.datasets import cifar10
from keras.layers import Conv2D, MaxPooling2D, Dense, Flatten, Input, Dropout, Activation, BatchNormalization, Embedding
from keras.models import Sequential, model_from_json, Model
from keras.optimizers import SGD
from keras.utils import np_utils, vis_utils
from keras.preprocessing.image import ImageDataGenerator
from keras import backend as K

import os, sys, re
import networkx as nx
import numpy as np
import os.path as osp


class Node(object):
    def __init__(self, type, name, config):
        self.type = type
        self.name = name
        self.config = config
        # decrypted:
        # self.input_tensors = []
        # self.output_tensors = []

    def __str__(self):
        return self.name

class MyGraph(nx.DiGraph):
    def __init__(self,model_l=None):
        super(MyGraph,self).__init__()
        if model_l is not None:
            _nodes = []
            for layer in model_l:
                type = layer[0]
                name = layer[1]
                # name_ind = int(re.findall(r'\d+', name)[0])
                config = layer[2]
                _nodes.append(Node(type, name, config))
                # if type not in self.type2inds.keys():
                #     self.type2inds[type] = [name_ind]
                # else:
                #     self.type2inds[type] += [name_ind]

            self.add_path(_nodes)


    def to_model(self,input_shape):
        graph_helper = self.copy()

        assert nx.is_directed_acyclic_graph(graph_helper)
        topo_nodes = nx.topological_sort(graph_helper)

        input_tensor = Input(shape=input_shape)

        for node in topo_nodes:
            pre_nodes = graph_helper.predecessors(node)
            suc_nodes = graph_helper.successors(node)
            # TODO Now single input; future multiple input; use len to judge
            if len(pre_nodes) == 0:
                layer_input_tensor = input_tensor
            else:
                assert len(pre_nodes) == 1
                layer_input_tensor = graph_helper[pre_nodes[0]][node]['tensor']

            if node.type == 'Conv2D':
                kernel_size = node.config.get('kernel_size', 3)
                filters = node.config['filters']

                layer = Conv2D(kernel_size=kernel_size, filters=filters, name=node.name)

            elif node.type == 'GlobalMaxPooling2D':
                layer = keras.layers.GlobalMaxPooling2D(name=node.name)

            elif node.type == 'Activation':
                activation_type = node.config['activation_type']
                layer = Activation(activation=activation_type,name=node.name)

            graph_helper.add_node(node, layer=layer)
            layer_output_tensor = layer(layer_input_tensor)
            if len(suc_nodes) == 0:
                output_tensor = layer_input_tensor
            else:
                for suc_node in suc_nodes:
                    graph_helper.add_edge(node, suc_node, tensor=layer_output_tensor)

        return Model(inputs=input_tensor, outputs=output_tensor)

class MyModel(object):
    def __init__(self,config=None,graph=None,model=None):
        if config is not None:
            self.config = config
        else:
            self.config=Config()

        if model is not None:
            self.config=model.config
            self.graph=model.graph.copy()
            self.model=self.graph.to_model(self.config.input_shape)

        elif graph is not None:
            self.graph=graph
            self.model=self.graph.to_model(self.config.input_shape)

        self.lr_reducer = ReduceLROnPlateau(monitor='val_loss', factor=np.sqrt(0.1), cooldown=0, patience=10,
                                            min_lr=0.5e-7)
        self.early_stopper = EarlyStopping(monitor='val_acc', min_delta=0.001, patience=10)
        self.csv_logger = CSVLogger(osp.join(root_dir, 'output', 'net2net.csv'))

    def update(self):
        # TODO update type2inds
        pass

    def get_layer(self, name, next_layer=False, last_layer=False):
        # for functional model
        pass

    def compile(self):
        self.model.compile(optimizer='rmsprop',
                           loss='categorical_crossentropy',
                           metrics=['accuracy'])

    def fit(self):
        self.model.fit(self.config.dataset['train_x'],
                       self.config.dataset['train_y'],
                       # validation_split=0.2,
                       validation_data=(self.config.dataset['test_x'], self.config.dataset['test_y']),
                       batch_size=self.config.batch_size,
                       epochs=self.config.epochs,
                       # callbacks=[self.lr_reducer,self.early_stopper,self.csv_logger]
                       )

    def evaluate(self):
        score = self.model.evaluate(self.config.dataset['test_x'],
                                    self.config.dataset['test_y'],
                                    batch_size=self.config.batch_size)
        return score

    def comp_fit_eval(self):
        self.compile()
        self.fit()
        score = self.evaluate()
        print('\n-- score --\n')
        print(score)

if __name__ == "__main__":

    dbg = True
    if dbg:
        config = Config(epochs=0, verbose=1, limit_data=9999)
    else:
        config = Config(epochs=100, verbose=1, limit_data=1)
    model_l= [["Conv2D", 'conv1', {'filters': 64}],
                                     ["Conv2D", 'conv2', {'filters': 64}],
                                     ["Conv2D", 'conv3', {'filters': 10}],
                                     ['GlobalMaxPooling2D', 'gmpool1', {}],
                                     ['Activation', 'activation1', {'activation_type': 'softmax'}]]
    graph=MyGraph(model_l)
    teacher_model = MyModel(config,graph)

    teacher_model.comp_fit_eval()