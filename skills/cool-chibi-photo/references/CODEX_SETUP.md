# Codex安装与首次运行 · 3.0.0-rc.3

当前默认图见[DEFAULT_STYLE.md](DEFAULT_STYLE.md)。不写模式/标准版均按图直接适配；只有明确场景版先三选一，scene_choice_needed不发图像请求。所有本次传入图包含内置图，都必须实际看过；身份与删人许可分别处理。

## 使用环境

Skill是给Codex读的路由、提示词和本地helper。Codex当前会话需要能实际看图和调用内置imagegen；终端helper本身不生成图片，不需要API key。没有内置生图能力时明确受阻步骤，不擅自切收费API。

首次安装可用npx（需Node.js/npm），只选择照片Skill与Codex：

```bash
npx -y skills add ilulu66/iluluskill -g --skill cool-chibi-photo --agent codex -y
```

也可从[试用版Release](https://github.com/ilulu66/iluluskill/releases/tag/v0.5.0-rc.3)下载ZIP。解压整个cool-chibi-photo目录，不仅复制SKILL.md。已有同名活动版时先定位和备份，在同一目录更新，避免多个版本竞争发现。尤其已有~/.codex/skills版本时，采用下方ZIP安装器原位更新；两种方式择一。

```bash
# 在解压目录运行；明确选择Codex位置
python3 scripts/install.py --codex --dry-run
python3 scripts/install.py --codex
# 已有版本且需要备份替换
python3 scripts/install.py --codex --replace --dry-run
python3 scripts/install.py --codex --replace
```

--codex目标为~/.codex/skills/cool-chibi-photo；备份在~/.codex/skill-backups/，不改全局配置、不联网。历史默认安装到~/.agents保留兼容，Codex用户明确用--codex，不能在本机已有活动版之外再安装一份。--project用于明确的项目级安装，与--codex互斥。

更新后让Codex读取实际路径和版本；已打开会话的技能描述可能仍是旧快照，必要时开启新会话刷新。能发现Skill与能用图像工具是独立检查。

## 自检与本地辅助

```bash
python3 scripts/codex_job.py doctor
python3 scripts/codex_job.py plan --config /absolute/spec.json
python3 scripts/codex_job.py collect --job /absolute/run/job.json --result /absolute/new.png
```

codex_job.py只用Python 3.10+标准库：校验输入、选择路由、编译当前内置图像工具参数、核原片哈希、归档PNG与任务记录。doctor报告本地条件，不假装已经探测到Codex内置工具。

photo_ops.py提供grade/restore/compose/pad/verify-lock，需Pillow和NumPy；沿用2.2.0实现，compose只做右下附近布局，不是任意位置入景或补景引擎。复用宿主已有依赖；仅在确实需要新环境时按requirements.txt安装。

```bash
python3 -m unittest discover -s tests -v
```

此命令需运行在已有Pillow、NumPy的Python环境；纯stdlib helper测试也可单跑test_codex_job.py。软件测试不证明人物相似度、交互动作、审美或用户接受。

## 可选私有参考索引

本机的local-profile.json可含references数组，每项有id/path/role/use_for。任务spec用reference_ids选取，并向plan显式传--profile。未选择的历史图片不自动进入请求；人物身份、当日衣服按本次原片与明确映射，不从图库猜。

私有profile及图片不随包分发；新设备提供自己的参考即可，不依赖原作者绝对路径。原片只链接，不复制进分发包。运行记录与生成结果放调用者指定输出目录。

## 真实能力与验收

普通视觉编辑可直接使用内置imagegen；严格原主体保留走独立透明资产＋本地底图/蒙版/合成。helper的PNG结构、CRC和哈希检查不等于完整像素解码、透明边缘合格或视觉通过。调用者需要实际打开结果，必要时用Pillow解码并按QA逐项目视。只在实际检查后记录通过。

## 画风选择

拿不准且未获选择时，spec设置style_selection=needed，提供2～3个真实可用参考候选（style_options含id/label/可选description）。plan只产生style-picker.json与style_choice_needed任务，不生成图像请求。Codex先展示候选图，再把picker参数传给当前可用原生提问工具；用户答复后创建resolved新计划。明确委托用delegate。没有原生工具则文字选项，不能自动采用界面预选或超时继续。已有本图/本批确认不重复提问。
