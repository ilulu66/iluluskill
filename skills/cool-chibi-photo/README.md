# 朋友圈照骗 Skill · Claude / Codex 三场景版

**组件3.0.0-rc.3（试用版），随iluluskill v0.5.0-rc.3分发。** 默认画风参考已随包提供。给已有照片加同款Q版：标准版保留真人，三个场景处理没拍到我、宠物小物互动、人太小替换。画风与当前原片衣服/动作分别指定；背景默认摄影感。

| 照片情况 | 处理方式 |
|---|---|
| 人清楚、想保留 | 保留真人，右下加入同款Q版 |
| 没拍到我 | 按空间选择角落小人或坐进台阶、窗边等合理位置 |
| 宠物或小物 | 保留真实宠物/物件，让指定人类Q版入景互动 |
| 人太小 | 推荐原位替换，取得本图/本批许可后执行 |

画风确实拿不准时，先展示2～3个真实参考，再用当前宿主支持的选择界面或文字让用户选；已指定、已认可本批画风或明确委托决定时直接沿用。选画风不等于许可换衣服、换景或删人。

## 装好就能怎么用

上传想处理的原照，说：

> 帮我用这个iluluskill P图。

不写模式，或写“标准版”，由Agent看图自动适配，不弹场景菜单。想自己控制场景时说：

> 帮我用这个iluluskill P图，场景版。

这时才弹出“没拍到我／宠物小物互动／人太小替换”三个选择，选完再做。默认沿用同一套画风；自动适配不默认删除真人，明确要本人又缺身份资料时只补问必要的本人照片。

## 内置画风参考

![Lulu Q版画风参考，仅用于绘制风格](assets/lulu-q-style.png)

这张Lulu本人Q版已获明确许可随Skill提供，Agent自动定位、实际查看并传入，不用读者再找画风图。默认细腻圆润二维、干净线条、柔和阴影、大头短身；只借画法和比例，其他人的身份、发型、衣服、动作与表情按其原照，不默认画成Lulu或穿黑衣。自己的明确画风/参考仍可覆盖。详见[默认画风规范](references/DEFAULT_STYLE.md)与[图片授权](assets/STYLE-REFERENCE-LICENSE.md)。

## 怎么安装

### Codex

首次安装，在终端运行（需要Node.js/npm提供npx）：

```bash
npx -y skills add ilulu66/iluluskill -g --skill cool-chibi-photo --agent codex -y
```

安装后开新对话，上传原照即可使用默认画风；原照没本人但要画本人时，再补一张本人照。当前会话需能看图并使用内置图像生成/编辑工具，Skill不会附带模型和额度。也可用ZIP安装器；已有`~/.codex/skills/cool-chibi-photo`时，按[CODEX_SETUP.md](references/CODEX_SETUP.md)先备份再原位更新，避免同名副本。

### Claude Code

在终端运行同一Skill的Claude Code安装命令：

```bash
npx -y skills add ilulu66/iluluskill -g --skill cool-chibi-photo --agent claude-code -y
```

安装器为Claude Code建立技能入口，安装后开新对话，给原照即可，默认画风参考由Agent从包内取用。Claude负责看图、选择场景和整理完整提示词；默认由用户带到Grok出图，再回传Claude检查。安装成功不表示已自动连接Grok。已有手动副本时先定位、备份并统一同名入口；包内Python安装器没有Claude参数。

### Claude网页 / 桌面版

这类界面使用ZIP方式：从[本次Release](https://github.com/ilulu66/iluluskill/releases/tag/v0.5.0-rc.3)下载完整Skill ZIP，在Claude的`Customize → Skills`中选择创建/上传Skill并启用。需开启代码执行与文件创建能力，具体入口以当前界面为准；此方式不要求本地npx或Python。详细步骤与[官方安装说明](https://support.claude.com/en/articles/12512180-use-skills-in-claude)见[CLAUDE_GROK.md](references/CLAUDE_GROK.md)。本轮未实际导入Claude网页界面，不把ZIP结构核验当作界面实测。

## Claude怎么配合Grok

Claude本身不直接生成照片或插画；[官方说明](https://support.claude.com/en/articles/9002504-can-claude-produce-images)确认它可以分析上传图片。Grok支持[上传现图并按文字编辑](https://x.ai/grok/use-cases/image-editing)，可以作为这个流程的出图工具：

1. 在Claude中发原照与自己的参考，说“用照骗skill分析这张图，给我可以直接发给Grok的提示词”。
2. Claude先确定场景、实际附件顺序、画风及必要许可，给一份完整单图提示词。
3. 用户到Grok的图片编辑入口上传**同一原照与实际使用的包内画风图/自选参考**，粘贴提示词生成；本地文件路径不会自动上传。
4. 下载真实结果，再回传Claude，检查角色比例、动作接触、原物件保留和画风；需要修改时只改对应部分。

这是**手动交接**。本包没有Grok自动连接器或API服务，Grok无需通过npx安装本Skill；账号可用功能与额度以Grok界面为准。未实际生成/回传前保持等待，不能称已完成。当前新增的是兼容规则与交接说明，Claude＋Grok实图链路尚未端到端验证。

## Codex最短用法与依赖

> 用 $cool-chibi-photo 处理这张图，让小人蹲在猫旁边摸它，保留真实猫与场景，参考图只借画风，不加文字。

Codex的`scripts/codex_job.py`负责doctor/plan/collect，实际看图与生图由当前内置工具完成；helper不单独生图。它与安装器需要Python 3.10+标准库。旧`photo_ops.py`提供非生成式调色、蒙版恢复、右下合成与像素检查，另需[requirements.txt](requirements.txt)中的Pillow和NumPy。Claude手动交接不必运行Codex helper。

- [Claude安装、Grok交接与完整模板](references/CLAUDE_GROK.md)
- [Codex安装与自检](references/CODEX_SETUP.md)
- [场景路由](references/SCENARIOS.md) · [提示词与参数](references/PROMPTS.md)
- [参考选择](references/EXAMPLES.md) · [验收](references/QA.md) · [实际验证范围](VALIDATION.md)

原片只读，私人实拍、人物库与运行记录不进入分发包；本版仅额外分发这张明确授权的纯Q版画风图。原有软件回归与Codex小物互动用户认可结果继承自rc.1；无人景物原片回归、替换比例修订，以及Claude＋Grok实际出图仍有未完成项，不承诺所有场景稳定成功。整图生成不保证原主体像素不变，严格主体保留需实际独立资产、蒙版与合成。

## 授权与联系Lulu

授权见[LICENSE.md](LICENSE.md)：代码PolyForm Noncommercial 1.0.0，文档CC BY-NC 4.0；个人学习研究免费，商业用途须Lulu书面授权并付费。私人素材不因本包获得再分发权，联系方式见[仓库联系区](https://github.com/ilulu66/iluluskill#联系-lulu)。
