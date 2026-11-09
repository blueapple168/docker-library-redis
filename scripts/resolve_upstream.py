#!/usr/bin/env python3
"""解析 redis/redis 上游的 stable（GA）版本。

规则：
  - 只认 GitHub Releases 里 draft=false 且 prerelease=false 的发布
  - tag 必须是纯 GA 语义化版本 x.y.z（8.8.3）；8.12-rc2 / 7.4-rc1 / 8.0-m03 一律跳过
  - 按 major.minor 归并，取该线最大的 patch
  - 若 release 名称或正文出现 LTS 字样，标记 lts=true（Redis 官方不强制标注，仅作参考）

用法：
  python3 scripts/resolve_upstream.py                # 输出 JSON
  python3 scripts/resolve_upstream.py --line 8.8     # 只输出该线的最新版本号
  python3 scripts/resolve_upstream.py --lines        # 只输出版本线列表（空格分隔）
  python3 scripts/resolve_upstream.py --json         # 同上默认

环境变量：
  GITHUB_TOKEN  可选；带上可把 API 限额从 60/h 提到 5000/h（CI 里必带）
"""

import argparse
import json
import os
import pathlib
import re
import sys
import urllib.error
import urllib.request

API = "https://api.github.com/repos/redis/redis"
GA_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


def api_get(url):
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "docker-library-redis-ci",
    })
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def collect_releases(pages=3):
    """返回 [(tag, name, body)]，只保留 GA。"""
    out = []
    for page in range(1, pages + 1):
        try:
            data = api_get(f"{API}/releases?per_page=100&page={page}")
        except urllib.error.HTTPError as e:
            if page == 1:
                raise
            print(f"WARN: 第 {page} 页 releases 拉取失败({e.code})，停止翻页", file=sys.stderr)
            break
        if not data:
            break
        for rel in data:
            if rel.get("draft") or rel.get("prerelease"):
                continue
            tag = (rel.get("tag_name") or "").strip()
            if not GA_RE.match(tag):
                continue
            out.append((tag, rel.get("name") or "", rel.get("body") or ""))
    return out


def collect_tags(pages=3):
    """releases 不可用时的兜底：从 tags 里挑 GA。"""
    out = []
    for page in range(1, pages + 1):
        try:
            data = api_get(f"{API}/tags?per_page=100&page={page}")
        except urllib.error.HTTPError as e:
            if page == 1:
                raise
            break
        if not data:
            break
        for t in data:
            tag = (t.get("name") or "").strip()
            if GA_RE.match(tag):
                out.append((tag, "", ""))
    return out


def vkey(ver):
    return tuple(int(x) for x in ver.split("."))


def build_index(entries):
    """{line: {"version":..., "lts": bool}}"""
    idx = {}
    for tag, name, body in entries:
        m = GA_RE.match(tag)
        if not m:
            continue
        line = f"{m.group(1)}.{m.group(2)}"
        cur = idx.get(line)
        if cur is None or vkey(tag) > vkey(cur["version"]):
            idx[line] = {
                "version": tag,
                "lts": "LTS" in f"{name}\n{body}".upper(),
            }
    return idx


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--line", help="只输出指定版本线的最新版本号")
    ap.add_argument("--lines", action="store_true", help="只输出版本线列表")
    ap.add_argument("--json", action="store_true", help="输出完整 JSON（默认）")
    ap.add_argument("--from-file", metavar="PATH", help="不从网络拉取，直接读本地缓存的 JSON")
    args = ap.parse_args()

    if args.from_file:
        data = json.loads(pathlib.Path(args.from_file).read_text(encoding="utf-8"))
        idx = data.get("lines", data)
        if args.line:
            print(idx[args.line]["version"])
        elif args.lines:
            print(" ".join(sorted(idx, key=vkey)))
        else:
            print(json.dumps({"lines": dict(sorted(idx.items(), key=lambda kv: vkey(kv[0])))},
                             ensure_ascii=False, indent=2))
        return 0

    try:
        entries = collect_releases()
    except Exception as e:  # noqa: BLE001
        print(f"WARN: releases API 不可用（{e}），回退到 tags API", file=sys.stderr)
        try:
            entries = collect_tags()
        except Exception as e2:  # noqa: BLE001
            print(f"ERROR: tags API 也不可用（{e2}）", file=sys.stderr)
            print("提示：未认证的 GitHub API 限额为 60 次/小时；设置 GITHUB_TOKEN 可提升到 5000 次/小时。",
                  file=sys.stderr)
            return 3

    idx = build_index(entries)
    if not idx:
        print("ERROR: 未能解析出任何 GA 版本，请检查网络或 API 限额", file=sys.stderr)
        return 1

    if args.line:
        item = idx.get(args.line)
        if not item:
            print(f"ERROR: 上游没有 {args.line} 的 GA 版本", file=sys.stderr)
            return 2
        print(item["version"])
        return 0

    if args.lines:
        print(" ".join(sorted(idx, key=vkey)))
        return 0

    print(json.dumps({"lines": dict(sorted(idx.items(), key=lambda kv: vkey(kv[0])))},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
