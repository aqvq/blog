# [YOLOv8自制数据集说明](https://github.com/aqvq/aqvq/issues/3)


### 格式

Ultralytics YOLO格式是一种数据集配置格式，允许您定义数据集根目录、训练/验证/测试图像目录或包含图像路径的*.txt文件的相对路径，以及类名字典。下面是一个例子：

```yaml
# Train/val/test sets as 1) dir: path/to/imgs, 2) file: path/to/imgs.txt, or 3) list: [path/to/imgs1, path/to/imgs2, ..]
path: ../datasets/coco8  # dataset root dir
train: images/train  # train images (relative to 'path') 4 images
val: images/val  # val images (relative to 'path') 4 images
test:  # test images (optional)

# Classes (80 COCO classes)
names:
  0: person
  1: bicycle
  2: car
  # ...
  77: teddy bear
  78: hair drier
  79: toothbrush
```

- 此格式的标签应导出为YOLO格式，每张图片一个`*.txt`文件。如果镜像中没有对象，则不需要`*.txt`文件。
- `*.txt`文件的格式应为每个对象一行，格式为`class x_center y_Center Width Height`。
- 框坐标必须采用**标准化的xywh**格式(从0到1)。如果您的box是以像素为单位的，则应将`x_center`和`width`除以图片宽度，并将`y_center`和`height`除以图片高度。
- 类号应为零索引(从0开始)。

## 用法

Python

```python
from ultralytics import YOLO

# Load a model
model = YOLO('yolov8n.pt')  # load a pretrained model (recommended for training)

# Train the model
results = model.train(data='coco8.yaml', epochs=100, imgsz=640)

```

CLI

```bash
# Start training from a pretrained *.pt model
yolo detect train data=coco8.yaml model=yolov8n.pt epochs=100 imgsz=640
```
