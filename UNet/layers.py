from __future__ import print_function, division, absolute_import, unicode_literals

import tensorflow as tf
import numpy as np

def weight_variable(shape, stddev=0.1, name="weight"):
    initial = tf.truncated_normal(shape, stddev=stddev)
    return tf.Variable(initial, name=name)

def weight_variable_devonc(shape, stddev=0.1, name="weight_devonc"):
    return tf.Variable(tf.truncated_normal(shape, stddev=stddev), name=name)

def bias_variable(shape, name="bias"):
    initial = tf.constant(0.1, shape=shape)
    return tf.Variable(initial, name=name)

def conv2d(x, in_dim, out_dim, keep_prob_, training):
    with tf.name_scope("conv2d"):
        stddev = np.sqrt(2 / (3 ** 2 * out_dim))
        w = weight_variable([3, 3, in_dim, out_dim], stddev, name="w")
        b = bias_variable([out_dim], name='b')
        conv2d = tf.nn.bias_add(tf.nn.conv2d(x, w, strides=[1, 1, 1, 1], padding="SAME"), b)
        conv2d = tf.layers.batch_normalization(conv2d, training=training, name=w.name[:-2]+'/bn')
        conv2d = tf.nn.dropout(conv2d, keep_prob_)
        return tf.nn.relu(conv2d)

def conv2d_2(x, in_dim, out_dim, keep_prob_):
    with tf.name_scope("conv2d"):
        stddev = np.sqrt(2 / (3 ** 2 * 32))
        w = weight_variable([3, 3, in_dim, out_dim], stddev, name="w")
        #w = weight_variable([1, 1, in_dim, out_dim], stddev, name="w")
        b = bias_variable([out_dim], name='b')
        conv_2d = tf.nn.conv2d(x, w, strides=[1, 1, 1, 1], padding="SAME")
        conv_2d_b = tf.nn.bias_add(conv_2d, b)
        return tf.nn.dropout(conv_2d_b, keep_prob_)

def rmvd_layer(x, out_dim, ratio, name):
    with tf.name_scope("rmvd_layer_{}".format(name)):
        squeeze = tf.reduce_mean(x, axis=[1,2])
        excitation = tf.layers.dense(inputs=squeeze, use_bias=False, units=int(out_dim//ratio), name="scSE_{}_1".format(name))
        excitation = tf.nn.relu(excitation)
        excitation = tf.layers.dense(inputs=excitation, use_bias=False, units=out_dim, name="scSE_{}_2".format(name))
        excitation = tf.nn.sigmoid(excitation)

        excitation = tf.reshape(excitation, [-1,1,1,out_dim])
        scale = x * excitation

        return scale, excitation

def cSE_layer(x, out_dim, ratio, name):
    with tf.name_scope("SE_{}".format(name)):
        squeeze = tf.reduce_mean(x, axis=[1,2])
        #squeeze = global_avg_pool(x)
        excitation = tf.layers.dense(inputs=squeeze, use_bias=False, units=int(out_dim//ratio), name="scSE_{}_1".format(name))
        excitation = tf.nn.relu(excitation)
        excitation = tf.layers.dense(inputs=excitation, use_bias=False, units=out_dim, name="scSE_{}_2".format(name))
        excitation = tf.nn.sigmoid(excitation)

        excitation = tf.reshape(excitation, [-1,1,1,out_dim])
        scale = x * excitation

        return scale

def deconv2d(x, in_dim, out_dim, training):
    with tf.name_scope("deconv2d"):
        stddev = np.sqrt(2 / (3 ** 2 * out_dim))
        #wd = weight_variable([2, 2, out_dim, in_dim], stddev, name="wd")
        wd = weight_variable([3, 3, out_dim, in_dim], stddev, name="wd")
        x_shape = tf.shape(x)
        output_shape = tf.stack([x_shape[0], x_shape[1]*2, x_shape[2]*2, x_shape[3]//2])
        deconv_2d = tf.nn.conv2d_transpose(x, wd, output_shape, strides=[1, 2, 2, 1], padding='SAME', name="conv2d_transpose")
        #deconv_2d = tf.layers.batch_normalization(deconv_2d, training=training)
        deconv_2d = tf.nn.relu(deconv_2d)
        return deconv_2d

def deconv2d_2(x, in_dim, out_dim, larger, training):
    with tf.name_scope("deconv2d"):
        stddev = np.sqrt(2 / (3 ** 2 * out_dim))
        x_shape = tf.shape(x)
        new_x = tf.image.resize_bilinear(x, size=[larger*x_shape[1], larger*x_shape[2]])
        w = weight_variable([3, 3, in_dim, out_dim], stddev, name="w")
        b = bias_variable([out_dim], name='b')
        conv_2d = tf.nn.conv2d(new_x, w, strides=[1, 1, 1, 1], padding="SAME")
        conv2d_b = tf.nn.bias_add(conv_2d, b)
        return conv2d_b

def deconv2d_xz(x, in_dim, out_dim, stride1, stride2, training):
    with tf.name_scope("deconv2d"):
        stddev = np.sqrt(2 / (3 ** 2 * out_dim))
        wd = weight_variable([2, 2, out_dim, in_dim], stddev, name="wd")
        x_shape = tf.shape(x)
        output_shape = tf.stack([x_shape[0], x_shape[1]*stride1, x_shape[2]*stride2, x_shape[3]//2])
        deconv_2d = tf.nn.conv2d_transpose(x, wd, output_shape, strides=[1, stride1, stride2, 1], padding='SAME', name="conv2d_transpose")
        #deconv_2d = tf.layers.batch_normalization(deconv_2d, training=training)
        deconv_2d = tf.nn.relu(deconv_2d)
        return deconv_2d

def deconv2d_xz_2(x, in_dim, out_dim, larger1, larger2, training):
    with tf.name_scope("deconv2d"):
        stddev = np.sqrt(2 / (3 ** 2 * out_dim))
        x_shape = tf.shape(x)
        new_x = tf.image.resize_bilinear(x, size=[larger1*x_shape[1], larger2*x_shape[2]])
        w = weight_variable([3, 3, in_dim, out_dim], stddev, name="w")
        b = bias_variable([out_dim], name='b')
        conv_2d = tf.nn.conv2d(new_x, w, strides=[1, 1, 1, 1], padding="SAME")
        conv2d_b = tf.nn.bias_add(conv_2d, b)
        return conv2d_b

def inception_conv(x, in_dim, out_dim, keep_prob_, training):
    with tf.name_scope("conv2d"):
        stddev = np.sqrt(2 / (3 ** 2 * out_dim))

        w0 = weight_variable([3, 3, in_dim, out_dim], stddev, name="w0")
        conv2d_0 = tf.nn.conv2d(x, w0, strides=[1, 1, 1, 1], padding="SAME")
        conv2d_0 = tf.layers.batch_normalization(conv2d_0, training=training, name=w0.name[:-2]+'/bn')
        conv2d_0 = tf.nn.relu(conv2d_0)

        w1 = weight_variable([1, 1, out_dim, out_dim], stddev, name="w1")
        conv2d_1 = tf.nn.conv2d(conv2d_0, w1, strides=[1, 1, 1, 1], padding="SAME")
        b1 = bias_variable([out_dim], name="b1")
        conv2d_1 = tf.nn.bias_add(conv2d_1, b1)
        #conv2d_1 = tf.layers.batch_normalization(conv2d_1, training=training, name=w1.name[:-2]+'/bn')
        conv2d_1 = tf.nn.relu(conv2d_1)

        w2 = weight_variable([3, 3, out_dim, out_dim], stddev, name="w2")
        conv2d_2 = tf.nn.conv2d(conv2d_0, w2, strides=[1, 1, 1, 1], padding="SAME")
        b2 = bias_variable([out_dim], name="b2")
        conv2d_2 = tf.nn.bias_add(conv2d_2, b2)
        #conv2d_2 = tf.layers.batch_normalization(conv2d_2, training=training, name=w2.name[:-2]+'/bn')
        conv2d_2 = tf.nn.relu(conv2d_2)

        w3 = weight_variable([5, 5, out_dim, out_dim], stddev, name="w3")
        conv2d_3 = tf.nn.conv2d(conv2d_0, w3, strides=[1, 1, 1, 1], padding="SAME")
        b3 = bias_variable([out_dim], name="b3")
        conv2d_3 = tf.nn.bias_add(conv2d_3, b3)
        #conv2d_3 = tf.layers.batch_normalization(conv2d_3, training=training, name=w3.name[:-2]+'/bn')
        conv2d_3 = tf.nn.relu(conv2d_3)

        w4 = weight_variable([3, 3, out_dim, out_dim], stddev, name="w4")
        conv2d_4 = tf.nn.atrous_conv2d(conv2d_0, w4, rate=2, padding="SAME")
        b4 = bias_variable([out_dim], name="b4")
        conv2d_4 = tf.nn.bias_add(conv2d_4, b4)
        #conv2d_4 = tf.layers.batch_normalization(conv2d_4, training=training, name=w4.name[:-2]+'/bn')
        conv2d_4 = tf.nn.relu(conv2d_4)

        w5 = weight_variable([3, 3, out_dim, out_dim], stddev, name="w5")
        conv2d_5 = tf.nn.atrous_conv2d(conv2d_0, w5, rate=4, padding="SAME")
        b5 = bias_variable([out_dim], name="b5")
        conv2d_5 = tf.nn.bias_add(conv2d_5, b5)
        #conv2d_5 = tf.layers.batch_normalization(conv2d_5, training=training, name=w5.name[:-2]+'/bn')
        conv2d_5 = tf.nn.relu(conv2d_5)

        conv2d_input = tf.concat([conv2d_1, conv2d_2, conv2d_3, conv2d_4, conv2d_5], axis=3)
        w6 = weight_variable([1, 1, out_dim*5, out_dim], stddev, name="w6")
        conv2d_6 = tf.nn.conv2d(conv2d_input, w6, strides=[1, 1, 1, 1], padding="SAME")
        conv2d_6 = tf.layers.batch_normalization(conv2d_6, training=training, name=w6.name[:-2] + '/bn')
        conv2d_6 = tf.nn.relu(conv2d_6)

        conv2d = conv2d_6 + conv2d_0
        w = weight_variable([3, 3, out_dim, out_dim], stddev, name="w")
        conv2d_output = tf.nn.conv2d(conv2d, w, strides=[1, 1, 1, 1], padding="SAME")
        conv2d_output = tf.layers.batch_normalization(conv2d_output, training=training, name=w.name[:-2] + '/bn')
        conv2d_output = tf.nn.relu(conv2d_output)

        return conv2d_output

def max_pool(x, n):
    return tf.nn.max_pool(x, ksize=[1, n, n, 1], strides=[1, n, n, 1], padding='VALID')

def max_pool_xz(x, n1, n2):
    return tf.nn.max_pool(x, ksize=[1, n1, n2, 1], strides=[1, n1, n2, 1], padding='VALID')

def pixel_wise_softmax(output_map):
    with tf.name_scope("pixel_wise_softmax"):
        max_axis = tf.reduce_max(output_map, axis=3, keepdims=True)
        exponential_map = tf.exp(output_map - max_axis)
        normalize = tf.reduce_sum(exponential_map, axis=3, keepdims=True)
        return exponential_map / normalize

def cross_entropy(y_,output_map):
    return -tf.reduce_mean(y_*tf.log(tf.clip_by_value(output_map,1e-10,1.0)), name="cross_entropy")
