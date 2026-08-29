# iluluskill · 会客厅 skill

> Lulu 的开源 skill 总箱,中文名「**会客厅 skill**」(出自「Lulu 的会客厅」)。
> 首发系列:**lulu-learn 学习工坊**——把一场 3 小时的讲座,做成一份可回访的学习资产。
> 别人做压缩,我们做加工——压缩丢真相,加工保真相。

**状态:v0.1 可安装核心快照(2026-08-29)。**明档的可视化 HTML 仍在迭代,当前发布的是数据契约版。

## 命名三层

```
iluluskill / 会客厅skill   ← 总箱(本仓库,一条命令装全家)
└── lulu-learn / 学习工坊  ← 系列(讲座/课程/工作坊/书)
    └── lulu-learn-intake  ← 件:具体 skill
```

以后新的系列进同一个箱,安装命令永远不变。对你的 agent 说「会客厅skill」即可唤起。

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
└── lulu-learn-board/SKILL.md

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

装好后对你的 agent 说「讲座整理」,或直接粘一个腾讯会议录制分享链接。

## Roadmap

`-calibrate`(校准源降级链+主题热词表)· `-map`(知识原则/学习路线图深加工)· `-diff`(同一讲者跨期对比)· 转写扩源 · 多路录音判重 · 下一个系列进箱

## License

代码 MIT;文档与方法论 CC BY-NC 4.0。

---

*出自「Lulu 的会客厅」。这套流程不是设计出来的,是在两次真实学习项目(2500+ 分钟逐字稿)里被一次次纠偏调出来的。*
