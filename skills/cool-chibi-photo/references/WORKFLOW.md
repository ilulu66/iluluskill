# 技术执行与输出

背景/构图的决策见 [BACKGROUND_COMPOSITION.md](BACKGROUND_COMPOSITION.md)，生成与编辑提示词见 [PROMPTS.md](PROMPTS.md)。本页管来源、坐标、合成与验证。

## 1. 输入和基准

按EXIF统一方向；有ICC时转sRGB，记录转换与哈希。原图只读，保存无Q版底图。每位主角编号，按可见证据记录特征、衣服、动作、道具和授权补全；多图各自映射，旧图不作为当前内容原图。

自然调色先解决曝光/偏色，再克制地建立neutral-cool/neutral/warm-soft。脚本grade是全局基础处理，不识别肤色，强混合光需要局部方案与目视检查；不把重采样放大称为细节恢复。

## 2. 两种蒙版

| 用途 | 白/非零含义 | 典型范围 |
|---|---|---|
| restore的keep_mask | 255保留原前景，灰值边缘混合，0使用新背景 | 人物全体、发丝、衣服、毛边、关键桌椅/道具 |
| compose的protect_mask | 非零处禁止贴纸遮挡，0允许叠放 | 原脸、主要手势、道具关键辨识/互动处、必要文字 |

两者分别制作，不能互相复制。衣服/下方头发可以属于原前景保留层，同时允许贴纸在成品中适度覆盖。遮挡是否影响情境仍由视觉判断。生成工具的蒙版语义按其文档转换，不能假定同样白色含义。

蒙版与保护框使用EXIF/ICC规范化后输入照片的坐标；灰度L/1，尺寸相同。几何变换后更新坐标。compose内置crop和padding会自动平移框/蒙版；旋转、缩放、前景组移动需在上游正确变换后另交已配准保护区。

## 3. 背景与构图实现边界

先确定scene_intent、完整前景组、目标画幅和落点。背景板单独生成，再恢复原前景。需要缩放/平移时将人物和关联道具一起变换，并检查接触关系。alpha边缘、发丝/毛边、桌椅遮挡、透视、光向与阴影必须实际查看。

本包脚本支持确定性调色、同尺寸蒙版恢复、裁切、白画布留白、右下合成和像素比较；不提供语义抠图、背景生成、自动前景重排或倾斜校正。其他操作需用当前可用的编辑/合成能力，并记录实际变换；不得因为有构图C选项就声称本脚本已实现它。

pixel_lock仅保护与基准配准后的指定像素；调色/缩放会改变像素值。没有可靠蒙版或透视无法匹配时，不输出重画脸的“保脸成品”。

## 4. 脚本示例

依赖安装在独立虚拟环境，或使用已具备Pillow/NumPy的本地运行时。用户指定本Skill分层工作流时，按宿主图像工具规则使用确定性合成；有额外限制时遵循实际限制。

```bash
python scripts/photo_ops.py grade --input input/photo.jpg --output work/graded.png --preset neutral-cool --strength 0.35 --exposure 0.1
python scripts/photo_ops.py restore --reference work/graded.png --edited work/background.png --keep-mask work/foreground_keep.png --output work/base.png
python scripts/photo_ops.py compose --photo work/base.png --sticker work/chibi.png --protect-mask work/overlay_exclusion.png --width-ratio 0.30 --min-width-ratio 0.22 --output output/final.png
```

compose默认先在右下向内搜索，范围不超过画宽/高12%，在当前可读尺寸找不到位置后才缩小，最小画宽22%。`--max-inset-ratio 0`固定贴右下安全边距；最大允许0.25。无安全位置时失败并解释，不能偷偷关闭保护区或把最小尺寸改到10%。确有小角标要求时才能降低下限。

可另用 `--protect-json assets/protect.example.json` 指定矩形，必须换成本图坐标；它与protect-mask取并集。这些都是叠放禁区，不是自动识别人脸。裁切会拒绝删除已标记禁区；未标记的其他人物/道具仍需人工检查，不能把脚本通过等同构图正确。

只有已授权白边时使用：
```bash
python scripts/photo_ops.py compose --photo work/base.png --sticker work/chibi.png --protect-mask work/overlay_exclusion.png --padding 24 24 140 24 --output output/final-padded.png
python scripts/photo_ops.py pad --input output/final.png --padding 0 0 120 0 --output output/final-right-margin.png
python scripts/photo_ops.py verify-lock --reference work/reference.png --candidate work/result.png --keep-mask work/face_core.png --report output/pixel-check.json
```

padding顺序为左、上、右、下。扩白画布与生成背景延展不同。verify-lock退出码0一致、1有差异、2输入错误；不证明蒙版覆盖了所有脸。

## 5. 贴纸处理与验收

独立生成足够清晰的贴纸，真Alpha，深浅底查看边缘、白衣/眼白和棋盘格残留。半透明RGB底色显示为灰并不证明Alpha无效，须检查通道；不靠删白色实现透明。无用透明空隙可裁去，不能裁掉手脚/装饰；放大不意味着恢复细节。

合成允许非关键衣服/下方头发适度叠放，保护原脸、主要手势、道具辨识区。单人默认30%画宽，手机整图看清表情与核心互动。脚本布局报告包含尺寸、内移量、宽度下限、保护区像素比较；不验证故事、画风、头身或用户认可。

## 6. 任务记录

默认输出base.png、chibi.png、final.png、job.json、qa.json。修改另存版本，记录参考角色与实际提示词、锁定项/修改项、原片哈希、补全依据、背景模式、前景组、几何变换和贴纸位置。

```json
{
  "status": "needs_review",
  "technical_checks": {"files": "pass", "alpha": "pass", "source_unchanged": "pass"},
  "visual_checks": {"scene_intent": "pending", "pose_and_props": "pending", "style_and_proportions": "pending", "face_occlusion_and_visible_features": "pending", "background_and_composition": "pending"},
  "user_acceptance": "pending",
  "unresolved": []
}
```

面部局部遮挡另查：露出的面部是否被错误留空、眼睛是否落在脸的合理位置、是否穿透手机/手；若调整遮挡物，是否仅限已授权Q版设计且仍读得出原动作。这个检查由目视完成，像素测试不判断是否有眼睛。

上例pending必须由实际视觉检查补齐；未检查时总体仍为needs_review。程序通过不能填视觉pass。用户明确拒绝时更新状态和失败原因，技术检查可保留但不能继续标整图通过。
