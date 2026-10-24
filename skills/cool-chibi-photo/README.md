# 朋友圈照骗 Skill · Codex三场景版

**版本3.0.0-rc.1（试用版），随iluluskill v0.5.0-rc.1分发。** 保留标准版，再支持没拍到我、宠物小物互动、人太小替换。已认可角色设计与当前原片衣服动作分别锁定；背景摄影感默认，可按明确参考选柔和插画感。

| 照片情况 | 处理方式 |
|---|---|
| 人清楚、想保留 | 保留真人，右下加入同款Q版 |
| 没拍到我 | 按空间选择角落小人或坐进台阶、窗边等合理位置 |
| 宠物或小物 | 保留真实宠物/物件，让指定人类Q版入景互动 |
| 人太小 | 推荐原位替换，取得本图/本批许可后执行 |

画风确实拿不准时，先展示2～3个真实参考，再弹出当前宿主支持的选择；没有原生选择工具时用文字选项。已有明确参考、已认可的本批画风，或用户说“你决定”，就直接沿用。

## 安装到Codex

首次安装可在终端运行（需要Node.js/npm提供npx）：

```bash
npx -y skills add ilulu66/iluluskill -g --skill cool-chibi-photo --agent codex -y
```

这条命令只安装照片Skill。也可下载[GitHub试用版ZIP](https://github.com/ilulu66/iluluskill/releases/tag/v0.5.0-rc.1)，解压完整目录后运行`python3 scripts/install.py --codex`。安装器默认不覆盖旧版；若已有`~/.codex/skills/cool-chibi-photo`，采用ZIP方式并运行`--codex --replace`，先备份再原位更新，避免与另一种安装方式留下同名副本。

安装后开启新的Codex对话，附原照与自己的角色/画风参考。当前会话需能看图并使用内置图像生成/编辑工具；安装Skill不会附带模型、额度或API服务。路由helper与安装器需要Python 3.10+；本地非生成式合成另需[requirements.txt](requirements.txt)中的Pillow和NumPy。

## 最短用法

在Codex中读取SKILL.md并给实际照片及必要参考；可以说：

> 用 $cool-chibi-photo 处理这张图，让小人蹲在猫旁边摸它，保留真实猫与场景，参考图只借画风，不加文字。

本地scripts/codex_job.py提供doctor/plan/collect，实际看图与生图调用由Codex内置工具完成，不是独立终端修图引擎。旧photo_ops.py继续提供非生成式调色、蒙版恢复、右下合成和像素检查。

- 安装、自检：[CODEX_SETUP.md](references/CODEX_SETUP.md)
- 场景路由：[SCENARIOS.md](references/SCENARIOS.md)
- 提示词与参数：[PROMPTS.md](references/PROMPTS.md)
- 范例：[EXAMPLES.md](references/EXAMPLES.md)
- 验收：[QA.md](references/QA.md)，实际验证：[VALIDATION.md](VALIDATION.md)

原片只读，参考图库与任务记录不进入分发包。软件测试、生成成功和用户认可分别记录；本版为试跑候选，未覆盖的原片场景见验证记录。

67项软件回归已通过；小物互动已取得一张用户认可结果。无人景物场景尚未完成真实原片生图回归，小人物替换仍有比例修订待收口，不能据此承诺三场景均稳定通过。

授权见[LICENSE.md](LICENSE.md)。个人研究使用与商业授权范围按该文件处理，私人素材不因本包获得再分发权。

## 联系Lulu

商业用途须取得Lulu书面授权并付费，联系方式见[仓库联系区](https://github.com/ilulu66/iluluskill#联系-lulu)。
