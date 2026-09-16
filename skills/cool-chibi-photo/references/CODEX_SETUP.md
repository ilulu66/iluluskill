# 装载与运行 · 2.1.1

## 安装与升级

从iluluskill单独安装：

```bash
npx -y skills add ilulu66/iluluskill -g --skill cool-chibi-photo
```

安装参数可先用 `npx -y skills --help` 核对。命令会连接公开仓库，当前Agent的图像能力需要另行检查。下文是下载完整技能目录后使用本地安装脚本的方式。

包根目录为 `cool-chibi-photo`，完整复制文档、references、assets、scripts、tests及校验清单。只复制SKILL.md会缺少被引用的流程和脚本。

先定位当前实际安装。已经在 `~/.codex/skills/cool-chibi-photo` 使用时，备份后原位更新；不要再运行默认安装器造成第二份活动安装。不要混用多个目录的同名不同版本。

本包安装脚本的确定行为：

- 默认安装到 `~/.agents/skills/cool-chibi-photo`。
- `--project /绝对路径/项目` 改为该项目的 `.agents/skills/cool-chibi-photo`。
- `--replace` 先把该目标旧版移到同级 `.agents/skill-backups/`，再安装。
- `--dry-run` 只显示计划；不修改文件。
- 不联网、不安装依赖、不改全局配置。不复制本机维护台账、Python缓存、虚拟环境、环境文件或input/output/work/runs/tmp运行目录。
- 脚本不自动发现其他目录中的同名安装，需执行者先检查。

```bash
python3 scripts/install.py --dry-run
python3 scripts/install.py
# 目标确有旧版、需要升级时：
python3 scripts/install.py --replace
```

在当前客户端确认实际加载路径和版本；如果选择器未刷新，可开启新会话或重启客户端后检查。能发现技能不等于能生成图像。

## 首次自检

```text
读取已安装的 cool-chibi-photo/SKILL.md，报告路径与版本，检查同名冲突。
确认当前真实的读图、生图/编辑与本地合成能力；有imagegen技能时读取其当前说明。
只做路径、依赖与脚本自检，不生成图片，不修改原照片。
```

## 能力边界

- Skill提供情境识别、参考分工、背景/构图计划、分层流程和验收要求。
- 当前可用图像工具负责Q版及获准的背景生成；遵守其实际接口与编辑规则。
- 本地脚本负责非生成式调色、指定蒙版像素恢复、裁切/白边、右下合成与像素核验。
- 蒙版需实际制作；脚本不分割人物、不识别脸、不自动重构画面。
- 视觉检查负责动作、画风、比例、人数、服装及背景光影合理性；最终接受由用户决定。

无图像能力时说明受阻步骤，不以旧图充数。API替代方案只在用户要求或已授权时采用，本包没有自动API调用或费用设置。

## 脚本环境

Python 3.10+，Pillow与NumPy；优先复用现有依赖环境。需要新环境时：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
```

基本命令：

```bash
python scripts/photo_ops.py grade --input input/photo.jpg \
  --output work/graded.png --preset neutral-cool --strength 0.35 --exposure 0.1

python scripts/photo_ops.py restore --reference work/graded.png \
  --edited work/background.png --keep-mask work/keep_foreground.png \
  --output work/base.png

python scripts/photo_ops.py compose --photo work/base.png --sticker work/chibi.png \
  --protect-mask work/no_overlay.png --width-ratio 0.30 --min-width-ratio 0.22 \
  --margin-ratio 0.035 --output output/final.png

python scripts/photo_ops.py verify-lock --reference work/base.png \
  --candidate output/final.png --keep-mask work/face_core.png \
  --report output/pixel_check.json
```

两种蒙版不同：restore的keep-mask保留完整原前景；compose的protect-mask只禁止贴纸覆盖关键区域。后者不能直接使用前者，否则容易把贴纸越缩越小。具体坐标转换与局限见 [WORKFLOW.md](WORKFLOW.md)。

compose先在右下局部内移、再缩小，默认下限22%画宽；不够则报错并调整方案。它不会自动加白边或生成延展背景。经用户授权仅加右边白边时可用：

```bash
python scripts/photo_ops.py pad --input output/final.png \
  --padding 0 0 120 0 --output output/final_right_margin.png
```

verify-lock返回0表示指定255核心区RGB相同，1表示不同，2表示输入错误。基准必须与结果同坐标同尺寸；它不验证蒙版是否准确、动作是否正确或身份是否相似。

## 延伸资料

以下是产品资料入口；实际能力以当前会话为准，本次维护未重新核验网页：
- [Codex skills](https://developers.openai.com/codex/skills/)
- [Image generation API](https://developers.openai.com/api/docs/guides/image-generation)

本技能的比例起点、22%尺寸下限和3.5%边距是设计约定，不是API参数或效果保证。
