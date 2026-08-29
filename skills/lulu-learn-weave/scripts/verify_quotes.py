#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""引文全量回核:核对文档里的「」引文是否逐字存在于真源逐字稿。
用法: python3 verify_quotes.py --doc 整理版.md --source 逐字稿1.md [--source 逐字稿2.md ...]
      [--min-len 6]  短于 min-len 字的引文跳过(误报多)

判定:
  ✅ 直接命中真源
  ⚠️ 松匹配命中(去掉空白/标点后一致)——多为转写连字差异(如「6、7k」vs「67k」),人工看一眼
  ❌ 未命中——回真源核对:是引错了还是真源里另有写法
退出码: 有 ❌ 时为 1,否则 0。Python 3.9+,零依赖。
"""
import argparse
import re
import sys

PUNCS = "，。、！？；：""''《》()（）·…—-—~ \t\n\r"


def norm(s):
    return "".join(ch for ch in s if ch not in PUNCS)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--doc", required=True)
    ap.add_argument("--source", required=True, action="append")
    ap.add_argument("--min-len", type=int, default=6)
    args = ap.parse_args()

    with open(args.doc, encoding="utf-8") as f:
        doc = f.read()
    raw_sources, norm_sources = [], []
    for p in args.source:
        with open(p, encoding="utf-8") as f:
            t = f.read()
        raw_sources.append(t)
        norm_sources.append(norm(t))

    quotes = re.findall(r"「([^」]+)」", doc)
    # 剥离引文内的编者按语「……(按:……)……」再核(体例上按语应在引号外,此处兼容存量)
    quotes = [re.sub(r"[（(]按[:：][^）)]*[）)]", "", q) for q in quotes]
    seen = set()
    ok = loose = miss = skipped = 0
    for q in quotes:
        if q in seen:
            continue
        seen.add(q)
        if len(norm(q)) < args.min_len:
            skipped += 1
            continue
        if any(q in s for s in raw_sources):
            ok += 1
        elif any(norm(q) in s for s in norm_sources):
            loose += 1
            print("⚠️ 松匹配(标点/空白差异,人工看一眼): 「%s」" % q[:60])
        else:
            miss += 1
            print("❌ 未命中真源: 「%s」" % q[:60])

    print("—— 回核完毕:✅ %d 全中 / ⚠️ %d 松匹配 / ❌ %d 未命中 / 跳过短引文 %d(共 %d 条去重后)"
          % (ok, loose, miss, skipped, len(seen)))
    sys.exit(1 if miss else 0)


if __name__ == "__main__":
    main()
