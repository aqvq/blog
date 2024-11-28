# [explore-eqa中的三个三维坐标系](https://github.com/aqvq/aqvq/issues/1)

在 Habitat 项目中，坐标系的转换涉及多个代码模块，主要包括相机坐标系、体素坐标系和世界坐标系之间的转换。为了帮助理解，下面用字符画绘制三个坐标系的轴向关系，并结合 Habitat 项目的代码说明它们的用法。

### 1. 世界坐标系 (World Coordinate System)
Habitat 使用右手坐标系作为世界坐标系，`X` 轴朝右，`Y` 轴朝上，`Z` 轴指向外（朝观察者）。在世界坐标系中，物体的位置和方向都是全局的。Habitat 中的坐标转换，例如 `pos_habitat_to_normal()` 和 `pos_normal_to_habitat()`，会涉及此坐标系的使用。

字符画表示：
```
       Y (向上)
       |
       |
       |
       +-------- X (向右)
      /
     /
    Z (指向外，朝观察者)
```

代码示例：
```python
def pos_habitat_to_normal(pts):
    # -90 度绕 X 轴旋转，将 Habitat 坐标系转换到标准右手坐标系
    return np.dot(pts, np.array([[1, 0, 0], [0, 0, 1], [0, -1, 0]]))
```

这段代码表示：Habitat 的世界坐标系在默认情况下，`Y` 轴朝上，`Z` 轴指向观察者；而这里 `pos_habitat_to_normal()` 函数进行坐标系转换，使其符合标准的右手坐标系表示。

### 2. 相机坐标系 (Camera Coordinate System)
相机坐标系的惯例是，`X` 轴向右，`Y` 轴向下，`Z` 轴指向前方（即相机视线方向）。在 Habitat 中，摄像头的位置和方向被用于生成深度图和彩色图，并且涉及相机坐标系和世界坐标系之间的转换。

字符画表示：
```
       Z (指向前方，视线方向)
       |
       |
       |
       +-------- X (向右)
      /
     /
    Y (向下)
```

代码示例：
```python
def get_current_view_mask(self, cam_intr, cam_pose, im_w, im_h):
    cam_pts = rigid_transform(self.cam_pts_pre, np.linalg.inv(cam_pose))
    # 代码中进行了相机坐标到世界坐标的转换
```
在这段代码中，通过 `rigid_transform` 函数，`cam_pose` 的逆矩阵将相机坐标转换到世界坐标系。这是因为在 Habitat 中，相机的观察点首先是根据世界坐标系确定的，然后进行转换以生成深度图等数据。

### 3. 体素坐标系 (Voxel Coordinate System)
体素坐标系用于表示 3D 空间中的离散网格。体素原点通常放置在网格的某个角，`X` 轴、`Y` 轴、`Z` 轴沿着体素网格的三个维度方向。在 Habitat 中，体素坐标系主要用于 TSDF（截断符号距离函数）体积融合中，以更新 3D 地图。

字符画表示：
```
       Y (向上)
       |
       |
       |
       +-------- X (向右)
      /
     /
    Z (指向深度方向)
```

代码示例：
```python
def world2vox(self, pts):
    pts = pts - self._vol_origin
    coords = np.round(pts / self._voxel_size).astype(int)
    coords = np.clip(coords, 0, self._vol_dim - 1)
    return coords
```
在这段代码中，`world2vox()` 函数将世界坐标转换为体素坐标。首先，它将输入点减去体素体积的原点，然后根据体素大小缩放到离散的体素网格中。

### 结合示意图与代码关系
1. **世界坐标系**：表示场景中物体的全局位置，通过 `pos_habitat_to_normal()` 和 `pos_normal_to_habitat()` 函数进行转换。
2. **相机坐标系**：相机坐标系与世界坐标系之间的转换主要通过相机的姿态矩阵 `cam_pose`，以及像 `get_current_view_mask()` 这样的函数来实现。
3. **体素坐标系**：用于构建 3D 地图，`world2vox()` 函数负责将世界坐标转换到体素坐标系，以便在 TSDF 融合中进行更新。

### 总结
- 世界坐标系描述了物体在全局场景中的位置和方向。
- 相机坐标系用于相机的观察，通常是右手系，但 `Y` 轴朝下，`Z` 轴指向前方。
- 体素坐标系是一个离散的网格坐标系，用于 3D 重建和地图更新。

Habitat 项目中，不同坐标系之间的转换是核心部分，比如 TSDF 体积融合过程中涉及相机坐标系和体素坐标系之间的转换。
