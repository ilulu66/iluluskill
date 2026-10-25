---
name: cool-chibi-photo
description: 编辑已有照片，按标准版或没拍到我、宠物小物互动、人太小替换三个场景加入同款Q版。用户说用iluluskill P图、朋友圈照骗、真人加小人、摸猫或小物互动时使用；默认自动适配，明确场景版才弹路由；支持Codex内置图像工具，或Claude分析并交接Grok手动出图。
metadata:
  version: "3.0.0-rc.3"
---

# 朋友圈照骗 · Claude / Codex 三场景版

标准底子保留真人＋右下同款Q版；三个场景处理没人入镜、宠物小物互动、替换小人物。先看实际图片，再按本张情境选择，不让所有照片共用一个右下贴纸模板。

## 用户入口：默认直接做，场景版才弹路由

| 用户怎么说 | 执行行为 |
|---|---|
| “帮我用这个iluluskill P图”或未写模式 | entry_mode=auto，看实际图片后自动选择合适scenario，直接执行；不弹场景菜单 |
| “标准版” | entry_mode=standard，同样直接处理；有清楚真人时保留真人加Q版，缺主角或以宠物小物为主时按照片自动适配 |
| “场景版” | entry_mode=scene，先让用户选下方三个场景；没有明确选择前不生成 |

场景版用当前实际可用的原生选择工具，三项是“没拍到我”“宠物小物互动”“人太小替换”；没有工具时用同样的文字选项。选择等待不能按预选或超时代答。答复后设置scene_choice为no_person / pet_object / small_person并新建计划；已选场景或本批明确方案不重复询问。场景菜单只控制本图做法，画风默认沿用包内参考。

entry_mode只控制交互；内部scenario仍需Agent实际看图确定，helper不识别画面。标准入口遇到本人没入镜时可以用no_person，宠物或小物为主时可用pet_object，不强套右下模板。自动适配不擅自删真人：未获替换许可时保留真人加Q版，明确替换后才用small_person。用户选了表述清楚的替换选项且目标明确，可记录本图许可，不重复问同一件事；helper仍要求replace_real_person=true。

缺少主体时优先用本次已有、明确映射的角色。用户明确要“本人”而缺本人资料时只补问一张本人身份照；未要求特定本人时，可明确说明并采用通用原创角色，不把示例Lulu当使用者本人、不猜真实身份。缺原片等必要信息仍须补齐，不用假图占位。

## 默认画风已内置

默认使用[包内Lulu Q版画风图](assets/lulu-q-style.png)与[规范](references/DEFAULT_STYLE.md)：细腻圆润二维彩色、干净线条、柔和体积阴影、大头短躯干短四肢；新设计约两头身，认可角色比例优先。只借画法和比例，不复制Lulu身份、发型/肤色、黑衣、闭眼笑、坐姿、手势或人数。读者人物、衣服动作与表情按自己的原照。

不必让读者另外找画风图；Agent需实际打开并传入包内图。Codex helper在没有明确文字画风或style参考时自动加入这张图；Claude把它作为实际附件交给用户带到Grok。默认已明确时直接做，不把缺少自备风格图变成弹窗。自己的style参考、style_instructions或已认可角色设计优先；use_builtin_style=false可关闭内置图。风格选择不改变背景、服装或删人许可。

## 先选实际执行方式

- **Codex且当前会话有图像工具**：读取下方“在Codex里执行”，用内置图像工具生成/编辑。
- **Claude / Claude Code**：按共同规则看图、选场景和确认必要选择，再读[CLAUDE_GROK.md](references/CLAUDE_GROK.md)，交付可复制提示词、实际附件顺序与检查项；用户在Grok出图后回传，Claude再检查。不要因缺少Codex专属工具阻塞分析，也不要声称Claude本身已生图。
- **其他没有生图工具的宿主**：同样可交付手动交接材料并停在等待外部结果。没有收到新图前，保持`awaiting_external_result`，不伪造成品或生图成功。

Grok在这里是外部图片编辑工具；本包没有自动Grok连接器，不默认使用API、操作账号或上传照片。具体宿主可用工具以实际会话为准。

## 标准底子：人清楚、想保留

`scenario=standard, placement=corner`。先按授权改善光色、背景和构图，再加对应Q版。背景不能只贴个小人就算美化过：写清本图问题、实际操作、可见收益；没有必要改时说明理由。身份、衣服、动作、主要道具按原片，参考图只贡献指定范围。

普通试跑用 `edit_scope=visual`：选用的图像工具编辑整图，只报告实际视觉保留程度。要求原主体不被生成式重画时，用 `strict_subject` 仅生成透明Q版，再用本地调光底图、保护蒙版和旧合成脚本；不能将整图生成称为严格保脸。详细执行见 [WORKFLOW.md](references/WORKFLOW.md)。

## 场景一：没拍到我

`scenario=no_person`。纯景、天空、远海通常用 `placement=corner`，右下放角色，景物仍占主导。有台阶、板凳、窗边等合理位置时，用 `in_scene`，让角色坐靠/站到空间里，匹配尺度、接触阴影与遮挡。背景路人、桌边手臂不自动变成主角或删除对象；加入的本人形象需实际可读参考或本批明确设计。

## 场景二：宠物、小物

`scenario=pet_object, placement=in_scene`。默认保留真实猫、狗、茶壶、杯子等，让指定人类Q版进入场景互动：蹲着摸到猫背、趴在壶旁、共同端同款盘子。手与对象接触、桌面支撑和前后遮挡要成立；不要默认把真实宠物/小物也动漫化或删除。用户另选宠物Q版时再按明确方案画。详见 [SCENARIOS.md](references/SCENARIOS.md)。

## 场景三：人太小

`scenario=small_person, placement=in_scene`。发现主要人物很小、脸部信息不足时，说明观察并主动推荐替换；保留小真人也是可选方案。用户本图/本批已说替换就沿用，不重复问；仅说美化、脸不像不等于删人授权。

获准后 `replace_real_person=true`：只删除指定真人及必要影子/反射，补齐原位置，再放入对应Q版；其他人不动，右下不留重复小人。复用已认可资产时锁比例与设计，不能为坐满椅子或填满真人轮廓拉长身体。工具无法原样提取就记录“参照重绘”，不冒称无损搬运。

## 参考与设置

- **画风不确定时让用户选**：内置默认已明确时不必询问；已有明确画风、本图/本批认可参考或“你决定”时直接沿用。确实拿不准且缺这些信息时，先展示2～3张实际可读、用途清楚的候选参考，再用当前可用的原生选择工具提问（如request_user_input_async）；没有该工具就给简短文字选项。选择只改变画风，不自动改变衣服、场景、背景或删人许可。界面预选和超时都不算答复；候选不足就如实说，不编图凑数。
- 对应spec用style_selection=needed与2～3项style_options，helper只生成style-picker.json并停在style_choice_needed。用户答复后记录选择，设置resolved并创建新计划；明确委托时用delegate。已有选择不重复问；具体JSON与工具入参见[PROMPTS.md](references/PROMPTS.md)。
- 逐张查看原片与实际选用的参考；生图时实际传入，记录每张为 identity / style / layout / overall 及 use_for。原图锁本张衣服动作；画风图不自动授权复制裙子、手势、文案或故事。
- 已认可角色比例优先；新角色无具体设计时用约两头身、短躯干短四肢。动作和情境可读优先于全身露脚；入景允许自然半身、遮挡和参考中的无白描边。
- `background_render_style=photo` 为默认；用户或明确整体参考选择时可用 `soft_illustrated`，仍保留空间和关键物件，不借此换地点。
- `decoration=clean/light_journal/full_journal`，`add_text` 独立控制；默认不加新文字。完整单图手账也不等于批量拼图。
- 发型/表情/身形设计只按本张授权变化；可见五官要自然，手机遮挡不画穿透眼睛。每位主角/宠物数量、手臂和关键道具都逐项核对。
- 已有明确设置继续生效；只改某一层时冻结满意项。多个相似输入仍逐张映射，不拿旧图或重复图充数。

## 在 Claude 里执行

先实际查看附件，沿用相同场景、参考分工和风格选择规则；待风格与必要删人许可明确后，按[CLAUDE_GROK.md](references/CLAUDE_GROK.md)给出一份完整单图提示词、图1/2/3对应的真实附件清单及回传要求。Claude网页/桌面模式不要求本地Python。没有脚本环境就用文字完成分析与检查；不虚构路径或调用Codex的`view_image`/`imagegen`。

不要把`codex_job.py`生成的工具JSON当作Grok接口。本轮Claude路线默认手动交接，图像出图、用户传回、Claude实际目视都完成后才分别记录；软件与安装检查不代表Claude＋Grok实图链路已验证。

## 在 Codex 里执行

当前会话需有 `view_image` 与内置 `imagegen`。本地helper不调用收费API，不负责视觉判断，也不能单独从终端生成图像。工具接口以当前会话实际说明为准。

1. 查看输入、写 scene_intent 与 subject_details，确定场景和本轮范围。需要本机已认可例图时，检查可选私有 `local-profile.json`，只挑本次所需引用；它不是分发包必需文件。[EXAMPLES.md](references/EXAMPLES.md)列出选参考的方法。
2. 用 [assets/job.example.json](assets/job.example.json) 填实际 spec；路径相对 spec 文件解析。确认已看所有传入图（含本次实际使用的包内默认图）后才设 `inputs_reviewed=true`。运行：

   ```bash
   python3 scripts/codex_job.py doctor
   python3 scripts/codex_job.py plan --config /absolute/job-spec.json
   # 若 spec 使用 reference_ids：加 --profile /absolute/local-profile.json
   ```

3. 读取生成的job。只有`planned`才有可执行的`imagegen-request.json`；`scene_choice_needed`按scene-picker.json等场景选择，`recommendation_needed`等用户替换选择，`needs_input_review`先真正看图，`style_choice_needed`先展示候选并提问。将请求中实际的 `prompt`、`referenced_image_paths`、`transparent_background` 传给内置imagegen；不要虚构模型、mask或输出路径参数。
4. 取得本次新PNG后查看，按 [QA.md](references/QA.md) 写真实视觉记录，再归档：

   ```bash
   python3 scripts/codex_job.py collect --job /absolute/run/job.json --result /absolute/new-generated.png --visual-review /absolute/actual-review.json
   ```

   只有真正拿到的图层才保存；没有base/chibi/decor就明说，不制造空文件。strict路径只得到透明资产时，还需本地合成与保护区核验。
5. 每原片一目录，原片仅链接并哈希；版本另存。技术检查、Agent目视、Lulu接受分开；成品状态`ready_for_user_review`、`user_acceptance=pending`。同一缺陷两次针对性修正仍不合格时说明问题，保留版本，不无限换画风。

Codex安装、依赖、自检见[CODEX_SETUP.md](references/CODEX_SETUP.md)；Claude安装与Grok交接见[CLAUDE_GROK.md](references/CLAUDE_GROK.md)；共用提示词见[PROMPTS.md](references/PROMPTS.md)。

## 版本与范围

3.0.0-rc.3：随包提供Lulu明确授权的纯角色画风图并实际接入默认请求；未写模式/标准版直接适配，场景版才三选一路由。保留Claude/Grok手动交接、原三场景与画风选择、非生成式工具。实图覆盖以[VALIDATION.md](VALIDATION.md)为准，Claude＋Grok尚未端到端实图验证。原片只读，私人照片、人物库和运行记录不进分发包。
