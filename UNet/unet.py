# tf_unet is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# tf_unet is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with tf_unet.  If not, see <http://www.gnu.org/licenses/>.


'''
Created on Jul 28, 2016

author: jakeret
'''
from __future__ import print_function, division, absolute_import, unicode_literals

import os
import shutil
import numpy as np
from collections import OrderedDict
import logging

import tensorflow as tf

from parameter import Parameter
import util
from layers import (weight_variable, weight_variable_devonc, bias_variable,
                    conv2d, conv2d_2, deconv2d, deconv2d_2, max_pool, pixel_wise_softmax, cross_entropy,
                    inception_conv, dense_link, cropCenter)

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
para = Parameter()

def create_IVD_net(x, keep_prob, channels, n_class, layers=5, features_root=32, summaries=True, training=True):
    logging.info(
        "Layers {layers}, features {features}".format(
            layers=layers,
            features=features_root))

    # Placeholder for the input image
    with tf.name_scope("preprocessing"):
        nx = tf.shape(x)[1]
        ny = tf.shape(x)[2]
        x_image = tf.reshape(x, tf.stack([-1, nx, ny, channels]))
        in_node = x_image
        batch_size = tf.shape(x_image)[0]

    weights = []
    biases = []
    fat_inputs = OrderedDict();     inn_inputs = OrderedDict();     wat_inputs = OrderedDict();     opp_inputs = OrderedDict();
    fat_pools = OrderedDict();      inn_pools = OrderedDict();      wat_pools = OrderedDict();      opp_pools = OrderedDict()
    fat_dw_h_convs = OrderedDict(); inn_dw_h_convs = OrderedDict(); wat_dw_h_convs = OrderedDict(); opp_dw_h_convs = OrderedDict();
    deconv = OrderedDict()
    up_h_convs = OrderedDict()

    # down layers
    for layer in range(0, layers):
        with tf.name_scope("down_conv_{}".format(str(layer))):
            features = 2 ** layer * features_root
            if layer==0:
                with tf.name_scope("fat"):
                    in_node = tf.reshape(x_image[..., 0],[batch_size, nx, ny, 1])
                    conv = inception_conv(in_node, 1, features, keep_prob, training)
                    fat_dw_h_convs[layer] = conv
                    fat_pools[layer] = max_pool(conv, 2)
                with tf.name_scope("inn"):
                    in_node = tf.reshape(x_image[..., 1],[batch_size, nx, ny, 1])
                    conv = inception_conv(in_node, 1, features, keep_prob, training)
                    inn_dw_h_convs[layer] = conv
                    inn_pools[layer] = max_pool(conv, 2)
                with tf.name_scope("wat"):
                    in_node = tf.reshape(x_image[..., 2],[batch_size, nx, ny, 1])
                    conv = inception_conv(in_node, 1, features, keep_prob, training)
                    wat_dw_h_convs[layer] = conv
                    wat_pools[layer] = max_pool(conv, 2)
                with tf.name_scope("opp"):
                    in_node = tf.reshape(x_image[..., 3],[batch_size, nx, ny, 1])
                    conv = inception_conv(in_node, 1, features, keep_prob, training)
                    opp_dw_h_convs[layer] = conv
                    opp_pools[layer] = max_pool(conv, 2)
            elif layer==1:
                with tf.name_scope("fat"):
                    in_node = tf.concat([fat_pools[0], inn_pools[0], wat_pools[0], opp_pools[0]], 3)
                    fat_inputs[layer] = in_node
                    conv = inception_conv(in_node, features_root*4, features, keep_prob, training)
                    fat_dw_h_convs[layer] = conv
                    fat_pools[layer] = max_pool(conv, 2)
                with tf.name_scope("inn"):
                    in_node = tf.concat([inn_pools[0], wat_pools[0], opp_pools[0], fat_pools[0]], 3)
                    inn_inputs[layer] = in_node
                    conv = inception_conv(in_node, features_root*4, features, keep_prob, training)
                    inn_dw_h_convs[layer] = conv
                    inn_pools[layer] = max_pool(conv, 2)
                with tf.name_scope("wat"):
                    in_node = tf.concat([wat_pools[0], opp_pools[0], fat_pools[0], inn_pools[0]], 3)
                    wat_inputs[layer] = in_node
                    conv = inception_conv(in_node, features_root*4, features, keep_prob, training)
                    wat_dw_h_convs[layer] = conv
                    wat_pools[layer] = max_pool(conv, 2)
                with tf.name_scope("opp"):
                    in_node = tf.concat([opp_pools[0], fat_pools[0], inn_pools[0], wat_pools[0]], 3)
                    opp_inputs[layer] = in_node
                    conv = inception_conv(in_node, features_root*4, features, keep_prob, training)
                    opp_dw_h_convs[layer] = conv
                    opp_pools[layer] = max_pool(conv, 2)
            elif layer==2:
                with tf.name_scope("fat"):
                    in_node = tf.concat([fat_pools[1], inn_pools[1], wat_pools[1], opp_pools[1]], 3)
                    tmp_node = cropCenter(fat_inputs[1], in_node)
                    in_node = tf.concat([in_node, tmp_node], 3)
                    fat_inputs[layer] = in_node
                    conv = inception_conv(in_node, features_root*12, features, keep_prob, training)
                    fat_dw_h_convs[layer] = conv
                    fat_pools[layer] = max_pool(conv, 2)
                with tf.name_scope("inn"):
                    in_node = tf.concat([inn_pools[1], wat_pools[1], opp_pools[1], fat_pools[1]], 3)
                    tmp_node = cropCenter(inn_inputs[1], in_node)
                    in_node = tf.concat([in_node, tmp_node], 3)
                    inn_inputs[layer] = in_node
                    conv = inception_conv(in_node, features_root*12, features, keep_prob, training)
                    inn_dw_h_convs[layer] = conv
                    inn_pools[layer] = max_pool(conv, 2)
                with tf.name_scope("wat"):
                    in_node = tf.concat([wat_pools[1], opp_pools[1], fat_pools[1], inn_pools[1]], 3)
                    tmp_node = cropCenter(wat_inputs[1], in_node)
                    in_node = tf.concat([in_node, tmp_node], 3)
                    wat_inputs[layer] = in_node
                    conv = inception_conv(in_node, features_root*12, features, keep_prob, training)
                    wat_dw_h_convs[layer] = conv
                    wat_pools[layer] = max_pool(conv, 2)
                with tf.name_scope("opp"):
                    in_node = tf.concat([opp_pools[1], fat_pools[1], inn_pools[1], wat_pools[1]], 3)
                    tmp_node = cropCenter(opp_inputs[1], in_node)
                    in_node = tf.concat([in_node, tmp_node], 3)
                    opp_inputs[layer] = in_node
                    conv = inception_conv(in_node, features_root*12, features, keep_prob, training)
                    opp_dw_h_convs[layer] = conv
                    opp_pools[layer] = max_pool(opp_dw_h_convs[layer], 2)
            elif layer==3:
                with tf.name_scope("fat"):
                    in_node = tf.concat([fat_pools[2], inn_pools[2], wat_pools[2], opp_pools[2]], 3)
                    tmp_node = cropCenter(fat_inputs[2], in_node)
                    in_node = tf.concat([in_node, tmp_node], 3)
                    fat_inputs[layer] = in_node
                    conv = inception_conv(in_node, features_root*28, features, keep_prob, training)
                    fat_dw_h_convs[layer] = conv
                    fat_pools[layer] = max_pool(conv, 2)
                with tf.name_scope("inn"):
                    in_node = tf.concat([inn_pools[2], wat_pools[2], opp_pools[2], fat_pools[2]], 3)
                    tmp_node = cropCenter(inn_inputs[2], in_node)
                    in_node = tf.concat([in_node, tmp_node], 3)
                    #inn_inputs[layer] = in_node
                    conv = inception_conv(in_node, features_root*28, features, keep_prob, training)
                    inn_dw_h_convs[layer] = conv
                    inn_pools[layer] = max_pool(conv, 2)
                with tf.name_scope("wat"):
                    in_node = tf.concat([wat_pools[2], opp_pools[2], fat_pools[2], inn_pools[2]], 3)
                    tmp_node = cropCenter(wat_inputs[2], in_node)
                    in_node = tf.concat([in_node, tmp_node], 3)
                    #wat_inputs[layer] = in_node
                    conv = inception_conv(in_node, features_root*28, features, keep_prob, training)
                    wat_dw_h_convs[layer] = conv
                    wat_pools[layer] = max_pool(conv, 2)
                with tf.name_scope("opp"):
                    in_node = tf.concat([opp_pools[2], fat_pools[2], inn_pools[2], wat_pools[2]], 3)
                    '''
                    tmp = tf.concat([opp_pools[1], fat_pools[1], inn_pools[1], wat_pools[1]], 3)
                    opp_inputs_1 = tf.concat([opp_pools[0], fat_pools[0], inn_pools[0], wat_pools[0]], 3)
                    tmp_node = cropCenter(opp_inputs_1, tmp)
                    opp_inputs_2 = tf.concat([tmp, tmp_node], 3)
                    '''
                    tmp_node = cropCenter(opp_inputs[2], in_node)
                    in_node = tf.concat([in_node, tmp_node], 3)
                    #opp_inputs[layer] = in_node
                    conv = inception_conv(in_node, features_root*28, features, keep_prob, training)
                    opp_dw_h_convs[layer] = conv
                    opp_pools[layer] = max_pool(conv, 2)
            elif layer==4:
                in_node = tf.concat([fat_pools[3], inn_pools[3], wat_pools[3], opp_pools[3]], 3)
                tmp_node = cropCenter(fat_inputs[3], in_node)
                in_node = tf.concat([in_node, tmp_node], 3)
                conv = inception_conv(in_node, features_root*60, features, keep_prob, training)
                up_h_convs[layer] = conv


    in_node = up_h_convs[layers-1]
    # up layers
    for layer in range(layers - 2, -1, -1):
        with tf.name_scope("up_conv_{}".format(str(layer))):
            features = 2 ** (layer + 1) * features_root
            h_deconv = deconv2d(in_node, features, features//2, training)
            h_deconv_concat = (h_deconv + fat_dw_h_convs[layer] + inn_dw_h_convs[layer] +\
                              wat_dw_h_convs[layer] + opp_dw_h_convs[layer])/5

            deconv[layer] = h_deconv_concat
            in_node = inception_conv(h_deconv_concat, features//2, features//2, keep_prob, training)
            up_h_convs[layer] = in_node

    stddev = np.sqrt(2 / (3 ** 2 * features_root))
    w = weight_variable([3, 3, features_root, 2], stddev, name="w")
    b = bias_variable([2], name="b")
    output_map = tf.nn.bias_add(tf.nn.conv2d(up_h_convs[0], w, strides=[1, 1, 1, 1], padding="SAME"), b)
    up_h_convs["out"] = output_map

    if summaries:
        with tf.name_scope("summaries"):
            for k in fat_pools.keys():
                tf.summary.image('summary_pool_%02d' % k, get_image_summary(fat_pools[k]))

            #for k in deconv.keys():
            #    tf.summary.image('summary_deconv_concat_%02d' % k, get_image_summary(deconv[k]))

            for k in fat_dw_h_convs.keys():
                tf.summary.histogram("dw_convolution_%02d" % k + '/activations', fat_dw_h_convs[k])

            for k in up_h_convs.keys():
                tf.summary.histogram("up_convolution_%s" % k + '/activations', up_h_convs[k])

    variables = []
    for w1, w2 in weights:
        variables.append(w1)
        variables.append(w2)

    for b1, b2 in biases:
        variables.append(b1)
        variables.append(b2)

    return output_map, variables

def create_edge_net(x, keep_prob, channels, n_class, layers=5, features_root=32, summaries=True, training=True):
    logging.info(
        "Layers {layers}, features {features}".format(
            layers=layers,
            features=features_root))

    # Placeholder for the input image
    with tf.name_scope("preprocessing"):
        nx = tf.shape(x)[1]
        ny = tf.shape(x)[2]
        x_image = tf.reshape(x, tf.stack([-1, nx, ny, channels]))
        in_node = x_image
        batch_size = tf.shape(x_image)[0]

    weights = []
    biases = []
    fat_inputs = OrderedDict();     inn_inputs = OrderedDict();     wat_inputs = OrderedDict();     opp_inputs = OrderedDict();
    fat_pools = OrderedDict();      inn_pools = OrderedDict();      wat_pools = OrderedDict();      opp_pools = OrderedDict()
    fat_dw_h_convs = OrderedDict(); inn_dw_h_convs = OrderedDict(); wat_dw_h_convs = OrderedDict(); opp_dw_h_convs = OrderedDict();
    deconv = OrderedDict()
    up_h_convs = OrderedDict()

    # down layers
    for layer in range(0, layers):
        with tf.name_scope("down_conv_{}".format(str(layer))):
            features = 2 ** layer * features_root
            if layer==0:
                with tf.name_scope("fat"):
                    in_node = tf.reshape(x_image[..., 0],[batch_size, nx, ny, 1])
                    conv = inception_conv(in_node, 1, features, keep_prob, training)
                    fat_dw_h_convs[layer] = conv
                    fat_pools[layer] = max_pool(conv, 2)
                with tf.name_scope("inn"):
                    in_node = tf.reshape(x_image[..., 1],[batch_size, nx, ny, 1])
                    conv = inception_conv(in_node, 1, features, keep_prob, training)
                    inn_dw_h_convs[layer] = conv
                    inn_pools[layer] = max_pool(conv, 2)
                with tf.name_scope("wat"):
                    in_node = tf.reshape(x_image[..., 2],[batch_size, nx, ny, 1])
                    conv = inception_conv(in_node, 1, features, keep_prob, training)
                    wat_dw_h_convs[layer] = conv
                    wat_pools[layer] = max_pool(conv, 2)
                with tf.name_scope("opp"):
                    in_node = tf.reshape(x_image[..., 3],[batch_size, nx, ny, 1])
                    conv = inception_conv(in_node, 1, features, keep_prob, training)
                    opp_dw_h_convs[layer] = conv
                    opp_pools[layer] = max_pool(conv, 2)
            elif layer==1:
                with tf.name_scope("fat"):
                    in_node = tf.concat([fat_pools[0], inn_pools[0], wat_pools[0], opp_pools[0]], 3)
                    fat_inputs[layer] = in_node
                    conv = inception_conv(in_node, features_root*4, features, keep_prob, training)
                    fat_dw_h_convs[layer] = conv
                    fat_pools[layer] = max_pool(conv, 2)
                with tf.name_scope("inn"):
                    in_node = tf.concat([inn_pools[0], wat_pools[0], opp_pools[0], fat_pools[0]], 3)
                    inn_inputs[layer] = in_node
                    conv = inception_conv(in_node, features_root*4, features, keep_prob, training)
                    inn_dw_h_convs[layer] = conv
                    inn_pools[layer] = max_pool(conv, 2)
                with tf.name_scope("wat"):
                    in_node = tf.concat([wat_pools[0], opp_pools[0], fat_pools[0], inn_pools[0]], 3)
                    wat_inputs[layer] = in_node
                    conv = inception_conv(in_node, features_root*4, features, keep_prob, training)
                    wat_dw_h_convs[layer] = conv
                    wat_pools[layer] = max_pool(conv, 2)
                with tf.name_scope("opp"):
                    in_node = tf.concat([opp_pools[0], fat_pools[0], inn_pools[0], wat_pools[0]], 3)
                    opp_inputs[layer] = in_node
                    conv = inception_conv(in_node, features_root*4, features, keep_prob, training)
                    opp_dw_h_convs[layer] = conv
                    opp_pools[layer] = max_pool(conv, 2)
            elif layer==2:
                with tf.name_scope("fat"):
                    in_node = tf.concat([fat_pools[1], inn_pools[1], wat_pools[1], opp_pools[1]], 3)
                    tmp_node = cropCenter(fat_inputs[1], in_node)
                    in_node = tf.concat([in_node, tmp_node], 3)
                    fat_inputs[layer] = in_node
                    conv = inception_conv(in_node, features_root*12, features, keep_prob, training)
                    fat_dw_h_convs[layer] = conv
                    fat_pools[layer] = max_pool(conv, 2)
                with tf.name_scope("inn"):
                    in_node = tf.concat([inn_pools[1], wat_pools[1], opp_pools[1], fat_pools[1]], 3)
                    tmp_node = cropCenter(inn_inputs[1], in_node)
                    in_node = tf.concat([in_node, tmp_node], 3)
                    inn_inputs[layer] = in_node
                    conv = inception_conv(in_node, features_root*12, features, keep_prob, training)
                    inn_dw_h_convs[layer] = conv
                    inn_pools[layer] = max_pool(conv, 2)
                with tf.name_scope("wat"):
                    in_node = tf.concat([wat_pools[1], opp_pools[1], fat_pools[1], inn_pools[1]], 3)
                    tmp_node = cropCenter(wat_inputs[1], in_node)
                    in_node = tf.concat([in_node, tmp_node], 3)
                    wat_inputs[layer] = in_node
                    conv = inception_conv(in_node, features_root*12, features, keep_prob, training)
                    wat_dw_h_convs[layer] = conv
                    wat_pools[layer] = max_pool(conv, 2)
                with tf.name_scope("opp"):
                    in_node = tf.concat([opp_pools[1], fat_pools[1], inn_pools[1], wat_pools[1]], 3)
                    tmp_node = cropCenter(opp_inputs[1], in_node)
                    in_node = tf.concat([in_node, tmp_node], 3)
                    opp_inputs[layer] = in_node
                    conv = inception_conv(in_node, features_root*12, features, keep_prob, training)
                    opp_dw_h_convs[layer] = conv
                    opp_pools[layer] = max_pool(opp_dw_h_convs[layer], 2)
            elif layer==3:
                with tf.name_scope("fat"):
                    in_node = tf.concat([fat_pools[2], inn_pools[2], wat_pools[2], opp_pools[2]], 3)
                    tmp_node = cropCenter(fat_inputs[2], in_node)
                    in_node = tf.concat([in_node, tmp_node], 3)
                    fat_inputs[layer] = in_node
                    conv = inception_conv(in_node, features_root*28, features, keep_prob, training)
                    fat_dw_h_convs[layer] = conv
                    fat_pools[layer] = max_pool(conv, 2)
                with tf.name_scope("inn"):
                    in_node = tf.concat([inn_pools[2], wat_pools[2], opp_pools[2], fat_pools[2]], 3)
                    tmp_node = cropCenter(inn_inputs[2], in_node)
                    in_node = tf.concat([in_node, tmp_node], 3)
                    #inn_inputs[layer] = in_node
                    conv = inception_conv(in_node, features_root*28, features, keep_prob, training)
                    inn_dw_h_convs[layer] = conv
                    inn_pools[layer] = max_pool(conv, 2)
                with tf.name_scope("wat"):
                    in_node = tf.concat([wat_pools[2], opp_pools[2], fat_pools[2], inn_pools[2]], 3)
                    tmp_node = cropCenter(wat_inputs[2], in_node)
                    in_node = tf.concat([in_node, tmp_node], 3)
                    #wat_inputs[layer] = in_node
                    conv = inception_conv(in_node, features_root*28, features, keep_prob, training)
                    wat_dw_h_convs[layer] = conv
                    wat_pools[layer] = max_pool(conv, 2)
                with tf.name_scope("opp"):
                    in_node = tf.concat([opp_pools[2], fat_pools[2], inn_pools[2], wat_pools[2]], 3)
                    '''
                    tmp = tf.concat([opp_pools[1], fat_pools[1], inn_pools[1], wat_pools[1]], 3)
                    opp_inputs_1 = tf.concat([opp_pools[0], fat_pools[0], inn_pools[0], wat_pools[0]], 3)
                    tmp_node = cropCenter(opp_inputs_1, tmp)
                    opp_inputs_2 = tf.concat([tmp, tmp_node], 3)
                    '''
                    tmp_node = cropCenter(opp_inputs[2], in_node)
                    in_node = tf.concat([in_node, tmp_node], 3)
                    #opp_inputs[layer] = in_node
                    conv = inception_conv(in_node, features_root*28, features, keep_prob, training)
                    opp_dw_h_convs[layer] = conv
                    opp_pools[layer] = max_pool(conv, 2)
            elif layer==4:
                in_node = tf.concat([fat_pools[3], inn_pools[3], wat_pools[3], opp_pools[3]], 3)
                tmp_node = cropCenter(fat_inputs[3], in_node)
                in_node = tf.concat([in_node, tmp_node], 3)
                conv = inception_conv(in_node, features_root*60, features, keep_prob, training)
                up_h_convs[layer] = conv

    in_node = up_h_convs[layers-1]
    # up layers
    for layer in range(layers - 2, -1, -1):
        with tf.name_scope("up_conv_{}".format(str(layer))):
            features = 2 ** (layer + 1) * features_root
            h_deconv = deconv2d(in_node, features, features//2, training)
            h_deconv_concat = (h_deconv + fat_dw_h_convs[layer] + inn_dw_h_convs[layer] +\
                              wat_dw_h_convs[layer] + opp_dw_h_convs[layer])/5

            deconv[layer] = h_deconv_concat
            in_node = inception_conv(h_deconv_concat, features//2, features//2, keep_prob, training)
            up_h_convs[layer] = in_node

    # output
    stddev = np.sqrt(2 / (3 ** 2 * features_root))
    w = weight_variable([3, 3, features_root, 2], stddev, name="w")
    b = bias_variable([2], name="b")
    output_map = tf.nn.bias_add(tf.nn.conv2d(up_h_convs[0], w, strides=[1, 1, 1, 1], padding="SAME"), b)
    up_h_convs["out"] = output_map

    for layer in range(layers - 2, 0, -1):
        with tf.name_scope("output_{}".format(str(layer))):
            in_node = up_h_convs[layer]
            conv = conv2d_2(in_node, features_root*2**layer, 2, keep_prob)
            deconv = deconv2d_2(conv, 2, 2, 2**layer, keep_prob)
            up_h_convs["out_{}".format(layer)] = deconv

    if summaries:
        with tf.name_scope("summaries"):
            for k in fat_pools.keys():
                tf.summary.image('summary_pool_%02d' % k, get_image_summary(fat_pools[k]))

            #for k in deconv.keys():
            #    tf.summary.image('summary_deconv_concat_%02d' % k, get_image_summary(deconv[k]))

            for k in fat_dw_h_convs.keys():
                tf.summary.histogram("dw_convolution_%02d" % k + '/activations', fat_dw_h_convs[k])

    variables = []
    for w1, w2 in weights:
        variables.append(w1)
        variables.append(w2)

    for b1, b2 in biases:
        variables.append(b1)
        variables.append(b2)

    return [output_map, up_h_convs["out_1"], up_h_convs["out_2"], up_h_convs["out_3"]], variables

def create_edge_net_3(x, keep_prob, channels, n_class, layers=5, features_root=32, summaries=True, training=True):
    # delete  up_h_convs["out_3"]
    logging.info(
        "Layers {layers}, features {features}".format(
            layers=layers,
            features=features_root))

    # Placeholder for the input image
    with tf.name_scope("preprocessing"):
        nx = tf.shape(x)[1]
        ny = tf.shape(x)[2]
        x_image = tf.reshape(x, tf.stack([-1, nx, ny, channels]))
        in_node = x_image
        batch_size = tf.shape(x_image)[0]

    weights = []
    biases = []
    fat_inputs = OrderedDict();     inn_inputs = OrderedDict();     wat_inputs = OrderedDict();     opp_inputs = OrderedDict();
    fat_pools = OrderedDict();      inn_pools = OrderedDict();      wat_pools = OrderedDict();      opp_pools = OrderedDict()
    fat_dw_h_convs = OrderedDict(); inn_dw_h_convs = OrderedDict(); wat_dw_h_convs = OrderedDict(); opp_dw_h_convs = OrderedDict();
    deconv = OrderedDict()
    up_h_convs = OrderedDict()

    # down layers
    for layer in range(0, layers):
        with tf.name_scope("down_conv_{}".format(str(layer))):
            features = 2 ** layer * features_root
            if layer==0:
                with tf.name_scope("fat"):
                    in_node = tf.reshape(x_image[..., 0],[batch_size, nx, ny, 1])
                    conv = inception_conv(in_node, 1, features, keep_prob, training)
                    fat_dw_h_convs[layer] = conv
                    fat_pools[layer] = max_pool(conv, 2)
                with tf.name_scope("inn"):
                    in_node = tf.reshape(x_image[..., 1],[batch_size, nx, ny, 1])
                    conv = inception_conv(in_node, 1, features, keep_prob, training)
                    inn_dw_h_convs[layer] = conv
                    inn_pools[layer] = max_pool(conv, 2)
                with tf.name_scope("wat"):
                    in_node = tf.reshape(x_image[..., 2],[batch_size, nx, ny, 1])
                    conv = inception_conv(in_node, 1, features, keep_prob, training)
                    wat_dw_h_convs[layer] = conv
                    wat_pools[layer] = max_pool(conv, 2)
                with tf.name_scope("opp"):
                    in_node = tf.reshape(x_image[..., 3],[batch_size, nx, ny, 1])
                    conv = inception_conv(in_node, 1, features, keep_prob, training)
                    opp_dw_h_convs[layer] = conv
                    opp_pools[layer] = max_pool(conv, 2)
            elif layer==1:
                with tf.name_scope("fat"):
                    in_node = tf.concat([fat_pools[0], inn_pools[0], wat_pools[0], opp_pools[0]], 3)
                    fat_inputs[layer] = in_node
                    conv = inception_conv(in_node, features_root*4, features, keep_prob, training)
                    fat_dw_h_convs[layer] = conv
                    fat_pools[layer] = max_pool(conv, 2)
                with tf.name_scope("inn"):
                    in_node = tf.concat([inn_pools[0], wat_pools[0], opp_pools[0], fat_pools[0]], 3)
                    inn_inputs[layer] = in_node
                    conv = inception_conv(in_node, features_root*4, features, keep_prob, training)
                    inn_dw_h_convs[layer] = conv
                    inn_pools[layer] = max_pool(conv, 2)
                with tf.name_scope("wat"):
                    in_node = tf.concat([wat_pools[0], opp_pools[0], fat_pools[0], inn_pools[0]], 3)
                    wat_inputs[layer] = in_node
                    conv = inception_conv(in_node, features_root*4, features, keep_prob, training)
                    wat_dw_h_convs[layer] = conv
                    wat_pools[layer] = max_pool(conv, 2)
                with tf.name_scope("opp"):
                    in_node = tf.concat([opp_pools[0], fat_pools[0], inn_pools[0], wat_pools[0]], 3)
                    opp_inputs[layer] = in_node
                    conv = inception_conv(in_node, features_root*4, features, keep_prob, training)
                    opp_dw_h_convs[layer] = conv
                    opp_pools[layer] = max_pool(conv, 2)
            elif layer==2:
                with tf.name_scope("fat"):
                    in_node = tf.concat([fat_pools[1], inn_pools[1], wat_pools[1], opp_pools[1]], 3)
                    tmp_node = cropCenter(fat_inputs[1], in_node)
                    in_node = tf.concat([in_node, tmp_node], 3)
                    fat_inputs[layer] = in_node
                    conv = inception_conv(in_node, features_root*12, features, keep_prob, training)
                    fat_dw_h_convs[layer] = conv
                    fat_pools[layer] = max_pool(conv, 2)
                with tf.name_scope("inn"):
                    in_node = tf.concat([inn_pools[1], wat_pools[1], opp_pools[1], fat_pools[1]], 3)
                    tmp_node = cropCenter(inn_inputs[1], in_node)
                    in_node = tf.concat([in_node, tmp_node], 3)
                    inn_inputs[layer] = in_node
                    conv = inception_conv(in_node, features_root*12, features, keep_prob, training)
                    inn_dw_h_convs[layer] = conv
                    inn_pools[layer] = max_pool(conv, 2)
                with tf.name_scope("wat"):
                    in_node = tf.concat([wat_pools[1], opp_pools[1], fat_pools[1], inn_pools[1]], 3)
                    tmp_node = cropCenter(wat_inputs[1], in_node)
                    in_node = tf.concat([in_node, tmp_node], 3)
                    wat_inputs[layer] = in_node
                    conv = inception_conv(in_node, features_root*12, features, keep_prob, training)
                    wat_dw_h_convs[layer] = conv
                    wat_pools[layer] = max_pool(conv, 2)
                with tf.name_scope("opp"):
                    in_node = tf.concat([opp_pools[1], fat_pools[1], inn_pools[1], wat_pools[1]], 3)
                    tmp_node = cropCenter(opp_inputs[1], in_node)
                    in_node = tf.concat([in_node, tmp_node], 3)
                    opp_inputs[layer] = in_node
                    conv = inception_conv(in_node, features_root*12, features, keep_prob, training)
                    opp_dw_h_convs[layer] = conv
                    opp_pools[layer] = max_pool(conv, 2)
            elif layer==3:
                with tf.name_scope("fat"):
                    in_node = tf.concat([fat_pools[2], inn_pools[2], wat_pools[2], opp_pools[2]], 3)
                    tmp_node = cropCenter(fat_inputs[2], in_node)
                    in_node = tf.concat([in_node, tmp_node], 3)
                    fat_inputs[layer] = in_node
                    conv = inception_conv(in_node, features_root*28, features, keep_prob, training)
                    fat_dw_h_convs[layer] = conv
                    fat_pools[layer] = max_pool(conv, 2)
                with tf.name_scope("inn"):
                    in_node = tf.concat([inn_pools[2], wat_pools[2], opp_pools[2], fat_pools[2]], 3)
                    tmp_node = cropCenter(inn_inputs[2], in_node)
                    in_node = tf.concat([in_node, tmp_node], 3)
                    #inn_inputs[layer] = in_node
                    conv = inception_conv(in_node, features_root*28, features, keep_prob, training)
                    inn_dw_h_convs[layer] = conv
                    inn_pools[layer] = max_pool(conv, 2)
                with tf.name_scope("wat"):
                    in_node = tf.concat([wat_pools[2], opp_pools[2], fat_pools[2], inn_pools[2]], 3)
                    tmp_node = cropCenter(wat_inputs[2], in_node)
                    in_node = tf.concat([in_node, tmp_node], 3)
                    #wat_inputs[layer] = in_node
                    conv = inception_conv(in_node, features_root*28, features, keep_prob, training)
                    wat_dw_h_convs[layer] = conv
                    wat_pools[layer] = max_pool(conv, 2)
                with tf.name_scope("opp"):
                    in_node = tf.concat([opp_pools[2], fat_pools[2], inn_pools[2], wat_pools[2]], 3)
                    tmp_node = cropCenter(opp_inputs[2], in_node)
                    in_node = tf.concat([in_node, tmp_node], 3)
                    #opp_inputs[layer] = in_node
                    conv = inception_conv(in_node, features_root*28, features, keep_prob, training)
                    opp_dw_h_convs[layer] = conv
                    opp_pools[layer] = max_pool(conv, 2)
            elif layer==4:
                in_node = tf.concat([fat_pools[3], inn_pools[3], wat_pools[3], opp_pools[3]], 3)
                tmp_node = cropCenter(fat_inputs[3], in_node)
                in_node = tf.concat([in_node, tmp_node], 3)
                conv = inception_conv(in_node, features_root*60, features, keep_prob, training)
                up_h_convs[layer] = conv

    in_node = up_h_convs[layers-1]
    # up layers
    for layer in range(layers - 2, -1, -1):
        with tf.name_scope("up_conv_{}".format(str(layer))):
            features = 2 ** (layer + 1) * features_root
            h_deconv = deconv2d(in_node, features, features//2, training)
            h_deconv_concat = (h_deconv + fat_dw_h_convs[layer] + inn_dw_h_convs[layer] +\
                              wat_dw_h_convs[layer] + opp_dw_h_convs[layer])/5

            deconv[layer] = h_deconv_concat
            in_node = inception_conv(h_deconv_concat, features//2, features//2, keep_prob, training)
            up_h_convs[layer] = in_node

    # output
    stddev = np.sqrt(2 / (3 ** 2 * features_root))
    w = weight_variable([3, 3, features_root, 2], stddev, name="w")
    b = bias_variable([2], name="b")
    up_h_convs["out"] = tf.nn.bias_add(tf.nn.conv2d(up_h_convs[0], w, strides=[1, 1, 1, 1], padding="SAME"), b)

    # RCF
    for layer in range(2, 0, -1):
        with tf.name_scope("output_{}".format(str(layer))):
            in_node = up_h_convs[layer]
            conv = conv2d_2(in_node, features_root*2**layer, 2, keep_prob)
            deconv = deconv2d_2(conv, 2, 2, 2**layer, keep_prob)
            up_h_convs["out_{}".format(layer)] = deconv
    in_node = tf.concat([up_h_convs["out"], up_h_convs["out_1"], up_h_convs["out_2"]], 3)
    w_out = weight_variable([1, 1, 6, 2], stddev, name="w_out")
    b_out = bias_variable([2], name="b_out")
    output_map = tf.nn.bias_add(tf.nn.conv2d(in_node, w_out, strides=[1, 1, 1, 1], padding="SAME"), b_out)

    if summaries:
        with tf.name_scope("summaries"):
            for k in up_h_convs.keys():
                tf.summary.image('up_h_convs_%s' % k, get_image_summary(up_h_convs[k]))
            tf.summary.image("output_map", get_image_summary(output_map))

    variables = []
    for w1, w2 in weights:
        variables.append(w1)
        variables.append(w2)

    for b1, b2 in biases:
        variables.append(b1)
        variables.append(b2)

    return [output_map, up_h_convs["out"], up_h_convs["out_1"], up_h_convs["out_2"]], variables

def create_edge_net_4(x, keep_prob, channels, n_class, layers=5, features_root=32, summaries=True, training=True):
    # delete  up_h_convs["out_2"]
    logging.info(
        "Layers {layers}, features {features}".format(
            layers=layers,
            features=features_root))

    # Placeholder for the input image
    with tf.name_scope("preprocessing"):
        nx = tf.shape(x)[1]
        ny = tf.shape(x)[2]
        x_image = tf.reshape(x, tf.stack([-1, nx, ny, channels]))
        in_node = x_image
        batch_size = tf.shape(x_image)[0]

    weights = []
    biases = []
    fat_inputs = OrderedDict();     inn_inputs = OrderedDict();     wat_inputs = OrderedDict();     opp_inputs = OrderedDict();
    fat_pools = OrderedDict();      inn_pools = OrderedDict();      wat_pools = OrderedDict();      opp_pools = OrderedDict()
    fat_dw_h_convs = OrderedDict(); inn_dw_h_convs = OrderedDict(); wat_dw_h_convs = OrderedDict(); opp_dw_h_convs = OrderedDict();
    deconv = OrderedDict()
    up_h_convs = OrderedDict()

    # down layers
    for layer in range(0, layers):
        with tf.name_scope("down_conv_{}".format(str(layer))):
            features = 2 ** layer * features_root
            if layer==0:
                with tf.name_scope("fat"):
                    in_node = tf.reshape(x_image[..., 0],[batch_size, nx, ny, 1])
                    conv = inception_conv(in_node, 1, features, keep_prob, training)
                    fat_dw_h_convs[layer] = conv
                    fat_pools[layer] = max_pool(conv, 2)
                with tf.name_scope("inn"):
                    in_node = tf.reshape(x_image[..., 1],[batch_size, nx, ny, 1])
                    conv = inception_conv(in_node, 1, features, keep_prob, training)
                    inn_dw_h_convs[layer] = conv
                    inn_pools[layer] = max_pool(conv, 2)
                with tf.name_scope("wat"):
                    in_node = tf.reshape(x_image[..., 2],[batch_size, nx, ny, 1])
                    conv = inception_conv(in_node, 1, features, keep_prob, training)
                    wat_dw_h_convs[layer] = conv
                    wat_pools[layer] = max_pool(conv, 2)
                with tf.name_scope("opp"):
                    in_node = tf.reshape(x_image[..., 3],[batch_size, nx, ny, 1])
                    conv = inception_conv(in_node, 1, features, keep_prob, training)
                    opp_dw_h_convs[layer] = conv
                    opp_pools[layer] = max_pool(conv, 2)
            elif layer==1:
                with tf.name_scope("fat"):
                    in_node = tf.concat([fat_pools[0], inn_pools[0], wat_pools[0], opp_pools[0]], 3)
                    fat_inputs[layer] = in_node
                    conv = inception_conv(in_node, features_root*4, features, keep_prob, training)
                    fat_dw_h_convs[layer] = conv
                    fat_pools[layer] = max_pool(conv, 2)
                with tf.name_scope("inn"):
                    in_node = tf.concat([inn_pools[0], wat_pools[0], opp_pools[0], fat_pools[0]], 3)
                    inn_inputs[layer] = in_node
                    conv = inception_conv(in_node, features_root*4, features, keep_prob, training)
                    inn_dw_h_convs[layer] = conv
                    inn_pools[layer] = max_pool(conv, 2)
                with tf.name_scope("wat"):
                    in_node = tf.concat([wat_pools[0], opp_pools[0], fat_pools[0], inn_pools[0]], 3)
                    wat_inputs[layer] = in_node
                    conv = inception_conv(in_node, features_root*4, features, keep_prob, training)
                    wat_dw_h_convs[layer] = conv
                    wat_pools[layer] = max_pool(conv, 2)
                with tf.name_scope("opp"):
                    in_node = tf.concat([opp_pools[0], fat_pools[0], inn_pools[0], wat_pools[0]], 3)
                    opp_inputs[layer] = in_node
                    conv = inception_conv(in_node, features_root*4, features, keep_prob, training)
                    opp_dw_h_convs[layer] = conv
                    opp_pools[layer] = max_pool(conv, 2)
            elif layer==2:
                with tf.name_scope("fat"):
                    in_node = tf.concat([fat_pools[1], inn_pools[1], wat_pools[1], opp_pools[1]], 3)
                    tmp_node = cropCenter(fat_inputs[1], in_node)
                    in_node = tf.concat([in_node, tmp_node], 3)
                    fat_inputs[layer] = in_node
                    conv = inception_conv(in_node, features_root*12, features, keep_prob, training)
                    fat_dw_h_convs[layer] = conv
                    fat_pools[layer] = max_pool(conv, 2)
                with tf.name_scope("inn"):
                    in_node = tf.concat([inn_pools[1], wat_pools[1], opp_pools[1], fat_pools[1]], 3)
                    tmp_node = cropCenter(inn_inputs[1], in_node)
                    in_node = tf.concat([in_node, tmp_node], 3)
                    inn_inputs[layer] = in_node
                    conv = inception_conv(in_node, features_root*12, features, keep_prob, training)
                    inn_dw_h_convs[layer] = conv
                    inn_pools[layer] = max_pool(conv, 2)
                with tf.name_scope("wat"):
                    in_node = tf.concat([wat_pools[1], opp_pools[1], fat_pools[1], inn_pools[1]], 3)
                    tmp_node = cropCenter(wat_inputs[1], in_node)
                    in_node = tf.concat([in_node, tmp_node], 3)
                    wat_inputs[layer] = in_node
                    conv = inception_conv(in_node, features_root*12, features, keep_prob, training)
                    wat_dw_h_convs[layer] = conv
                    wat_pools[layer] = max_pool(conv, 2)
                with tf.name_scope("opp"):
                    in_node = tf.concat([opp_pools[1], fat_pools[1], inn_pools[1], wat_pools[1]], 3)
                    tmp_node = cropCenter(opp_inputs[1], in_node)
                    in_node = tf.concat([in_node, tmp_node], 3)
                    opp_inputs[layer] = in_node
                    conv = inception_conv(in_node, features_root*12, features, keep_prob, training)
                    opp_dw_h_convs[layer] = conv
                    opp_pools[layer] = max_pool(conv, 2)
            elif layer==3:
                with tf.name_scope("fat"):
                    in_node = tf.concat([fat_pools[2], inn_pools[2], wat_pools[2], opp_pools[2]], 3)
                    tmp_node = cropCenter(fat_inputs[2], in_node)
                    in_node = tf.concat([in_node, tmp_node], 3)
                    fat_inputs[layer] = in_node
                    conv = inception_conv(in_node, features_root*28, features, keep_prob, training)
                    fat_dw_h_convs[layer] = conv
                    fat_pools[layer] = max_pool(conv, 2)
                with tf.name_scope("inn"):
                    in_node = tf.concat([inn_pools[2], wat_pools[2], opp_pools[2], fat_pools[2]], 3)
                    tmp_node = cropCenter(inn_inputs[2], in_node)
                    in_node = tf.concat([in_node, tmp_node], 3)
                    #inn_inputs[layer] = in_node
                    conv = inception_conv(in_node, features_root*28, features, keep_prob, training)
                    inn_dw_h_convs[layer] = conv
                    inn_pools[layer] = max_pool(conv, 2)
                with tf.name_scope("wat"):
                    in_node = tf.concat([wat_pools[2], opp_pools[2], fat_pools[2], inn_pools[2]], 3)
                    tmp_node = cropCenter(wat_inputs[2], in_node)
                    in_node = tf.concat([in_node, tmp_node], 3)
                    #wat_inputs[layer] = in_node
                    conv = inception_conv(in_node, features_root*28, features, keep_prob, training)
                    wat_dw_h_convs[layer] = conv
                    wat_pools[layer] = max_pool(conv, 2)
                with tf.name_scope("opp"):
                    in_node = tf.concat([opp_pools[2], fat_pools[2], inn_pools[2], wat_pools[2]], 3)
                    tmp_node = cropCenter(opp_inputs[2], in_node)
                    in_node = tf.concat([in_node, tmp_node], 3)
                    #opp_inputs[layer] = in_node
                    conv = inception_conv(in_node, features_root*28, features, keep_prob, training)
                    opp_dw_h_convs[layer] = conv
                    opp_pools[layer] = max_pool(conv, 2)
            elif layer==4:
                in_node = tf.concat([fat_pools[3], inn_pools[3], wat_pools[3], opp_pools[3]], 3)
                tmp_node = cropCenter(fat_inputs[3], in_node)
                in_node = tf.concat([in_node, tmp_node], 3)
                conv = inception_conv(in_node, features_root*60, features, keep_prob, training)
                up_h_convs[layer] = conv

    in_node = up_h_convs[layers-1]
    # up layers
    for layer in range(layers - 2, -1, -1):
        with tf.name_scope("up_conv_{}".format(str(layer))):
            features = 2 ** (layer + 1) * features_root
            h_deconv = deconv2d(in_node, features, features//2, training)
            h_deconv_concat = (h_deconv + fat_dw_h_convs[layer] + inn_dw_h_convs[layer] +\
                              wat_dw_h_convs[layer] + opp_dw_h_convs[layer])/5

            deconv[layer] = h_deconv_concat
            in_node = inception_conv(h_deconv_concat, features//2, features//2, keep_prob, training)
            up_h_convs[layer] = in_node

    # output
    stddev = np.sqrt(2 / (3 ** 2 * features_root))
    w = weight_variable([3, 3, features_root, 2], stddev, name="w")
    b = bias_variable([2], name="b")
    up_h_convs["out"] = tf.nn.bias_add(tf.nn.conv2d(up_h_convs[0], w, strides=[1, 1, 1, 1], padding="SAME"), b)

    # RCF
    for layer in range(1, 0, -1):
        with tf.name_scope("output_{}".format(str(layer))):
            in_node = up_h_convs[layer]
            conv = conv2d_2(in_node, features_root*2**layer, 2, keep_prob)
            deconv = deconv2d_2(conv, 2, 2, 2**layer, keep_prob)
            up_h_convs["out_{}".format(layer)] = deconv
    in_node = tf.concat([up_h_convs["out"], up_h_convs["out_1"]], 3)
    w_out = weight_variable([1, 1, 4, 2], stddev, name="w_out")
    b_out = bias_variable([2], name="b_out")
    output_map = tf.nn.bias_add(tf.nn.conv2d(in_node, w_out, strides=[1, 1, 1, 1], padding="SAME"), b_out)

    if summaries:
        with tf.name_scope("summaries"):
            for k in up_h_convs.keys():
                tf.summary.image('up_h_convs_%s' % k, get_image_summary(up_h_convs[k]))
            tf.summary.image("output_map", get_image_summary(output_map))

    variables = []
    for w1, w2 in weights:
        variables.append(w1)
        variables.append(w2)

    for b1, b2 in biases:
        variables.append(b1)
        variables.append(b2)

    return [output_map, up_h_convs["out"], up_h_convs["out_1"]], variables

def edge_net_4layer(x, keep_prob, channels, n_class, layers=4, features_root=32, summaries=True, training=True):
    logging.info(
        "Layers {layers}, features {features}".format(
            layers=layers,
            features=features_root))

    # Placeholder for the input image
    with tf.name_scope("preprocessing"):
        nx = tf.shape(x)[1]
        ny = tf.shape(x)[2]
        x_image = tf.reshape(x, tf.stack([-1, nx, ny, channels]))
        in_node = x_image
        batch_size = tf.shape(x_image)[0]

    weights = []
    biases = []
    fat_inputs = OrderedDict();     inn_inputs = OrderedDict();     wat_inputs = OrderedDict();     opp_inputs = OrderedDict();
    fat_pools = OrderedDict();      inn_pools = OrderedDict();      wat_pools = OrderedDict();      opp_pools = OrderedDict()
    fat_dw_h_convs = OrderedDict(); inn_dw_h_convs = OrderedDict(); wat_dw_h_convs = OrderedDict(); opp_dw_h_convs = OrderedDict();
    deconv = OrderedDict()
    up_h_convs = OrderedDict()

    # down layers
    for layer in range(0, 4):
        with tf.name_scope("down_conv_{}".format(str(layer))):
            features = 2 ** layer * features_root
            if layer==0:
                with tf.name_scope("fat"):
                    in_node = tf.reshape(x_image[..., 0],[batch_size, nx, ny, 1])
                    conv = inception_conv(in_node, 1, features, keep_prob, training)
                    fat_dw_h_convs[layer] = conv
                    fat_pools[layer] = max_pool(conv, 2)
                with tf.name_scope("inn"):
                    in_node = tf.reshape(x_image[..., 1],[batch_size, nx, ny, 1])
                    conv = inception_conv(in_node, 1, features, keep_prob, training)
                    inn_dw_h_convs[layer] = conv
                    inn_pools[layer] = max_pool(conv, 2)
                with tf.name_scope("wat"):
                    in_node = tf.reshape(x_image[..., 2],[batch_size, nx, ny, 1])
                    conv = inception_conv(in_node, 1, features, keep_prob, training)
                    wat_dw_h_convs[layer] = conv
                    wat_pools[layer] = max_pool(conv, 2)
                with tf.name_scope("opp"):
                    in_node = tf.reshape(x_image[..., 3],[batch_size, nx, ny, 1])
                    conv = inception_conv(in_node, 1, features, keep_prob, training)
                    opp_dw_h_convs[layer] = conv
                    opp_pools[layer] = max_pool(conv, 2)
            elif layer==1:
                with tf.name_scope("fat"):
                    in_node = tf.concat([fat_pools[0], inn_pools[0], wat_pools[0], opp_pools[0]], 3)
                    fat_inputs[layer] = in_node
                    conv = inception_conv(in_node, features_root*4, features, keep_prob, training)
                    fat_dw_h_convs[layer] = conv
                    fat_pools[layer] = max_pool(conv, 2)
                with tf.name_scope("inn"):
                    in_node = tf.concat([inn_pools[0], wat_pools[0], opp_pools[0], fat_pools[0]], 3)
                    inn_inputs[layer] = in_node
                    conv = inception_conv(in_node, features_root*4, features, keep_prob, training)
                    inn_dw_h_convs[layer] = conv
                    inn_pools[layer] = max_pool(conv, 2)
                with tf.name_scope("wat"):
                    in_node = tf.concat([wat_pools[0], opp_pools[0], fat_pools[0], inn_pools[0]], 3)
                    wat_inputs[layer] = in_node
                    conv = inception_conv(in_node, features_root*4, features, keep_prob, training)
                    wat_dw_h_convs[layer] = conv
                    wat_pools[layer] = max_pool(conv, 2)
                with tf.name_scope("opp"):
                    in_node = tf.concat([opp_pools[0], fat_pools[0], inn_pools[0], wat_pools[0]], 3)
                    opp_inputs[layer] = in_node
                    conv = inception_conv(in_node, features_root*4, features, keep_prob, training)
                    opp_dw_h_convs[layer] = conv
                    opp_pools[layer] = max_pool(conv, 2)
            elif layer==2:
                with tf.name_scope("fat"):
                    in_node = tf.concat([fat_pools[1], inn_pools[1], wat_pools[1], opp_pools[1]], 3)
                    tmp_node = cropCenter(fat_inputs[1], in_node)
                    in_node = tf.concat([in_node, tmp_node], 3)
                    fat_inputs[layer] = in_node
                    conv = inception_conv(in_node, features_root*12, features, keep_prob, training)
                    fat_dw_h_convs[layer] = conv
                    fat_pools[layer] = max_pool(conv, 2)
                with tf.name_scope("inn"):
                    in_node = tf.concat([inn_pools[1], wat_pools[1], opp_pools[1], fat_pools[1]], 3)
                    tmp_node = cropCenter(inn_inputs[1], in_node)
                    in_node = tf.concat([in_node, tmp_node], 3)
                    inn_inputs[layer] = in_node
                    conv = inception_conv(in_node, features_root*12, features, keep_prob, training)
                    inn_dw_h_convs[layer] = conv
                    inn_pools[layer] = max_pool(conv, 2)
                with tf.name_scope("wat"):
                    in_node = tf.concat([wat_pools[1], opp_pools[1], fat_pools[1], inn_pools[1]], 3)
                    tmp_node = cropCenter(wat_inputs[1], in_node)
                    in_node = tf.concat([in_node, tmp_node], 3)
                    wat_inputs[layer] = in_node
                    conv = inception_conv(in_node, features_root*12, features, keep_prob, training)
                    wat_dw_h_convs[layer] = conv
                    wat_pools[layer] = max_pool(conv, 2)
                with tf.name_scope("opp"):
                    in_node = tf.concat([opp_pools[1], fat_pools[1], inn_pools[1], wat_pools[1]], 3)
                    tmp_node = cropCenter(opp_inputs[1], in_node)
                    in_node = tf.concat([in_node, tmp_node], 3)
                    opp_inputs[layer] = in_node
                    conv = inception_conv(in_node, features_root*12, features, keep_prob, training)
                    opp_dw_h_convs[layer] = conv
                    opp_pools[layer] = max_pool(conv, 2)
            elif layer==3:
                with tf.name_scope("fat"):
                    in_node = tf.concat([fat_pools[2], inn_pools[2], wat_pools[2], opp_pools[2]], 3)
                    tmp_node = cropCenter(fat_inputs[2], in_node)
                    in_node = tf.concat([in_node, tmp_node], 3)
                    conv = inception_conv(in_node, features_root*28, features, keep_prob, training)
                    up_h_convs[layer] = conv

    in_node = up_h_convs[4-1]
    # up layers
    for layer in range(4 - 2, -1, -1):
        with tf.name_scope("up_conv_{}".format(str(layer))):
            features = 2 ** (layer + 1) * features_root
            h_deconv = deconv2d(in_node, features, features//2, training)
            h_deconv_concat = (h_deconv + fat_dw_h_convs[layer] + inn_dw_h_convs[layer] +\
                              wat_dw_h_convs[layer] + opp_dw_h_convs[layer])/5

            deconv[layer] = h_deconv_concat
            in_node = inception_conv(h_deconv_concat, features//2, features//2, keep_prob, training)
            up_h_convs[layer] = in_node

    # output
    stddev = np.sqrt(2 / (3 ** 2 * features_root))
    w = weight_variable([3, 3, features_root, 2], stddev, name="w")
    b = bias_variable([2], name="b")
    up_h_convs["out"] = tf.nn.bias_add(tf.nn.conv2d(up_h_convs[0], w, strides=[1, 1, 1, 1], padding="SAME"), b)
    
    # RCF
    for layer in range(2, 0, -1):
        with tf.name_scope("output_{}".format(str(layer))):
            in_node = up_h_convs[layer]
            conv = conv2d_2(in_node, features_root*2**layer, 2, keep_prob)
            deconv = deconv2d_2(conv, 2, 2, 2**layer, keep_prob)
            up_h_convs["out_{}".format(layer)] = deconv
    
    in_node = tf.concat([up_h_convs["out"], up_h_convs["out_1"], up_h_convs["out_2"]], 3)
    w_out = weight_variable([1, 1, 6, 2], stddev, name="w_out")
    b_out = bias_variable([2], name="b_out")
    output_map = tf.nn.bias_add(tf.nn.conv2d(in_node, w_out, strides=[1, 1, 1, 1], padding="SAME"), b_out)
    
    if summaries:
        with tf.name_scope("summaries"):
            for k in up_h_convs.keys():
                tf.summary.image('up_h_convs_%s' % k, get_image_summary(up_h_convs[k]))
            tf.summary.image("output_map", get_image_summary(output_map))

            for k in fat_dw_h_convs.keys():
                tf.summary.histogram("dw_convolution_%02d" % k + '/activations', fat_dw_h_convs[k])

    variables = []
    for w1, w2 in weights:
        variables.append(w1)
        variables.append(w2)

    for b1, b2 in biases:
        variables.append(b1)
        variables.append(b2)

    return [output_map, up_h_convs["out"], up_h_convs["out_1"]], variables

def edge_net_3layer(x, keep_prob, channels, n_class, layers=3, features_root=32, summaries=True, training=True):
    logging.info(
        "Layers {layers}, features {features}".format(
            layers=layers,
            features=features_root))

    # Placeholder for the input image
    with tf.name_scope("preprocessing"):
        nx = tf.shape(x)[1]
        ny = tf.shape(x)[2]
        x_image = tf.reshape(x, tf.stack([-1, nx, ny, channels]))
        in_node = x_image
        batch_size = tf.shape(x_image)[0]

    weights = []
    biases = []
    fat_inputs = OrderedDict();     inn_inputs = OrderedDict();     wat_inputs = OrderedDict();     opp_inputs = OrderedDict();
    fat_pools = OrderedDict();      inn_pools = OrderedDict();      wat_pools = OrderedDict();      opp_pools = OrderedDict()
    fat_dw_h_convs = OrderedDict(); inn_dw_h_convs = OrderedDict(); wat_dw_h_convs = OrderedDict(); opp_dw_h_convs = OrderedDict();
    deconv = OrderedDict()
    up_h_convs = OrderedDict()

    # down layers
    for layer in range(0, 3):
        with tf.name_scope("down_conv_{}".format(str(layer))):
            features = 2 ** layer * features_root
            if layer==0:
                with tf.name_scope("fat"):
                    in_node = tf.reshape(x_image[..., 0],[batch_size, nx, ny, 1])
                    conv = inception_conv(in_node, 1, features, keep_prob, training)
                    fat_dw_h_convs[layer] = conv
                    fat_pools[layer] = max_pool(conv, 2)
                with tf.name_scope("inn"):
                    in_node = tf.reshape(x_image[..., 1],[batch_size, nx, ny, 1])
                    conv = inception_conv(in_node, 1, features, keep_prob, training)
                    inn_dw_h_convs[layer] = conv
                    inn_pools[layer] = max_pool(conv, 2)
                with tf.name_scope("wat"):
                    in_node = tf.reshape(x_image[..., 2],[batch_size, nx, ny, 1])
                    conv = inception_conv(in_node, 1, features, keep_prob, training)
                    wat_dw_h_convs[layer] = conv
                    wat_pools[layer] = max_pool(conv, 2)
                with tf.name_scope("opp"):
                    in_node = tf.reshape(x_image[..., 3],[batch_size, nx, ny, 1])
                    conv = inception_conv(in_node, 1, features, keep_prob, training)
                    opp_dw_h_convs[layer] = conv
                    opp_pools[layer] = max_pool(conv, 2)
            elif layer==1:
                with tf.name_scope("fat"):
                    in_node = tf.concat([fat_pools[0], inn_pools[0], wat_pools[0], opp_pools[0]], 3)
                    fat_inputs[layer] = in_node
                    conv = inception_conv(in_node, features_root*4, features, keep_prob, training)
                    fat_dw_h_convs[layer] = conv
                    fat_pools[layer] = max_pool(conv, 2)
                with tf.name_scope("inn"):
                    in_node = tf.concat([inn_pools[0], wat_pools[0], opp_pools[0], fat_pools[0]], 3)
                    inn_inputs[layer] = in_node
                    conv = inception_conv(in_node, features_root*4, features, keep_prob, training)
                    inn_dw_h_convs[layer] = conv
                    inn_pools[layer] = max_pool(conv, 2)
                with tf.name_scope("wat"):
                    in_node = tf.concat([wat_pools[0], opp_pools[0], fat_pools[0], inn_pools[0]], 3)
                    wat_inputs[layer] = in_node
                    conv = inception_conv(in_node, features_root*4, features, keep_prob, training)
                    wat_dw_h_convs[layer] = conv
                    wat_pools[layer] = max_pool(conv, 2)
                with tf.name_scope("opp"):
                    in_node = tf.concat([opp_pools[0], fat_pools[0], inn_pools[0], wat_pools[0]], 3)
                    opp_inputs[layer] = in_node
                    conv = inception_conv(in_node, features_root*4, features, keep_prob, training)
                    opp_dw_h_convs[layer] = conv
                    opp_pools[layer] = max_pool(conv, 2)
            elif layer==2:
                with tf.name_scope("fat"):
                    in_node = tf.concat([fat_pools[1], inn_pools[1], wat_pools[1], opp_pools[1]], 3)
                    tmp_node = cropCenter(fat_inputs[1], in_node)
                    in_node = tf.concat([in_node, tmp_node], 3)
                    conv = inception_conv(in_node, features_root*12, features, keep_prob, training)
                    up_h_convs[layer] = conv

    in_node = up_h_convs[3-1]
    # up layers
    for layer in range(3 - 2, -1, -1):
        with tf.name_scope("up_conv_{}".format(str(layer))):
            features = 2 ** (layer + 1) * features_root
            h_deconv = deconv2d(in_node, features, features//2, training)
            h_deconv_concat = (h_deconv + fat_dw_h_convs[layer] + inn_dw_h_convs[layer] +\
                              wat_dw_h_convs[layer] + opp_dw_h_convs[layer])/5

            deconv[layer] = h_deconv_concat
            in_node = inception_conv(h_deconv_concat, features//2, features//2, keep_prob, training)
            up_h_convs[layer] = in_node

    # output
    stddev = np.sqrt(2 / (3 ** 2 * features_root))
    w = weight_variable([3, 3, features_root, 2], stddev, name="w")
    b = bias_variable([2], name="b")
    up_h_convs["out"] = tf.nn.bias_add(tf.nn.conv2d(up_h_convs[0], w, strides=[1, 1, 1, 1], padding="SAME"), b)
    
    # RCF
    for layer in range(1, 0, -1):
        with tf.name_scope("output_{}".format(str(layer))):
            in_node = up_h_convs[layer]
            conv = conv2d_2(in_node, features_root*2**layer, 2, keep_prob)
            deconv = deconv2d_2(conv, 2, 2, 2**layer, keep_prob)
            up_h_convs["out_{}".format(layer)] = deconv
            
    in_node = tf.concat([up_h_convs["out"], up_h_convs["out_1"], up_h_convs["out"]], 3)
    w_out = weight_variable([1, 1, 6, 2], stddev, name="w_out")
    b_out = bias_variable([2], name="b_out")
    output_map = tf.nn.bias_add(tf.nn.conv2d(in_node, w_out, strides=[1, 1, 1, 1], padding="SAME"), b_out)
    
    if summaries:
        with tf.name_scope("summaries"):
            for k in up_h_convs.keys():
                tf.summary.image('up_h_convs_%s' % k, get_image_summary(up_h_convs[k]))
            tf.summary.image("output_map", get_image_summary(output_map))

            for k in fat_dw_h_convs.keys():
                tf.summary.histogram("dw_convolution_%02d" % k + '/activations', fat_dw_h_convs[k])

    variables = []
    for w1, w2 in weights:
        variables.append(w1)
        variables.append(w2)

    for b1, b2 in biases:
        variables.append(b1)
        variables.append(b2)

    return [output_map, up_h_convs["out"], up_h_convs["out_1"]], variables

class Unet(object):
    """
    A unet implementation

    :param channels: (optional) number of channels in the input image
    :param n_class: (optional) number of output labels
    :param cost: (optional) name of the cost function. Default is 'cross_entropy'
    :param cost_kwargs: (optional) kwargs passed to the cost function. See Unet._get_cost for more options
    """

    def __init__(self, channels=3, n_class=2, cost="cross_entropy", cost_kwargs={}, **kwargs):
        tf.reset_default_graph()

        self.n_class = n_class
        self.summaries = kwargs.get("summaries", True)

        self.x = tf.placeholder("float", shape=[None, None, None, channels], name="x")
        self.y = tf.placeholder("float", shape=[None, None, None, n_class], name="y")
        self.z = tf.placeholder(tf.int32, shape=[None, 8], name="z")
        self.keep_prob = tf.placeholder(tf.float32, name="dropout_probability")  # dropout (keep probability)

        logits, self.variables= create_edge_net_3(self.x, self.keep_prob, channels, n_class, **kwargs)
        #logits, self.variables= edge_net_3layer(self.x, self.keep_prob, channels, n_class, **kwargs)
        self.cost = self._get_cost(logits, cost, cost_kwargs)

        self.gradients_node = tf.gradients(self.cost, self.variables)

        with tf.name_scope("cross_entropy"):
            self.cross_entropy = cross_entropy(tf.reshape(self.y, [-1, n_class]),
                                               tf.reshape(pixel_wise_softmax(logits[0]), [-1, n_class]))

        with tf.name_scope("results"):
            self.predicter = pixel_wise_softmax(logits[0])
            self.correct_pred = tf.equal(tf.argmax(self.predicter, 3), tf.argmax(self.y, 3))
            self.accuracy = tf.reduce_mean(tf.cast(self.correct_pred, tf.float32))

    def _get_cost(self, logits, cost_name, cost_kwargs):
        """
        Constructs the cost function, either cross_entropy, weighted cross_entropy or dice_coefficient.
        Optional arguments are:
        class_weights: weights for the different classes in case of multi-class imbalance
        regularizer: power of the L2 regularizers added to the loss function
        """

        with tf.name_scope("cost"):
            flat_logits = tf.reshape(logits, [-1, self.n_class])
            flat_labels = tf.reshape(self.y, [-1, self.n_class])
            if cost_name == "cross_entropy":
                class_weights = cost_kwargs.pop("class_weights", None)

                if class_weights is not None:
                    class_weights = tf.constant(np.array(class_weights, dtype=np.float32))

                    weight_map = tf.multiply(flat_labels, class_weights)
                    weight_map = tf.reduce_sum(weight_map, axis=1)

                    loss_map = tf.nn.softmax_cross_entropy_with_logits(logits=flat_logits,
                                                                          labels=flat_labels)
                    weighted_loss = tf.multiply(loss_map, weight_map)

                    loss = tf.reduce_mean(weighted_loss)

                else:
                    loss = tf.reduce_mean(tf.nn.softmax_cross_entropy_with_logits_v2(logits=flat_logits,
                                                                                     labels=flat_labels))
            elif cost_name == "dice":
                loss = 0
                for logit in logits:
                    prediction = pixel_wise_softmax(logit)
                    intersection = tf.reduce_sum(prediction * self.y)
                    coefficient = (2 * intersection + 1) / (tf.reduce_sum(prediction) + tf.reduce_sum(self.y) + 1)
                    loss += 1 - coefficient
            elif cost_name == "dice+ce":
                loss = 0
                for logit in logits:
                    flat_logit = tf.reshape(logit, [-1, self.n_class])
                    flat_label = tf.reshape(self.y, [-1, self.n_class])
                    loss += tf.reduce_mean(tf.nn.softmax_cross_entropy_with_logits_v2(logits=flat_logit, labels=flat_label))
                    prediction = pixel_wise_softmax(logit)
                    intersection = tf.reduce_sum(prediction * self.y)
                    coefficient = (2 * intersection + 1) / (tf.reduce_sum(prediction) + tf.reduce_sum(self.y) + 1)
                    loss += 1 - coefficient       
            elif cost_name == "shape":
                loss = 0
                for batch_index in range(4):   # 4 is batch_size
                    y_min = self.z[batch_index, 2]
                    y_max = self.z[batch_index, 3]
                    label = self.y[batch_index, :, 0:y_max]
                    logit = logits[batch_index, :, 0:y_max]
                    flat_logit = tf.reshape(logit, [-1, self.n_class])
                    flat_label = tf.reshape(label, [-1, self.n_class])
                    loss += tf.reduce_mean(tf.nn.softmax_cross_entropy_with_logits_v2(logits=flat_logit,
                                                                                    labels=flat_label))
            elif cost_name == "shape_1":
                loss = 0
                for batch_index in range(4):   # 4 is batch_size
                    x_min = self.z[batch_index, 0]
                    x_max = self.z[batch_index, 1]
                    y_min = self.z[batch_index, 2]
                    y_max = self.z[batch_index, 3]

                    label = self.y[batch_index]
                    logit = logits[batch_index]
                    flat_logit = tf.reshape(logit, [-1, self.n_class])
                    flat_label = tf.reshape(label, [-1, self.n_class])
                    loss_tmp = tf.reduce_sum(tf.nn.softmax_cross_entropy_with_logits_v2(logits=flat_logit,
                                                                                    labels=flat_label))
                    label_2 = self.y[batch_index, x_min:x_max, y_max+3:]
                    logit_2 = logits[batch_index, x_min:x_max, y_max+3:]
                    flat_logit_2 = tf.reshape(logit_2, [-1, self.n_class])
                    flat_label_2 = tf.reshape(label_2, [-1, self.n_class])
                    loss_tmp -= tf.reduce_sum(tf.nn.softmax_cross_entropy_with_logits_v2(logits=flat_logit_2,
                                                                                    labels=flat_label_2))
                    loss_tmp = loss_tmp/(256*256)
                    loss += loss_tmp
            elif cost_name == "shape_2":
                loss = 0
                for logit in logits:
                    for batch_index in range(4):
                        x_min = self.z[batch_index, 0]
                        x_max = self.z[batch_index, 1]
                        y_min = self.z[batch_index, 2]
                        y_max = self.z[batch_index, 3]

                        label_1 = self.y[batch_index]
                        logit_1 = logit[batch_index]
                        flat_logit_1 = tf.reshape(logit_1, [-1, self.n_class])
                        flat_label_1 = tf.reshape(label_1, [-1, self.n_class])
                        loss_tmp = tf.reduce_sum(tf.nn.softmax_cross_entropy_with_logits_v2(logits=flat_logit_1, 
                                                                                    labels=flat_label_1))

                        label_2 = self.y[batch_index, x_min:x_max, y_max+3:]
                        logit_2 = logit[batch_index, x_min:x_max, y_max+3:]
                        flat_logit_2 = tf.reshape(logit_2, [-1, self.n_class])
                        flat_label_2 = tf.reshape(label_2, [-1, self.n_class])
                        loss_tmp -= tf.reduce_sum(tf.nn.softmax_cross_entropy_with_logits_v2(logits=flat_logit_2,
                                                                                        labels=flat_label_2))
                        label_3 = self.y[batch_index, x_min:x_max, y_min:y_max]
                        logit_3 = logit[batch_index, x_min:x_max, y_min:y_max]
                        flat_logit_3 = tf.reshape(logit_3, [-1, self.n_class])
                        flat_label_3 = tf.reshape(label_3, [-1, self.n_class])
                        loss_tmp += 10*tf.reduce_sum(tf.nn.softmax_cross_entropy_with_logits_v2(logits=flat_logit_3,
                                                                                    labels=flat_label_3))
                        loss_tmp = loss_tmp/(256*256*2)
                    
                        loss += loss_tmp
            elif cost_name == "each_IVD":
                for batch_index in range(4):
                    label_1 = self.y[batch_index]
                    logit_1 = logits[batch_index]
                    flat_logit_1 = tf.reshape(logit_1, [-1, self.n_class])
                    flat_label_1 = tf.reshape(label_1, [-1, self.n_class])
                    loss_tmp = tf.reduce_sum(tf.nn.softmax_cross_entropy_with_logits_v2(logits=flat_logit_1, labels=flat_label_1))
                    for i in range(7):
                        x_min = self.z[batch_index, 0 + 4*i]
                        x_max = self.z[batch_index, 1 + 4*i]
                        y_min = self.z[batch_index, 2 + 4*i]
                        y_max = self.z[batch_index, 3 + 4*i]

            elif cost_name == "EPE":
                edge_gt = tf.image.sobel_edges(self.y / tf.reduce_max(self.y))
                edge_pre = tf.image.sobel_edges(logits / tf.reduce_max(logits))
                loss = tf.sqrt(tf.nn.l2_loss(edge_gt - edge_pre)*2)/256
            elif cost_name == "EPE_2": # EPE loss may be false
                edge_gt = tf.image.sobel_edges(self.y)
                edge_gt = tf.sqrt(tf.square(edge_gt[...,0]) + tf.square(edge_gt[...,1]))
                edge_pre = tf.image.sobel_edges(logits)
                edge_pre = tf.sqrt(tf.square(edge_pre[...,0]) + tf.square(edge_pre[...,1]))
                loss = tf.reduce_mean(edge_gt - edge_pre)
                #loss = tf.sqrt(tf.nn.l2_loss(edge_gt - edge_pre)*2)/256
            elif cost_name == "CE+EPE":
                loss_1 = tf.reduce_mean(tf.nn.softmax_cross_entropy_with_logits_v2(logits=flat_logits,
                                                                                     labels=flat_labels))
                edge_gt = tf.image.sobel_edges(self.y / tf.reduce_max(self.y))
                edge_pre = tf.image.sobel_edges(logits / tf.reduce_max(logits))
                loss_2 = tf.sqrt(tf.nn.l2_loss(edge_gt - edge_pre)*2)/256/10

                loss = loss_1 + loss_2*10
            elif cost_name == "shape+CE+EPE":
                loss = 0
                for logit in logits:
                    for batch_index in range(4):
                        x_min = self.z[batch_index, 0]
                        x_max = self.z[batch_index, 1]
                        y_min = self.z[batch_index, 2]
                        y_max = self.z[batch_index, 3]

                        label_1 = self.y[batch_index]
                        logit_1 = logit[batch_index]
                        flat_logit_1 = tf.reshape(logit_1, [-1, self.n_class])
                        flat_label_1 = tf.reshape(label_1, [-1, self.n_class])
                        loss_tmp = tf.reduce_sum(tf.nn.softmax_cross_entropy_with_logits_v2(logits=flat_logit_1, 
                                                                                            labels=flat_label_1))

                        label_2 = self.y[batch_index, x_min:x_max, y_max+3:]
                        logit_2 = logit[batch_index, x_min:x_max, y_max+3:]
                        flat_logit_2 = tf.reshape(logit_2, [-1, self.n_class])
                        flat_label_2 = tf.reshape(label_2, [-1, self.n_class])
                        loss_tmp -= tf.reduce_sum(tf.nn.softmax_cross_entropy_with_logits_v2(logits=flat_logit_2,
                                                                                            labels=flat_label_2))
                        label_3 = self.y[batch_index, x_min:x_max, y_min:y_max]
                        logit_3 = logit[batch_index, x_min:x_max, y_min:y_max]
                        flat_logit_3 = tf.reshape(logit_3, [-1, self.n_class])
                        flat_label_3 = tf.reshape(label_3, [-1, self.n_class])
                        loss_tmp += 10*tf.reduce_sum(tf.nn.softmax_cross_entropy_with_logits_v2(logits=flat_logit_3,
                                                                                                labels=flat_label_3))

                        loss_tmp = loss_tmp/(256*256*2)

                        label_3 = tf.expand_dims(label_3, 0)
                        logit_3 = tf.expand_dims(logit_3, 0)
                        edge_gt = tf.image.sobel_edges(label_3 / tf.reduce_max(label_3))
                        edge_pre = tf.image.sobel_edges(logit_3 / tf.reduce_max(logit_3))
                        loss_edge = tf.sqrt(tf.nn.l2_loss(edge_gt - edge_pre)*2)/256/2
                    
                        loss_tmp += loss_edge
                    
                        loss += loss_tmp 
            else:
                raise ValueError("Unknown cost function: " % cost_name)

            regularizer = cost_kwargs.pop("regularizer", None)
            if regularizer is not None:
                regularizers = sum([tf.nn.l2_loss(variable) for variable in self.variables])
                loss += (regularizer * regularizers)

            return loss

        with tf.name_scope("cost"):
            if cost_name == "cross_entropy":
                loss = 0
                flat_label = tf.reshape(self.y, [-1, self.n_class])
                for logit in logits:
                    flat_logit = tf.reshape(logit, [-1, self.n_class])
                    loss += tf.reduce_mean(tf.nn.softmax_cross_entropy_with_logits_v2(logits=flat_logit,
                                                                                     labels=flat_label))
            elif cost_name == "dice_coefficient":
                eps = 1e-5
                loss = 0
                for logit in logits:
                    prediction = pixel_wise_softmax(logit)
                    intersection = tf.reduce_sum(prediction * self.y)
                    union = eps + tf.reduce_sum(prediction) + tf.reduce_sum(self.y)
                    loss += -(2 * intersection / (union))
            elif cost_name == "shape":
                loss = 0
                for batch_index in range(4):   # 4 is batch_size
                    y_min = self.z[batch_index, 2]
                    y_max = self.z[batch_index, 3]
                    label = self.y[batch_index, :, 0:y_max]
                    logit = logits[batch_index, :, 0:y_max]
                    flat_logit = tf.reshape(logit, [-1, self.n_class])
                    flat_label = tf.reshape(label, [-1, self.n_class])
                    loss += tf.reduce_mean(tf.nn.softmax_cross_entropy_with_logits_v2(logits=flat_logit,
                                                                                    labels=flat_label))
            elif cost_name == "shape_2":
                loss = 0
                for batch_index in range(4):   # 4 is batch_size
                    y_min = self.z[batch_index, 2]
                    y_max = self.z[batch_index, 3]
                    label = self.y[batch_index, :, 0:y_max]
                    logit = logits[batch_index, :, 0:y_max]
                    flat_logit = tf.reshape(logit, [-1, self.n_class])
                    flat_label = tf.reshape(label, [-1, self.n_class])
                    loss_tmp = tf.reduce_sum(tf.nn.softmax_cross_entropy_with_logits_v2(logits=flat_logit,
                                                                                    labels=flat_label))
                    label_2 = self.y[batch_index, :, 252:]
                    logit_2 = logits[batch_index, :, 252:]
                    flat_logit_2 = tf.reshape(logit_2, [-1, self.n_class])
                    flat_label_2 = tf.reshape(label_2, [-1, self.n_class])
                    loss_tmp += tf.reduce_sum(tf.nn.softmax_cross_entropy_with_logits_v2(logits=flat_logit_2,
                                                                                    labels=flat_label_2))
                    loss_tmp = loss_tmp/(256*256)
                    loss += loss_tmp
            elif cost_name == "shape_3":
                loss = 0
                for batch_index in range(4):   # 4 is batch_size
                    x_min = self.z[batch_index, 0]
                    x_max = self.z[batch_index, 1]
                    y_min = self.z[batch_index, 2]
                    y_max = self.z[batch_index, 3]

                    label = self.y[batch_index]
                    logit = logits[batch_index]
                    flat_logit = tf.reshape(logit, [-1, self.n_class])
                    flat_label = tf.reshape(label, [-1, self.n_class])
                    loss_tmp = tf.reduce_sum(tf.nn.softmax_cross_entropy_with_logits_v2(logits=flat_logit,
                                                                                    labels=flat_label))
                    label_2 = self.y[batch_index, x_min:x_max, y_max+7:252]
                    logit_2 = logits[batch_index, x_min:x_max, y_max+7:252]
                    flat_logit_2 = tf.reshape(logit_2, [-1, self.n_class])
                    flat_label_2 = tf.reshape(label_2, [-1, self.n_class])
                    loss_tmp -= tf.reduce_sum(tf.nn.softmax_cross_entropy_with_logits_v2(logits=flat_logit_2,
                                                                                    labels=flat_label_2))
                    loss_tmp = loss_tmp/(256*256)
                    loss += loss_tmp
            elif cost_name == "shape_4":
                loss = 0
                for batch_index in range(4):   # 4 is batch_size
                    x_min = self.z[batch_index, 0]
                    x_max = self.z[batch_index, 1]
                    y_min = self.z[batch_index, 2]
                    y_max = self.z[batch_index, 3]
                    smallest_x_min = self.z[batch_index, 4]
                    smallest_x_max = self.z[batch_index, 5]
                    smallest_y_min = self.z[batch_index, 6]
                    smallest_y_max = self.z[batch_index, 7]

                    label = self.y[batch_index]
                    logit = logits[batch_index]
                    flat_logit = tf.reshape(logit, [-1, self.n_class])
                    flat_label = tf.reshape(label, [-1, self.n_class])
                    loss_tmp = tf.reduce_sum(tf.nn.softmax_cross_entropy_with_logits_v2(logits=flat_logit,
                                                                                    labels=flat_label))
                    label_2 = self.y[batch_index, x_min+3:x_max+5, y_max+3:252]
                    logit_2 = logits[batch_index, x_min+3:x_max+5, y_max+3:252]
                    flat_logit_2 = tf.reshape(logit_2, [-1, self.n_class])
                    flat_label_2 = tf.reshape(label_2, [-1, self.n_class])
                    loss_tmp -= tf.reduce_sum(tf.nn.softmax_cross_entropy_with_logits_v2(logits=flat_logit_2,
                                                                                    labels=flat_label_2))
                    label_3 = self.y[batch_index, smallest_x_min-2:smallest_x_max+2, smallest_y_min-2:smallest_y_max+2]
                    logit_3 = logits[batch_index, smallest_x_min-2:smallest_x_max+2, smallest_y_min-2:smallest_y_max+2]
                    flat_logit_3 = tf.reshape(logit_3, [-1, self.n_class])
                    flat_label_3 = tf.reshape(label_3, [-1, self.n_class])
                    loss_tmp += 2*tf.reduce_sum(tf.nn.softmax_cross_entropy_with_logits_v2(logits=flat_logit_3,
                                                                                    labels=flat_label_3))
                    loss_tmp = loss_tmp/(256*256+40*30)
                    loss += loss_tmp
            elif cost_name == "shape_5":
                loss = 0
                for batch_index in range(4):   # 4 is batch_size
                    x_min = self.z[batch_index, 0]
                    x_max = self.z[batch_index, 1]
                    y_min = self.z[batch_index, 2]
                    y_max = self.z[batch_index, 3]
                    smallest_x_min = self.z[batch_index, 4]
                    smallest_x_max = self.z[batch_index, 5]
                    smallest_y_min = self.z[batch_index, 6]
                    smallest_y_max = self.z[batch_index, 7]

                    label = self.y[batch_index]
                    logit = logits[batch_index]
                    flat_logit = tf.reshape(logit, [-1, self.n_class])
                    flat_label = tf.reshape(label, [-1, self.n_class])
                    loss_tmp = tf.reduce_sum(tf.nn.softmax_cross_entropy_with_logits_v2(logits=flat_logit,
                                                                                    labels=flat_label))
                    label_2 = self.y[batch_index, smallest_x_min-2:smallest_x_max+2, smallest_y_min-2:smallest_y_max+2]
                    logit_2 = logits[batch_index, smallest_x_min-2:smallest_x_max+2, smallest_y_min-2:smallest_y_max+2]
                    flat_logit_2 = tf.reshape(logit_2, [-1, self.n_class])
                    flat_label_2 = tf.reshape(label_2, [-1, self.n_class])
                    loss_tmp += 2*tf.reduce_sum(tf.nn.softmax_cross_entropy_with_logits_v2(logits=flat_logit_2,
                                                                                    labels=flat_label_2))
                    loss_tmp = loss_tmp/(256*256 + 2*40*30)
                    loss += loss_tmp
            else:
                raise ValueError("Unknown cost function: " % cost_name)

            regularizer = cost_kwargs.pop("regularizer", None)
            if regularizer is not None:
                regularizers = sum([tf.nn.l2_loss(variable) for variable in self.variables])
                loss += (regularizer * regularizers)

            return loss

    def predict(self, model_path, x_test):
        """
        Uses the model to create a prediction for the given data

        :param model_path: path to the model checkpoint to restore
        :param x_test: Data to predict on. Shape [n, nx, ny, channels]
        :returns prediction: The unet prediction Shape [n, px, py, labels] (px=nx-self.offset/2)
        """

        init = tf.global_variables_initializer()
        with tf.Session() as sess:
            # Initialize variables
            sess.run(init)

            # Restore model weights from previously saved model
            self.restore(sess, model_path)

            y_dummy = np.empty((x_test.shape[0], x_test.shape[1], x_test.shape[2], self.n_class))
            range_arr = np.empty((x_test.shape[0], 8))
            prediction = sess.run(self.predicter, feed_dict={self.x: x_test, self.y: y_dummy, self.z: range_arr, self.keep_prob: 1.})

        return prediction

    def save(self, sess, model_path):
        """
        Saves the current session to a checkpoint

        :param sess: current session
        :param model_path: path to file system location
        """
        saver = tf.train.Saver(var_list=tf.global_variables())
        save_path = saver.save(sess, model_path)
        return save_path

    def restore(self, sess, model_path):
        """
        Restores a session from a checkpoint

        :param sess: current session instance
        :param model_path: path to file system checkpoint location
        """

        saver = tf.train.Saver(tf.global_variables())
        saver.restore(sess, model_path)
        logging.info("Model restored from file: %s" % model_path)


class Trainer(object):
    """
    Trains a unet instance

    :param net: the unet instance to train
    :param batch_size: size of training batch
    :param verification_batch_size: size of verification batch
    :param norm_grads: (optional) true if normalized gradients should be added to the summaries
    :param optimizer: (optional) name of the optimizer to use (momentum or adam)
    :param opt_kwargs: (optional) kwargs passed to the learning rate (momentum opt) and to the optimizer

    """

    def __init__(self, net, batch_size=1, verification_batch_size = 4, norm_grads=False, optimizer="momentum", opt_kwargs={}):
        self.net = net
        self.batch_size = batch_size
        self.verification_batch_size = verification_batch_size
        self.norm_grads = norm_grads
        self.optimizer = optimizer
        self.opt_kwargs = opt_kwargs

    def _get_optimizer(self, training_iters, global_step):
        if self.optimizer == "momentum":
            learning_rate = self.opt_kwargs.pop("learning_rate", 0.2)
            decay_rate = self.opt_kwargs.pop("decay_rate", 0.95)
            momentum = self.opt_kwargs.pop("momentum", 0.2)

            self.learning_rate_node = tf.train.exponential_decay(learning_rate=learning_rate,
                                                                 global_step=global_step,
                                                                 decay_steps=training_iters,
                                                                 decay_rate=decay_rate,
                                                                 staircase=True)

            optimizer = tf.train.MomentumOptimizer(learning_rate=self.learning_rate_node, momentum=momentum,
                                                   **self.opt_kwargs).minimize(self.net.cost,
                                                                               global_step=global_step)
        elif self.optimizer == "adam":
            learning_rate = self.opt_kwargs.pop("learning_rate", 0.001)
            decay_rate = self.opt_kwargs.pop("decay_rate", 1)
            
            self.learning_rate_node = tf.train.exponential_decay(learning_rate=learning_rate,
                                                                 global_step=global_step,
                                                                 decay_steps=training_iters*para.decay_epochs,
                                                                 decay_rate=decay_rate,
                                                                 staircase=True)
            
            #self.learning_rate_node = tf.Variable(learning_rate, name="learning_rate")

            update_ops = tf.get_collection(tf.GraphKeys.UPDATE_OPS)
            with tf.control_dependencies(update_ops):
                optimizer = tf.train.AdamOptimizer(learning_rate=self.learning_rate_node, beta1=0.9, beta2=0.99,
                                **self.opt_kwargs).minimize(self.net.cost, global_step=global_step)

        return optimizer

    def _initialize(self, training_iters, output_path, restore, prediction_path):
        global_step = tf.Variable(0, name="global_step")

        self.norm_gradients_node = tf.Variable(tf.constant(0.0, shape=[len(self.net.gradients_node)]), name="norm_gradients")

        if self.net.summaries and self.norm_grads:
            tf.summary.histogram('norm_grads', self.norm_gradients_node)

        tf.summary.scalar('loss', self.net.cost)
        tf.summary.scalar('cross_entropy', self.net.cross_entropy)
        tf.summary.scalar('accuracy', self.net.accuracy)

        self.optimizer = self._get_optimizer(training_iters, global_step)
        tf.summary.scalar('learning_rate', self.learning_rate_node)

        self.summary_op = tf.summary.merge_all()
        init = tf.global_variables_initializer()

        self.prediction_path = prediction_path
        abs_prediction_path = os.path.abspath(self.prediction_path)
        output_path = os.path.abspath(output_path)

        if not restore:
            logging.info("Removing '{:}'".format(abs_prediction_path))
            shutil.rmtree(abs_prediction_path, ignore_errors=True)
            logging.info("Removing '{:}'".format(output_path))
            shutil.rmtree(output_path, ignore_errors=True)

        if not os.path.exists(abs_prediction_path):
            logging.info("Allocating '{:}'".format(abs_prediction_path))
            os.makedirs(abs_prediction_path)

        if not os.path.exists(output_path):
            logging.info("Allocating '{:}'".format(output_path))
            os.makedirs(output_path)

        return init

    def train(self, data_provider, output_path, training_iters=10, epochs=100, dropout=0.75, display_step=1, restore=False, write_graph=False, prediction_path='prediction'):
        """
        Lauches the training process

        :param data_provider: callable returning training and verification data
        :param output_path: path where to store checkpoints
        :param training_iters: number of training mini batch iteration
        :param epochs: number of epochs
        :param dropout: dropout probability
        :param display_step: number of steps till outputting stats
        :param restore: Flag if previous model should be restored
        :param write_graph: Flag if the computation graph should be written as protobuf file to the output path
        :param prediction_path: path where to save predictions on each epoch
        """
        save_path = os.path.join(output_path, "model.ckpt")
        if epochs == 0:
            return save_path

        init = self._initialize(training_iters, output_path, restore, prediction_path)

        with tf.Session() as sess:
            if write_graph:
                tf.train.write_graph(sess.graph_def, output_path, "graph.pb", False)

            sess.run(init)

            if restore:
                ckpt = tf.train.get_checkpoint_state(output_path)
                if ckpt and ckpt.model_checkpoint_path:
                    self.net.restore(sess, ckpt.model_checkpoint_path)

            test_x, test_y, range_arr = data_provider(self.verification_batch_size)
            pred_shape = self.store_prediction(sess, test_x, test_y, range_arr, "_init")

            summary_writer = tf.summary.FileWriter(output_path, graph=sess.graph)
            logging.info("Start optimization")

            avg_gradients = None
            for epoch in range(epochs):
                total_loss = 0
                for step in range((epoch * training_iters), ((epoch + 1) * training_iters)):
                    batch_x, batch_y, range_arr = data_provider(self.batch_size)

                    # Run optimization op (backprop)
                    _, loss, lr, gradients = sess.run(
                        (self.optimizer, self.net.cost, self.learning_rate_node, self.net.gradients_node),
                        feed_dict={self.net.x: batch_x,
                                   self.net.y: batch_y,
                                   self.net.z: range_arr,
                                   self.net.keep_prob: dropout})

                    if self.net.summaries and self.norm_grads:
                        avg_gradients = _update_avg_gradients(avg_gradients, gradients, step)
                        norm_gradients = [np.linalg.norm(gradient) for gradient in avg_gradients]
                        self.norm_gradients_node.assign(norm_gradients).eval()

                    if step % display_step == 0:
                        self.output_minibatch_stats(sess, summary_writer, step, batch_x, batch_y, range_arr)

                    total_loss += loss

                self.output_epoch_stats(epoch, total_loss, training_iters, lr)
                self.store_prediction(sess, test_x, test_y, range_arr, "epoch_%s" % epoch)

                save_path = self.net.save(sess, save_path)
            logging.info("Optimization Finished!")

            return save_path

    def store_prediction(self, sess, batch_x, batch_y, range_arr, name):
        prediction = sess.run(self.net.predicter, feed_dict={self.net.x: batch_x,
                                                             self.net.y: batch_y,
                                                             self.net.z: range_arr,
                                                             self.net.keep_prob: 1.})
        pred_shape = prediction.shape

        loss = sess.run(self.net.cost, feed_dict={self.net.x: batch_x,
                                                  self.net.y: batch_y,
                                                  self.net.z: range_arr,
                                                  self.net.keep_prob: 1.})

        #logging.info("Verification error= {:.2f}%, loss= {:.6f}".format(error_rate(prediction, batch_y), loss))

        img = util.combine_img_prediction(batch_x, batch_y, prediction)
        util.save_image(img, "%s/%s.jpg" % (self.prediction_path, name))

        return pred_shape

    def output_epoch_stats(self, epoch, total_loss, training_iters, lr):
        logging.info(
            "Epoch {:}, Average loss: {:.6f}, learning rate: {:.5f}".format(epoch, (total_loss / training_iters), lr))

    def output_minibatch_stats(self, sess, summary_writer, step, batch_x, batch_y, range_arr):
        # Calculate batch loss and accuracy
        summary_str, loss, acc, predictions = sess.run([self.summary_op,
                                                        self.net.cost,
                                                        self.net.accuracy,
                                                        self.net.predicter],
                                                       feed_dict={self.net.x: batch_x,
                                                                  self.net.y: batch_y,
                                                                  self.net.z: range_arr,
                                                                  self.net.keep_prob: 1.})
        summary_writer.add_summary(summary_str, step)
        summary_writer.flush()
        logging.info(
            "Iter {:}, Minibatch Loss= {:.6f}, Training Accuracy= {:.6f}, Minibatch error= {:.2f}%".format(step,
                                                                                                           loss,
                                                                                                           acc,
                                                                                                           error_rate(
                                                                                                               predictions,
                                                                                                               batch_y)))

def _update_avg_gradients(avg_gradients, gradients, step):
    if avg_gradients is None:
        avg_gradients = [np.zeros_like(gradient) for gradient in gradients]
    for i in range(len(gradients)):
        avg_gradients[i] = (avg_gradients[i] * (1.0 - (1.0 / (step + 1)))) + (gradients[i] / (step + 1))

    return avg_gradients


def error_rate(predictions, labels):
    """
    Return the error rate based on dense predictions and 1-hot labels.
    """

    return 100.0 - (
            100.0 *
            np.sum(np.argmax(predictions, 3) == np.argmax(labels, 3)) /
            (predictions.shape[0] * predictions.shape[1] * predictions.shape[2]))


def get_image_summary(img, idx=0):
    """
    Make an image summary for 4d tensor image with index idx
    """

    V = tf.slice(img, (0, 0, 0, idx), (1, -1, -1, 1))
    V -= tf.reduce_min(V)
    V /= tf.reduce_max(V)
    V *= 255

    img_w = tf.shape(img)[1]
    img_h = tf.shape(img)[2]
    V = tf.reshape(V, tf.stack((img_w, img_h, 1)))
    V = tf.transpose(V, (2, 0, 1))
    V = tf.reshape(V, tf.stack((-1, img_w, img_h, 1)))
    return V