# iluluskill · 会客厅 skill

> Lulu 的公开 skill 总箱,中文名「**会客厅 skill**」(出自「Lulu 的会客厅」)。
> 当前包含两个系列和一件独立照片工具:
> - **lulu-learn 学习工坊**——把一场 3 小时的讲座,做成一份可回访的学习资产。别人做压缩,我们做加工:压缩丢真相,加工保真相。
> - **lulu-consult 咨询流水线**——把一次专业对话,变成客户当天收到的报告 + 一颗进你自己库的经验原子。
> - **cool-chibi-photo 朋友圈照骗**——标准版保留真人＋同款Q版，新增没拍到我、宠物小物互动、人太小替换三个场景。

**状态：v0.5.0-rc.1 试用版（2026-10-25），共8个Skill。** 照片组件升级至cool-chibi-photo 3.0.0-rc.1，优先适配Codex；学习与咨询组件本轮未改。下载[三场景试用版ZIP](https://github.com/ilulu66/iluluskill/releases/tag/v0.5.0-rc.1)。

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

## cool-chibi-photo · 朋友圈照骗三场景版

给一张已有照片和自己的角色/画风参考，让Q版进入这张照片的具体情境。标准版仍可保留真人、在右下加同款小人；三种新场景按照片内容选择：

| 照片情况 | 处理方式 |
|---|---|
| 没拍到我 | 纯景放角落，有合理位置时让角色坐进台阶、窗边等空间 |
| 宠物或小物 | 保留真实猫狗/物件，让指定人类Q版入景互动 |
| 人太小 | 先推荐原位替换，取得本图或本批许可后执行 |

画风确实拿不准时，先展示2～3个真实参考，再用宿主支持的选择界面让你选；没有原生选择工具就用文字。已指定、已认可或明确委托决定时继续执行，不重复询问。选择画风不会顺带改变衣服、背景或删人许可。

**适用环境**：当前优先适配能看图、能调用内置图像生成/编辑工具的Codex会话。路由helper与安装器需Python 3.10+；旧本地合成脚本另需Pillow和NumPy。安装Skill不会附带生图模型、额度或API服务。用自己的原照与参考即可，公开包不含作者私人图库。

**验证范围**：67项软件回归通过；小物互动已取得一张用户认可结果。无人景物尚未完成真实原片生图回归，小人物替换的比例仍待修订；本版标记为试用版，不承诺三场景均稳定通过。整图生成与严格主体保留分开，后者需要实际蒙版、合成和像素核验。

- [照片组件完整说明与安装](skills/cool-chibi-photo/README.md)
- [Codex首次运行](skills/cool-chibi-photo/references/CODEX_SETUP.md) · [场景路由](skills/cool-chibi-photo/references/SCENARIOS.md)
- [实际验证范围](skills/cool-chibi-photo/VALIDATION.md)

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

想交流讲座整理、AI Agent 或 Skill，或洽谈商业授权，欢迎扫码添加微信：

![Lulu 微信二维码](assets/lulu-wechat-qr.png)

## 安装

```bash
npx -y skills add ilulu66/iluluskill -g --all
```

只把新版照片工具安装到Codex（首次安装，需Node.js/npm提供npx）：

```bash
npx -y skills add ilulu66/iluluskill -g --skill cool-chibi-photo --agent codex -y
```

已有`~/.codex/skills/cool-chibi-photo`时，下载上述ZIP后在组件目录运行`python3 scripts/install.py --codex --replace`，先备份再原位更新，避免留下另一种方式安装的同名副本。安装后开新的Codex对话，附原照和自己的参考即可。详细位置与依赖见[安装说明](skills/cool-chibi-photo/references/CODEX_SETUP.md)。

| 你想做什么 | 装好后怎么说 |
|---|---|
| 整理讲座 | “讲座整理”，或提供会议录制分享链接 |
| 咨询准备/复盘 | 先填写咨询配置，再调用 lulu-consult |
| 照片三场景＋Q版 | 附原照与参考，说“用 $cool-chibi-photo，让小人坐在玩偶旁边，保留真实玩偶，不加文字” |

## Roadmap

`-calibrate`(校准源降级链+主题热词表)· `-map`(知识原则/学习路线图深加工)· `-diff`(同一讲者跨期对比)· 转写扩源 · 多路录音判重 · 下一个系列进箱

## License

**个人学习、研究免费；商业用途需授权付费。**

- 代码:PolyForm Noncommercial 1.0.0;文档与方法论:CC BY-NC 4.0。
- 公司内部使用、给客户交付服务、放进付费课程/社群、集成进产品,都算商业用途,请先扫上方二维码联系 Lulu 取得书面授权。
- v0.4.0 及更早版本的代码按当时的 MIT 发布,旧版本仍适用原授权。

详见 [LICENSE.md](LICENSE.md)。

---

*出自「Lulu 的会客厅」。这套流程不是设计出来的,是在两次真实学习项目(2500+ 分钟逐字稿)里被一次次纠偏调出来的。*
