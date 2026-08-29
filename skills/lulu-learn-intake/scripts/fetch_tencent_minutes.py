#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""腾讯会议录制分享页 · 免登录拉全量逐字稿
工艺来源:真实长讲座项目实测,已覆盖多页逐字稿的续拉场景。

用法:
  1. 浏览器打开录制分享页(meeting.tencent.com/crm/<code>),F12 网络面板
     找 `wemeet-cloudrecording-webapi/v1/minutes/detail` 请求,抄三个参数。
  2. python3 fetch_tencent_minutes.py --id <auth_share_id> \
       --meeting-id <meeting_id> --recording-id <recording_id> \
       --title 项目名 -o 输出目录

翻页铁律(别改):
  - 首拉: fview=1&limit=100&start_pid=0 —— 只回前 100 段。
  - ⚠️ start_pid 增大不起作用(永远回前 100 段),是死胡同。
  - 真续页: pid=<最后一段pid>&fview=0(去掉 limit/start_pid),
    一次返回其余全部段落直到 more=False。

零第三方依赖(urllib),Python 3.9+。
"""
import argparse
import datetime
import json
import sys
import urllib.parse
import urllib.request

BASE = "https://meeting.tencent.com/wemeet-cloudrecording-webapi/v1/minutes/detail"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36")


def http_get(params):
    url = BASE + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": "https://meeting.tencent.com/"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def extract_paragraphs(payload):
    """容错解析:minutes.paragraphs[].{pid,start_time,sentences[].words[].text,speaker.user_name}"""
    minutes = payload.get("minutes") or payload.get("data", {}).get("minutes") or {}
    paras = minutes.get("paragraphs") or []
    more = minutes.get("more", payload.get("more", False))
    out = []
    for p in paras:
        text = ""
        for s in p.get("sentences", []):
            for w in s.get("words", []):
                text += w.get("text", "")
        speaker = (p.get("speaker") or {}).get("user_name", "未知")
        out.append({"pid": p.get("pid"), "ms": p.get("start_time", 0), "speaker": speaker, "text": text})
    return out, more


def fmt_ts(ms):
    s = int(ms) // 1000
    return "%02d:%02d:%02d" % (s // 3600, (s % 3600) // 60, s % 60)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", required=True, help="auth share id(分享页 detail 请求里的 id)")
    ap.add_argument("--meeting-id", required=True)
    ap.add_argument("--recording-id", required=True)
    ap.add_argument("--title", default="讲座", help="项目名,用于文件命名")
    ap.add_argument("-o", "--outdir", default=".", help="输出目录")
    ap.add_argument("--source-url", default="", help="分享页 URL,写进 frontmatter")
    args = ap.parse_args()

    common = {"id": args.id, "meeting_id": args.meeting_id, "recording_id": args.recording_id}

    # 首拉
    payload = http_get(dict(common, fview=1, limit=100, start_pid=0))
    paras, more = extract_paragraphs(payload)
    if not paras:
        print("❌ 首拉 0 段。原始响应键:%s\n请核对三个参数是否从 detail 请求原样抄下。" % list(payload.keys()))
        sys.exit(1)
    print("首拉 %d 段, more=%s" % (len(paras), more))

    # 续拉:pid=<最后pid>&fview=0,直到 more=False(防呆上限 50 轮)
    rounds = 0
    while more and rounds < 50:
        rounds += 1
        last_pid = paras[-1]["pid"]
        payload = http_get(dict(common, fview=0, pid=last_pid))
        chunk, more = extract_paragraphs(payload)
        # 防重:续页可能含锚点段自身
        seen = {p["pid"] for p in paras}
        chunk = [c for c in chunk if c["pid"] not in seen]
        if not chunk:
            break
        paras.extend(chunk)
        print("续拉第 %d 轮 +%d 段(累计 %d), more=%s" % (rounds, len(chunk), len(paras), more))

    paras.sort(key=lambda p: p["ms"])
    total = len(paras)
    dur = fmt_ts(paras[-1]["ms"]) if paras else "00:00:00"
    speakers = sorted({p["speaker"] for p in paras})

    fname = "逐字稿-%s-%d段.md" % (args.title, total)
    path = args.outdir.rstrip("/") + "/" + fname
    with open(path, "w", encoding="utf-8") as f:
        f.write("---\n来源: \"%s\"\ncreated: %s\ntags: [讲座培训, 逐字稿]\n---\n\n" % (
            args.source_url, datetime.date.today().isoformat()))
        f.write("> %d 段 · %d 位说话人 · 至 %s · 腾讯会议机器转写**原样导出,未校准,🔒只读**\n\n" % (
            total, len(speakers), dur))
        for p in paras:
            f.write("[%s] %s:%s\n\n" % (fmt_ts(p["ms"]), p["speaker"], p["text"]))
    print("✅ %s(%d 段 / %d 位说话人 / 至 %s)" % (path, total, len(speakers), dur))


if __name__ == "__main__":
    main()
