# 单图提示词与执行方式

当前默认图见[DEFAULT_STYLE.md](DEFAULT_STYLE.md)。不写模式/标准版均按图直接适配；只有明确场景版先三选一，scene_choice_needed不发图像请求。所有本次传入图包含内置图，都必须实际看过；身份与删人许可分别处理。

模板需按本张任务编译，只保留当前 scenario、placement 和获准开关。人物数量、衣服、动作和文案都是任务数据，不固定双人或某套服装。

Claude用本文件的共用规则编写纯文本提示词，安装、实际附件映射与Grok手动步骤见[CLAUDE_GROK.md](CLAUDE_GROK.md)。下方第2节的工具JSON与helper命令只用于Codex，不是Grok接口；没有对应工具时不要照抄工具名。风格待选时，两端都须等真实答复。

## 1. 最短用户入口

    按 cool-chibi-photo 处理这张照片。先看图，说明本图情境，按标准底子或三个场景选路由。参考图只用于我指定的身份、画风、布局或整体效果。背景默认摄影感，不加新文字；已有本批授权继续沿用。每张单独输出。

用户可直接补“没拍到我，把小人坐到凳子上”“让小人蹲下摸这只猫”“人太小，同意替换为对应Q版”。缺关键身份参考时只阻塞相关图，不假装已经读到历史图片。

## 2. Codex 实际执行

1. 用 view_image 实际查看 source_photo 和本次会传入的每一张参考；必要时再看细节。文件存在、哈希匹配或勾选 inputs_reviewed 不代替看图。
2. 按第7节判断画风是否已经明确，再填 job spec（格式见 ../assets/job.example.json）。references 为数组，每张都有 path、role、use_for；可用 --profile 指定私有 local-profile.json，并通过 reference_ids 只选择本次需要的索引项。
3. 规划时用本地 helper；它只编译、核输入和记录，不负责看图或生图：

    python3 scripts/codex_job.py doctor
    python3 scripts/codex_job.py plan --config work/job-spec.json
    python3 scripts/codex_job.py plan --config work/job-spec.json --profile local-profile.json

4. 只有计划状态为 planned 才执行。读取该目录 imagegen-request.json，将其中 prompt、referenced_image_paths、transparent_background 实际传给当前 Codex 内置 imagegen；所有传入图此前都必须已查看。不能只把路径名写进提示词，或用其他参数猜测接口。
5. 取得本次真正生成的 PNG 后查看结果，按 QA.md 检查；归档工具不会自动判断人物、动作或审美。记录实际视觉报告，再归档：

    python3 scripts/codex_job.py collect --job work/run/job.json --result work/new-result.png --visual-review work/actual-review.json

没有实际视觉报告就省略 --visual-review，保持视觉 pending，不能填预制 pass。实际路径由本次工具返回及 spec 决定；以上相对路径只演示命令，不代表包中已附照片。

## 3. 参考角色必须分清

| role | 允许贡献 | 不自动带入 |
|---|---|---|
| identity | 明确选定人物/宠物的识别特征 | 该参考的衣服、动作、背景、关系 |
| style | 线条、五官概括、角色比例及描边画法 | 同套衣服、手势、家具、文案 |
| layout | 主次、角色视觉占比、装饰密度 | 换人、换景、文字事实 |
| overall | use_for 明确认可的整体效果，如柔和画风和入景方式 | 参考的全部人物、服装、地点、故事自动移入 |

同一图可有多种用途，但每项必须明确；角色服装按当前原片及本批明确说明记录在 subject_details。镜像左右不等于身份。旧成品可以是画风/效果参考，不能假装未编辑原片。

## 4. 四种路由的编译段

### standard

    保留当前原片主角、可见衣服、动作、视线和关键道具；先按授权改善光色与构图，右下加一组对应Q版。原照片仍是主画面。
    这是 visual 整图编辑，检查视觉一致，不声称已像素锁脸或原主体从未被生成重绘。

### no_person

    当前没有需要保留为主角的本人。使用指定角色加入场景；背景路人或桌边手臂不自动计入主角，也不自动删除。
    placement=corner 时右下仅一组，保留纯景主导；placement=in_scene 时在本图明确落点坐靠/站立，匹配透视、尺度、遮挡、光线和接触阴影。不要机械套右下位置。

### pet_object

    保留原照片里的真实宠物/物件及其数量、毛纹、形状与细节，让 subject_details 指定的人类Q版进入场景互动。
    摸猫要有手与猫背接触、合理蹲姿；茶壶旁趴靠要有桌面支撑和正确遮挡。按角色的短身比例设计动作，不为了够到物件拉长身体。
    只有明确选择宠物Q版时才画对应宠物Q版，不自动把真实猫或茶壶替换掉；原真人也不因本场景被删除。

### small_person

    用户已明确授权 replace_real_person=true：只删除 subject_details 指定的小真人及必要影子/反射，局部补齐背后场景，将对应Q版入景替换。
    已有认可资产时锁其设计与比例，清掉旧角落重复小人；不能为了填满真人外接框而拉长腿和躯干。
    若无法可靠提取原资产，说明实际采用参照重绘或局部改画；不声称只是原样平移。未授权时停在推荐记录，不发送替换生图请求。

## 5. 开关附加段

- photo：摄影背景、自然材质和现场光向；克制整理明暗偏色，不借修光删物或换景。
- soft_illustrated：在获准范围柔化笔触和色调，保留空间、主物件与原情境；不自动改成另一处地点。
- clean：无新增装饰；light_journal：少量相关点缀；full_journal：单张主图加纸边、标签等，主图完整可读。都不加第二组重复角色。
- add_text=false：不添加新文字。开启时优先使用给定 text，逐字核对；只授权短文案时不编日期、店名、关系或经历。
- 描边、半身/全身与角色大小依明确参考和情境调整；不能把贴纸的厚白边、安全边距、完整全身要求全盘压给入景角色。

## 6. 严格原主体保留与普通试跑分开

visual 路径：view_image → 计划 → 内置 imagegen 整图编辑 → 查看并归档。它能交付供评图的效果，不保证生成模型从未改变真人或原图像素。

strict_subject 路径目前由 helper 支持 standard：只请求独立透明Q版，collect 只能归档 chibi.png，仍需旧 photo_ops.py 的非生成式底图、真实保护蒙版、合成与 verify-lock。只有实际完成相应检查才报告保护区通过；透明元数据存在不证明边缘正确或实际有透明像素。

不要求每次整图试跑都自动分割出完美图层；没有独立 base/chibi/decor 就写“未提供”，不造空文件。只改动作、位置、文字等也优先最小范围；工具做不到时说明实际重绘范围，不把整图再生成说成无损局部移动。

## 7. 条件画风选择，不固定三种预设

最短可复制要求：

    画风已明确或这批已定下就沿用；我说“你决定”就由你选。只有你确实不确定时，先展示本次实际可读的2～3张角色画风参考，再用当前可用的原生选项让我选；没有原生工具就文字列项。等我回答后再生图，只选角色画风，其他设置不变。

对 helper 的字段：

- resolved（默认）：已有明确选择、认可参考或本批锁定，或画风并无待解决的不确定项。不重复弹窗；不是自动选择第一候选。
- delegate：用户已授权“你决定/你选”。简述采用依据后继续，不把等待用户选项作为必经步骤。
- needed：确实有歧义且没有上述选择或委托。用2～3个实际候选写 style_options；每项必须有独立 id、label 和清楚的 description。选择前不发送 imagegen 请求。

只有在已展示两张真实候选图时，才可把下列字段作为该job的增量示例；A/B是本次图号，不是包内预设风格，也不代表本包附有这两张图：

    "style_selection": "needed",
    "style_options": [
      {"id": "ref_a", "label": "A：上方参考图1", "description": "只采用图1已展示的角色画法与比例"},
      {"id": "ref_b", "label": "B：上方参考图2", "description": "只采用图2已展示的角色画法与比例"}
    ]

先 view_image 并在会话展示候选，label需与图号一一对应；description描述实际区别，不杜撰“效果”。plan的 style_choice_needed 会保存 style-picker.json，其原生问题结构为 questions 数组，每项使用 title 和 options（字符串数组）；不编造 question/header 等其他工具的字段。

当前会话若确实提供 request_user_input_async，可把 style-picker.json 的 questions 原样交给它；不要把整份job或style_options直接当原生工具参数。若原生选择工具不存在或当前模式不可用，直接用同题同项的文字选择。候选少于2张就如实说明并文字澄清，不伪造第二张来通过helper校验。

收到明确答案后只保留选中画风参考的相关用途，设 style_selection=resolved、style_options=[]，新 output_dir 重新plan；其他仍需的身份/布局参考可以保留，但不能让未选中的画风继续混入请求。没有答复、只展示了预选项或等待超时，都不等于已选中，不进入生图。

确认只作用于声明的本图/本批范围。例如“这个效果挺好”可认可当前结果与本批画风，不自动接受其他图、其他参考或未来任务；已确认的本批后续不反复问。
