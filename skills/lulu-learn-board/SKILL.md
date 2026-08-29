---
name: lulu-learn-board
description: 学习工坊明档——2.5D 后厨可视化,看着你的讲座被加工(真数据驱动,非演示动画)。触发词:开明档 / 明档 / 看后厨 / board。v1 视觉产物由 Codex 任务单交付中,本文件先定数据契约。
---

# lulu-learn-board:明档(open kitchen)

明档 = 餐厅里让客人看见厨房的那扇玻璃窗。这个组件把 lulu-learn 流程的**真实运行状态**渲染成 2.5D 后厨场景:小厨师们备菜(并行拆解)、主厨试味退盘(验收纠错)、出菜口上架(成篇发布)。它读真数据,不演动画。

## 怎么开

```bash
cd <项目文件夹> && python3 -m http.server 8765
# 浏览器开 http://localhost:8765/_board/board.html
# 彩排/演示模式(假数据): http://localhost:8765/_board/board.html?demo=1
```

`board.html` 实物由 Codex 任务单交付后放本 skill `assets/`,intake 建项目时复制进项目 `_board/`。

## status.json 契约 v1(页面轮询的唯一数据源)

流程各阶段把状态写进项目 `_board/status.json`(v1 联调期由主脑手动/半自动更新,联调通过后写进三个子 skill 的收尾义务):

```json
{
  "project": "项目名",
  "phase": "intake | decompose | weave | done",
  "intake": {"segments": 481, "duration": "02:56:17", "done": true},
  "decompose": {
    "plan_confirmed": true,
    "stations": [
      {"seg": "A", "topic": "争点一句话", "status": "working | done | rejected", "points": 7, "quotes": 3}
    ]
  },
  "verify": {"checked": 14, "fixed": 5, "rejected_to": "A"},
  "weave": {"draft": false, "checklist_passed": false, "published": false}
}
```

`status: "rejected"` = 主厨退盘(验收发现问题退回该工位)——画面上最有戏剧性的一幕,数据必须真实,不许为了好看造假。

## 边界

- 单 HTML 零外部依赖;强制 CSP 环境下也能跑。
- 页面只读 status.json,不碰任何真源文件。
- 演示模式必须显式 `?demo=1`,且画面角落常驻「DEMO」水印——真跑和演示不许混淆。
