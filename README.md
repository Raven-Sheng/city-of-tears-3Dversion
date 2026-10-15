# 泪水之城 3D

使用 Blender 与 Python 构建《空洞骑士》泪水之城的可编辑三维场景。

- 28 个区域的建筑、桥梁、室内空间与地标。
- 程序化构件、区域材质与灯光，以及雨、雾和水面效果。
- 玛丽莎、奎若与长椅独立资产。
- 178 秒、24 fps、4272 帧的相机漫游，支持分镜续渲和静帧输出。

`scripts/` 为建模、材质、镜头与渲染代码，`config/` 为参数，`assets/` 为当前资产，`CityOfTears_Reference/` 为参考图。总图使用 `docs/reference_review/` 中的缩略版本。

使用 Blender 5.2.1 LTS 打开 `scenes/city_animation_v010.blend` 即可编辑或播放相机动画；也可从仓库根目录渲染单帧：

```sh
blender -b scenes/city_animation_v010.blend --python scripts/render/render_delivery_frame.py -- --frame 4230 --camera CAM_V8_S07 --output _work/f4230.png
```

阶段生成脚本需先生成相应的中间工程。仓库仅保留当前场景、核心源码与素材，不含历史工程、成片、渲染序列和缓存；区域正式美术验收尚未全部完成。

《空洞骑士》同人项目，原作与游戏素材归 Team Cherry 所有。
