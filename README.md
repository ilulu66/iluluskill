# iluluskill · 会客厅 skill

> Lulu 的开源 skill 总箱,中文名「**会客厅 skill**」(出自「Lulu 的会客厅」)。
> 当前包含两个系列和一件独立照片工具:
> - **lulu-learn 学习工坊**——把一场 3 小时的讲座,做成一份可回访的学习资产。别人做压缩,我们做加工:压缩丢真相,加工保真相。
> - **lulu-consult 咨询流水线**——把一次专业对话,变成客户当天收到的报告 + 一颗进你自己库的经验原子。
> - **cool-chibi-photo 照片创作**——保留真实照片,在右下角加入还原人物或宠物情境与动作的同款Q版。

**状态:v0.3 可安装公开快照(2026-09-16),共8个Skill。** 新增 cool-chibi-photo 2.1.1；学习工坊明档仍为数据契约版。

## 命名三层

```
iluluskill / 会客厅skill      ← 总箱(本仓库,一条命令装全家)
├── lulu-learn / 学习工坊     ← 系列(讲座/课程/工作坊/书)
│   └── lulu-learn-intake     ← 件:具体 skill
├── lulu-consult / 咨询流水线 ← 系列(咨询/售前/访谈/答疑)
└── cool-chibi-photo / 照片创作 ← 独立工具(真实照片＋同款Q版)
```

新的系列或独立工具都可进同一个箱,全量安装命令不变。按具体Skill名或下方场景调用,避免不同流程混用。

## 为什么有 lulu-learn

市面的 AI 纪要工具(一键摘要)有一个根病:**AI 摘要会在原话空白处补全**——这是我们拿 2500+ 分钟逐字稿逐段校准实测出来的。所以这套流程的每一步都围绕一件事:**可信**。

- 真源只读:逐字稿落盘即不可变,一切加工可溯源
- 引文逐字带时间戳+说话人,交付前脚本全量回核
- 拆解抓「分歧」——别人吵起来的地方最值钱,摘要工具的"要点归纳"恰恰把它抹平
- 判断归人,执行归 Agent:议题切分、脱敏边界、深加工取舍三处问你,其余不烦你

## 六件套(lulu-learn v0.1)

| Skill | 后厨位 | 干什么 |
|---|---|---|
| `lulu-learn` | 领班 | 主入口路由 + 任务后单步导航 |
| `lulu-learn-intake` | 采买 | 会议链接/录音/文字稿 → 只读真源 → 4 层项目;会前热词表 |
| `lulu-learn-decompose` | 备菜 | 议题切分提案(你确认)→ 并行细拆(论点/硬信息/分歧/金句)→ 引文全量回核 |
| `lulu-learn-atom` | 切件装盒 | 每个论点提炼成独立可检索的知识原子,项目内成库、可选汇入你的全局库 |
| `lulu-learn-weave` | 出菜 | 五大判断/议题线/观点地图 → 显式验收 checklist → 按去向脱敏发布 |
| `lulu-learn-board` | 明档 | 2.5D 后厨可视化,看着你的讲座被加工(真数据驱动,非演示动画) |

> 说明:流程图里的 8 个站点是工艺阶段,不是 8 个独立 Skill。6 个 Skill 负责把 8 个阶段串起来;`lulu-learn-board` 当前先发布状态数据契约。

## 为什么有 lulu-consult

你有专业能力,也真在跟客户聊。但聊完之后往往两头空:**客户没拿到东西**(你没时间写总结),**你自己也没沉淀**(第 10 个客户问的问题跟第 1 个一样,你还是从零想)。

这条流水线把两头接上:

```
客户情况 → 会前准备(核心矛盾 + 三段提问序列)
              ↓  (你去谈,记得录音)
      逐字稿 → 分析(数据 + 你的关键干预时刻)
              ↓  你补三句现场判断  ← 唯一不能自动化的一步
      报告完整版(发客户) + 可公开版(打码,可外发)
              ↓
      5-15 颗经验原子 → 进你自己的案例库
```

| Skill | 干什么 |
|---|---|
| `lulu-consult` | 主入口 + 4 个 agent(会前侦察 / 逐字稿分析 / 写报告 / 提炼原子) |

**它跟市面「AI 会议助手」的区别在两处**:

1. **P2.5 补充环节** —— 分析完成后它会停下来问你三句话(当时没说、事后想补的判断是什么)。AI 只看得见逐字稿,你现场的直觉判断逐字稿里没有。这一步是报告值不值钱的分水岭。
2. **它调用的是你自己的判断,不是别人的** —— 装上之后 `config/我的配置.md` 必须先填,尤其是「我的专业判断从哪几个维度切」。律师、医美、供应链填出来的是三套完全不同的东西。第一次跑比较一般(你的案例库是空的),跑到第二十次会明显不一样。

⚠️ **不适合**:还没有可收费专业能力的人(这是放大器不是发生器)、一次性不打算做第二次的对话、纯执行类交付。

## cool-chibi-photo · 照片创作

上传一张照片，可附画风参考，得到自然调色/按需调整构图的底图、独立透明Q版和合成成品。

它先判断照片里的完整情境：比如“电脑前工作，顺手比耶”，就同时保留电脑、工作手和手势。原照决定内容与动作，参考图决定画风和角色比例；真人与Q版分层制作，修改动作时复用底图。

| Skill | 入口与范围 |
|---|---|
| [cool-chibi-photo](skills/cool-chibi-photo/README.md) | 单人AB流程已实测；背景清理/更换、大幅重构、多人/宠物尚未完成端到端实图验证 |

**使用前提**：宿主Agent具备读图与图像生成/编辑能力；本地合成脚本需要Python 3.10+、Pillow和NumPy。安装Skill不会自动获得生图模型或额度。

- [完整说明与安装](skills/cool-chibi-photo/README.md)
- [背景与构图怎么选](skills/cool-chibi-photo/references/BACKGROUND_COMPOSITION.md)
- [整体复盘](skills/cool-chibi-photo/references/RETROSPECTIVE.md) · [实际验证范围](skills/cool-chibi-photo/VALIDATION.md)

## 仓库结构

```text
skills/
├── lulu-learn/SKILL.md
├── lulu-learn-intake/SKILL.md
│   └── scripts/fetch_tencent_minutes.py
├── lulu-learn-decompose/SKILL.md
├── lulu-learn-atom/SKILL.md
├── lulu-learn-weave/SKILL.md
│   └── scripts/verify_quotes.py
├── lulu-learn-board/SKILL.md
├── lulu-consult/
│   ├── SKILL.md
│   ├── config/我的配置.md      # ⭐ 装完先填
│   ├── agents/                 # 4 个 agent 定义
│   └── templates/              # 空的案例库模板
└── cool-chibi-photo/
    ├── SKILL.md
    ├── README.md               # 从这里开始
    ├── references/             # 提示词、背景构图、复盘
    ├── assets/                 # 可替换的设置与任务示例
    ├── scripts/                # 本地调色、恢复与合成
    └── tests/                  # 确定性回归检查

assets/
└── lulu-wechat-qr.png       # 联系 Lulu
```

安装器读取每个子目录中的 `SKILL.md`;不要只下载仓库根目录的 README。

## 联系 Lulu

想交流讲座整理、AI Agent 或 Skill 开源，欢迎扫码添加微信：

![Lulu 微信二维码](assets/lulu-wechat-qr.png)

## 安装

```bash
npx -y skills add ilulu66/iluluskill -g --all
```

只安装照片工具：

```bash
npx -y skills add ilulu66/iluluskill -g --skill cool-chibi-photo
```

| 你想做什么 | 装好后怎么说 |
|---|---|
| 整理讲座 | “讲座整理”，或提供会议录制分享链接 |
| 咨询准备/复盘 | 先填写咨询配置，再调用 lulu-consult |
| 真人照片＋Q版 | 上传照片，说“按 cool-chibi-photo 处理，背景A、构图B” |

## Roadmap

`-calibrate`(校准源降级链+主题热词表)· `-map`(知识原则/学习路线图深加工)· `-diff`(同一讲者跨期对比)· 转写扩源 · 多路录音判重 · 下一个系列进箱

## License

代码 MIT;文档与方法论 CC BY-NC 4.0。

---

*出自「Lulu 的会客厅」。这套流程不是设计出来的,是在两次真实学习项目(2500+ 分钟逐字稿)里被一次次纠偏调出来的。*
