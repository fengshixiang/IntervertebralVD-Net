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
Toy example, generates images at random that can be used for training

Created on Jul 28, 2016

author: jakeret
'''
from __future__ import print_function, division, absolute_import, unicode_literals

import numpy as np
import glob
import os
from image_util import BaseDataProvider
from parameter import Parameter

class GrayScaleDataProvider(BaseDataProvider):
    channels = 1
    n_class = 2
    
    def __init__(self, nx, ny, **kwargs):
        super(GrayScaleDataProvider, self).__init__()
        self.nx = nx
        self.ny = ny
        self.kwargs = kwargs
        rect = kwargs.get("rectangles", False)
        if rect:
            self.n_class=3
        
    def _next_data(self):
        return create_image_and_label(self.nx, self.ny, **self.kwargs)

class RgbDataProvider(BaseDataProvider):
    channels = 3
    n_class = 2
    
    def __init__(self, nx, ny, **kwargs):
        super(RgbDataProvider, self).__init__()
        self.nx = nx
        self.ny = ny
        self.kwargs = kwargs
        rect = kwargs.get("rectangles", False)
        if rect:
            self.n_class=3

        
    def _next_data(self):
        data, label = create_image_and_label(self.nx, self.ny, **self.kwargs)
        return to_rgb(data), label

def create_image_and_label(nx,ny, cnt = 10, r_min = 5, r_max = 50, border = 92, sigma = 20, rectangles=False):
    
    
    image = np.ones((nx, ny, 1))
    label = np.zeros((nx, ny, 3), dtype=np.bool)
    mask = np.zeros((nx, ny), dtype=np.bool)
    for _ in range(cnt):
        a = np.random.randint(border, nx-border)
        b = np.random.randint(border, ny-border)
        r = np.random.randint(r_min, r_max)
        h = np.random.randint(1,255)

        y,x = np.ogrid[-a:nx-a, -b:ny-b]
        m = x*x + y*y <= r*r
        mask = np.logical_or(mask, m)

        image[m] = h

    label[mask, 1] = 1
    
    if rectangles:
        mask = np.zeros((nx, ny), dtype=np.bool)
        for _ in range(cnt//2):
            a = np.random.randint(nx)
            b = np.random.randint(ny)
            r =  np.random.randint(r_min, r_max)
            h = np.random.randint(1,255)
    
            m = np.zeros((nx, ny), dtype=np.bool)
            m[a:a+r, b:b+r] = True
            mask = np.logical_or(mask, m)
            image[m] = h
            
        label[mask, 2] = 1
        
        label[..., 0] = ~(np.logical_or(label[...,1], label[...,2]))
    
    image += np.random.normal(scale=sigma, size=image.shape)
    image -= np.amin(image)
    image /= np.amax(image)
    
    if rectangles:
        return image, label
    else:
        return image, label[..., 1]

def to_rgb(img):
    img = img.reshape(img.shape[0], img.shape[1])
    img[np.isnan(img)] = 0
    img -= np.amin(img)
    img /= np.amax(img)
    blue = np.clip(4*(0.75-img), 0, 1)
    red  = np.clip(4*(img-0.25), 0, 1)
    green= np.clip(44*np.fabs(img-0.5)-1., 0, 1)
    rgb = np.stack((red, green, blue), axis=2)
    return rgb

para = Parameter()

class oneChannelProvider(BaseDataProvider):
    def __init__(self, search_path, a_min=None, a_max=None, data_suffix="fat.npy",
                 mask_suffix='label.npy', shuffle_data=True, n_class = 2):
        super(oneChannelProvider, self).__init__(a_min, a_max)
        self.data_suffix = data_suffix
        self.mask_suffix = mask_suffix
        self.file_idx = -1
        self.shuffle_data = shuffle_data
        self.n_class = n_class
        
        self.data_files = self._find_data_files(search_path)
        
        if self.shuffle_data:
            np.random.shuffle(self.data_files)
        
        assert len(self.data_files) > 0, "No training files"
        print("Number of files used: %s" % len(self.data_files))
        
        img = self._load_file(self.data_files[0])
        self.channels = 1 if len(img.shape) == 2 else img.shape[-1]
        
    def _find_data_files(self, search_path):
        all_files = glob.glob(search_path)
        return [name for name in all_files if self.data_suffix in name]
    
    def _load_file(self, path, dtype=np.float32):
        fat_path = path.replace(self.data_suffix, "opp.npy")
        fat_img = np.array(np.load(fat_path), dtype=dtype)

        img = np.zeros((fat_img.shape[0], fat_img.shape[1], 1), dtype=dtype)
        img[...,0] = fat_img

        return img

    def _load_label(self, path, dtype=np.bool):
        return np.array(np.load(path), dtype=dtype) 

    def _cylce_file(self):
        self.file_idx += 1
        if self.file_idx >= len(self.data_files):
            self.file_idx = 0 
            if self.shuffle_data:
                np.random.shuffle(self.data_files)
        
    def _next_data(self):
        self._cylce_file()
        image_name = self.data_files[self.file_idx]
        label_name = image_name.replace(self.data_suffix, self.mask_suffix)
        
        img = self._load_file(image_name, np.float32)
        label = self._load_label(label_name, np.bool)
    
        return img,label

    def __call__(self, n):
        train_data, labels = self._load_data_and_label()
        nx = train_data.shape[1]
        ny = train_data.shape[2]
    
        X = np.zeros((n, nx, ny, self.channels))
        Y = np.zeros((n, nx, ny, self.n_class))
    
        X[0] = train_data
        Y[0] = labels
        for i in range(1, n):
            train_data, labels = self._load_data_and_label()
            X[i] = train_data
            Y[i] = labels       
    
        return X, Y

class fourChannelProvider(BaseDataProvider):
    def __init__(self, search_path, a_min=None, a_max=None, data_suffix="fat.npy",
                 mask_suffix='label.npy', shuffle_data=True, n_class = 2):
        super(fourChannelProvider, self).__init__(a_min, a_max)
        self.data_suffix = data_suffix
        self.mask_suffix = mask_suffix
        self.file_idx = -1
        self.shuffle_data = shuffle_data
        self.n_class = n_class
        
        self.data_files = self._find_data_files(search_path)
        
        if self.shuffle_data:
            np.random.shuffle(self.data_files)
        
        assert len(self.data_files) > 0, "No training files"
        print("Number of files used: %s" % len(self.data_files))
        
        img = self._load_file(self.data_files[0])
        self.channels = 1 if len(img.shape) == 2 else img.shape[-1]
        
    def _find_data_files(self, search_path):
        all_files = glob.glob(search_path)
        return [name for name in all_files if self.data_suffix in name]

    
    def _load_file(self, path, dtype=np.float32):
        fat_path = path.replace(self.data_suffix, "fat.npy")
        inn_path = path.replace(self.data_suffix, "inn.npy")
        wat_path = path.replace(self.data_suffix, "wat.npy")
        opp_path = path.replace(self.data_suffix, "opp.npy")
        fat_img = np.array(np.load(fat_path), dtype=dtype)
        inn_img = np.array(np.load(inn_path), dtype=dtype)
        wat_img = np.array(np.load(wat_path), dtype=dtype)
        opp_img = np.array(np.load(opp_path), dtype=dtype)

        img = np.zeros((fat_img.shape[0], fat_img.shape[1], 4), dtype=dtype)
        img[...,0] = fat_img
        img[...,1] = inn_img
        img[...,2] = wat_img
        img[...,3] = opp_img

        return img

    def _load_label(self, path, dtype=np.bool):
        return np.array(np.load(path), dtype=dtype) 

    def _cylce_file(self):
        self.file_idx += 1
        if self.file_idx >= len(self.data_files):
            self.file_idx = 0 
            if self.shuffle_data:
                np.random.shuffle(self.data_files)
        
    def _next_data(self):
        self._cylce_file()
        image_name = self.data_files[self.file_idx]
        label_name = image_name.replace(self.data_suffix, self.mask_suffix)
        
        img = self._load_file(image_name, np.float32)
        label = self._load_label(label_name, np.bool)
    
        return img,label

    def __call__(self, n):
        train_data, labels = self._load_data_and_label()
        nx = train_data.shape[1]
        ny = train_data.shape[2]
    
        X = np.zeros((n, nx, ny, self.channels))
        Y = np.zeros((n, nx, ny, self.n_class))
    
        X[0] = train_data
        Y[0] = labels
        for i in range(1, n):
            train_data, labels = self._load_data_and_label()
            X[i] = train_data
            Y[i] = labels

        if para.RMVD:
            for i in range(0, n):
                if np.random.rand() >para.RMVD_value:
                    tmp = np.random.rand()
                    x = np.zeros((nx, ny))
                    if tmp < 0.25:
                        X[i, ..., 0] = x
                    elif tmp>=0.25 and tmp<0.5:
                        X[i, ..., 1] = x
                    elif tmp>=0.5 and tmp<0.75:
                        X[i, ..., 2] = x
                    elif tmp>=0.75:
                        X[i, ..., 3] = x
                    X[i] = X[i]/0.75        
    
        return X, Y

class eightChannelProvider(BaseDataProvider):
    def __init__(self, search_path, a_min=None, a_max=None, data_suffix="fat.npy",
                 mask_suffix='label.npy', shuffle_data=True, n_class = 2):
        super(eightChannelProvider, self).__init__(a_min, a_max)
        self.data_suffix = data_suffix
        self.mask_suffix = mask_suffix
        self.file_idx = -1
        self.shuffle_data = shuffle_data
        self.n_class = n_class
        
        self.data_files = self._find_data_files(search_path)
        
        if self.shuffle_data:
            np.random.shuffle(self.data_files)
        
        assert len(self.data_files) > 0, "No training files"
        print("Number of files used: %s" % len(self.data_files))
        
        img = self._load_file(self.data_files[0])
        self.channels = 1 if len(img.shape) == 2 else img.shape[-1]
        
    def _find_data_files(self, search_path):
        all_files = glob.glob(search_path)
        return [name for name in all_files if self.data_suffix in name]
    

    def _load_file(self, path, dtype=np.float32):
        fat_path = path.replace(self.data_suffix, "fat.npy")
        inn_path = path.replace(self.data_suffix, "inn.npy")
        wat_path = path.replace(self.data_suffix, "wat.npy")
        opp_path = path.replace(self.data_suffix, "opp.npy")
        fin_path = path.replace(self.data_suffix, "fin.npy")
        win_path = path.replace(self.data_suffix, "win.npy")
        wop_path = path.replace(self.data_suffix, "wop.npy")
        iop_path = path.replace(self.data_suffix, "iop.npy")
        fat_img = np.array(np.load(fat_path), dtype=dtype)
        inn_img = np.array(np.load(inn_path), dtype=dtype)
        wat_img = np.array(np.load(wat_path), dtype=dtype)
        opp_img = np.array(np.load(opp_path), dtype=dtype)
        fin_img = np.array(np.load(fin_path), dtype=dtype)
        win_img = np.array(np.load(win_path), dtype=dtype)
        wop_img = np.array(np.load(wop_path), dtype=dtype)
        iop_img = np.array(np.load(iop_path), dtype=dtype)

        img = np.zeros((fat_img.shape[0], fat_img.shape[1], 8), dtype=dtype)
        img[...,0] = fat_img
        img[...,1] = inn_img
        img[...,2] = wat_img
        img[...,3] = opp_img
        img[...,4] = fin_img
        img[...,5] = win_img
        img[...,6] = wop_img
        img[...,7] = iop_img

        return img

    def _load_label(self, path, dtype=np.bool):
        return np.array(np.load(path), dtype=dtype) 

    def _cylce_file(self):
        self.file_idx += 1
        if self.file_idx >= len(self.data_files):
            self.file_idx = 0 
            if self.shuffle_data:
                np.random.shuffle(self.data_files)
        
    def _next_data(self):
        self._cylce_file()
        image_name = self.data_files[self.file_idx]
        label_name = image_name.replace(self.data_suffix, self.mask_suffix)
        
        img = self._load_file(image_name, np.float32)
        label = self._load_label(label_name, np.bool)
    
        return img,label

    def __call__(self, n):
        train_data, labels = self._load_data_and_label()
        nx = train_data.shape[1]
        ny = train_data.shape[2]
    
        X = np.zeros((n, nx, ny, self.channels))
        Y = np.zeros((n, nx, ny, self.n_class))
    
        X[0] = train_data
        Y[0] = labels
        for i in range(1, n):
            train_data, labels = self._load_data_and_label()
            X[i] = train_data
            Y[i] = labels        
    
        return X, Y

if __name__ == '__main__':
    root_address = para.root_address
    generator_address = os.path.join(root_address, 'data/train/*/*/*.npy')
    generator = oneChannelProvider(generator_address)
    a, b= generator(4)
    print(a.shape)
    print(b.shape)
    print(generator.channels)