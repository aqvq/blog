# [CUB转YOLO数据集](https://github.com/aqvq/aqvq/issues/4)

参考文章：
[CUB_200_2011数据集转Yolo格式 - 哔哩哔哩 (bilibili.com)](https://www.bilibili.com/read/cv21940047/#:~:text=%E6%89%80%E4%BB%A5CUB%E6%95%B0%E6%8D%AE%E9%9B%86,%EF%BC%8C%E8%AF%B7%E5%9C%A8__get)

CUB数据集下载：
https://data.caltech.edu/records/65de6-vp158/files/CUB_200_2011.tgz

在此基础上添加细粒度类别，自动生成数据集yaml配置文件，具体源码如下：

```python
import os  
import cv2  
  
  
class Manager:  
    def __init__(self, path, target, train=True):  
        self.class_names = None  
        self.root = path  
        self.target = target  
        self.is_train = train  
        self.images_path = {}  
        self.phase_name = 'train' if train else 'val'  
        with open(os.path.join(self.root, 'images.txt')) as f:  
            for line in f:  
                image_id, path = line.split()  
                self.images_path[image_id] = path  
  
        # 获取类别标签dict  
        self.class_ids = {}  
        with open(os.path.join(self.root, 'image_class_labels.txt')) as f:  
            for line in f:  
                image_id, class_id = line.split()  
                self.class_ids[image_id] = class_id  
  
        # 获取标注框  
        self.bondingbox = {}  
        with open(os.path.join(self.root, 'bounding_boxes.txt')) as f:  
            for line in f:  
                image_id, x, y, w, h = line.split()  
                x, y, w, h = float(x), float(y), float(w), float(h)  
                self.bondingbox[image_id] = (x, y, w, h)  
  
        # 获取train/test数据id列表  
        self.data_id = []  
        if self.is_train:  
            with open(os.path.join(self.root, 'train_test_split.txt')) as f:  
                for line in f:  
                    image_id, is_train = line.split()  
                    if int(is_train):  
                        self.data_id.append(image_id)  
        if not self.is_train:  
            with open(os.path.join(self.root, 'train_test_split.txt')) as f:  
                for line in f:  
                    image_id, is_train = line.split()  
                    if not int(is_train):  
                        self.data_id.append(image_id)  
  
    def transfer(self):  
        # 清空 train.txt / val.txt        path_file_clear = open(os.path.join(self.target, (self.phase_name + '.txt')), 'w')  
        path_file_clear.close()  
        for i in range(self.__len__()):  
            image, file_name, x, y, w, h, label = self.__getitem__(i)  
            file_path = os.path.join(self.target, 'images', self.phase_name, file_name)  
            cv2.imwrite(file_path, image)  
            print(f"Write image {file_path}")  
            label_file = open(os.path.join(self.target, 'labels', self.phase_name, (os.path.splitext(file_name)[0] +  
                                                                                    '.txt')), 'w')  
            label_file.write('{} {} {} {} {}'.format(label, x, y, w, h))  
            label_file.close()  
            path_file = open(os.path.join(self.target, (self.phase_name + '.txt')), 'a')  
            path_file.write('{}{}'.format(('\n' if i != 0 else ''), file_path))  
            path_file.close()  
  
    def write_yaml(self):  
        self.class_names = {}  
        with open(os.path.join(self.root, 'classes.txt')) as f:  
            for line in f:  
                class_id, class_name = line.split()  
                class_name = class_name.split('.')[-1]  
                self.class_names[class_id] = class_name  
  
        with open(os.path.join(self.target, 'data.yaml'), 'w') as f:  
            f.write('path: {}\n'.format(self.target))  
            f.write('train: images/train\n')  
            f.write('val: images/val\n')  
            f.write('test: \n')  
            f.write('names:\n')  
            for k, v in self.class_names.items():  
                f.write('  {}: {}\n'.format(int(k) - 1, v))  
        print("Write yaml file successfully!")  
  
    def __len__(self):  
        return len(self.data_id)  
  
    def __getitem__(self, index):  
        image_id = self.data_id[index]  
        label = int(self._get_class_by_id(image_id)) - 1  
        path = self._get_path_by_id(image_id)  
        file_name = os.path.basename(path)  
        image = cv2.imread(os.path.join(self.root, 'images', path))  
        width = image.shape[1]  
        height = image.shape[0]  
        x, y, w, h = self.bondingbox[image_id]  
        x = (x + (w / 2)) / width  
        w /= width  
        y = (y + (h / 2)) / height  
        h /= height  
  
        return image, file_name, x, y, w, h, label  
  
    def _get_path_by_id(self, image_id):  
  
        return self.images_path[image_id]  
  
    def _get_class_by_id(self, image_id):  
  
        return self.class_ids[image_id]  
  
    def _get_bbox_by_id(self, image_id):  
  
        return self.bondingbox[image_id]  
  
  
def mkdirs(path):  
    if not os.path.exists(path):  
        os.makedirs(path)  
    for phase in ['train', 'val']:  
        images_path = os.path.join(path, 'images', phase)  
        labels_path = os.path.join(path, 'labels', phase)  
        if not os.path.exists(images_path):  
            os.makedirs(images_path)  
        if not os.path.exists(labels_path):  
            os.makedirs(labels_path)  
  
  
if __name__ == "__main__":  
    # 原数据集根目录  
    root = r'E:\Datasets\CUB_200_2011\CUB_200_2011'  
    # 目标yolo格式数据集根目录 - 须是完整绝对路径  
    des = r'E:\Datasets\CUB_YOLO'  
    # 创建目标路径下的文件夹  
    mkdirs(des)  
    manager_train = Manager(root, des, train=True)  
    manager_train.transfer()  
    manager_val = Manager(root, des, train=False)  
    manager_val.transfer()  
    manager_val.write_yaml()  
    print('Finished!')
```

数据集说明参考文章： #3 