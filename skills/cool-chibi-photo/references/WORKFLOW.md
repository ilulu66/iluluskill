# 图像执行路径

当前默认图见[DEFAULT_STYLE.md](DEFAULT_STYLE.md)。不写模式/标准版均按图直接适配；只有明确场景版先三选一，scene_choice_needed不发图像请求。所有本次传入图包含内置图，都必须实际看过；身份与删人许可分别处理。

每张先写清情境、输入参考分工和本轮修改范围。通用场景判断见SCENARIOS；本文件解决实际如何执行。

**Claude / Claude Code**先走[CLAUDE_GROK.md](CLAUDE_GROK.md)的手动交接：Claude分析与编写提示词→用户上传原照/选中参考到Grok生成/编辑→回传Claude实际检查。以下helper、内置imagegen与严格主体合成是Codex执行路径，不是Claude默认必经步骤，也不表示已自动连上Grok。

## 视觉编辑（标准与三个场景的普通试跑）

view_image逐张查看 → spec与plan → 读取imagegen-request.json → 实际内置imagegen → 查看输出 → 写真实视觉记录 → collect。

这里的图像编辑由内置工具完成。本地helper不自动分割、识别人脸、提取已有小人或调用云端API。输出是完整PNG也可交付，不要为了“分层”制造不存在的base/chibi/decor。源图只读，PNG另存；改动范围与工具实际行为都记录。

- 标准版检查主角身份、表情、衣服、动作和场景是否视觉对应，不称像素未变。
- 入景检查落点、前后遮挡、尺度和接触阴影，不机械套贴纸的尺寸下限或边距。
- 替换仅删指定真人；广告里的人像、其他人和未选对象不随之删除。缺原Q版资产时可按授权新画，明说参照重绘，不能说只平移。
- 局部修订优先从最新认可图开始。复用资产只移动时用等比合成；工具只能重绘时说明真实范围，不将生成式编辑称无损。

## 严格原主体保留（当前只为standard提供辅助入口）

1. 通过原片只读生成非生成式调光底图。先实际判断曝光、白平衡、肤色与背景层次，按最新授权改善；只套微量全局参数不代表已做局部美化。
2. spec设standard、edit_scope=strict_subject。helper只编译独立透明Q版请求；collect保存chibi.png，composition_required=true，不能当最终成片。
3. 实际制作必要蒙版，再用photo_ops.py compose。原主体保留蒙版与贴纸禁遮挡区是两件事：restore保留完整原前景；compose只禁贴纸压住脸、主要手势、关键道具及必要文字。
4. compose默认在右下局部内移、再缩小。参数只用于corner贴纸路径；它不做任意坐标的场景融合。
5. 需要保留区域像素校验时用verify-lock对齐同尺寸同坐标基准。它只比较keep-mask=255指定区RGB，不验证蒙版是否圈对或动作语义。

```bash
python3 scripts/photo_ops.py grade --input input.jpg --output base.png --preset neutral-cool --strength 0.35 --exposure 0.1
python3 scripts/photo_ops.py compose --photo base.png --sticker chibi.png --protect-mask no_overlay.png --output final.png
python3 scripts/photo_ops.py verify-lock --reference base.png --candidate final.png --keep-mask face_core.png --report pixel_check.json
```

数值只是命令示例，不是每图固定滤镜。背景A/B/C和构图专项保留在[BACKGROUND_COMPOSITION.md](BACKGROUND_COMPOSITION.md)，只在实际采用这些旧版分层设置时读取；它不覆盖三场景的新入景规则。

## 整体收益与边界

原图→底图（实际有时）→终图同尺寸比较：自然光色、背景主次、构图各写实际收益或保留理由；再查Q版和装饰。不要把Alpha、贴纸没盖脸、文件能解码当整体好看。

真人自然修饰仅按授权：局部补光、偏色和暂时油光可适度整理，保留本人结构与纹理。生成式修饰如实记录，不能同时宣称原主体零重绘。未知衣服/身体和不清楚五官分别记未见与获准设计补全。

候选输出等待用户评图；技术、视觉与用户接受分别记录。
