#!/usr/bin/env python3
"""Redis 官方版本生命周期（EOL）表读写与判定。

数据来源：config/lifecycle.json（官方 https://redis.io/docs/latest/operate/oss_and_stack/install/version-mgmt/ 的机器可读副本）
维护方式：官方页面更新后手工同步该 json；`retrieved` 字段记录同步日期。

判定规则：
  - eol 为 null          -> 官方未公布 EOL（TBD），视为仍支持
  - eol 日期 >= 今天     -> 仍支持
  - eol 日期 <  今天     -> 已 EOL，不再跟踪构建

CLI：
  python3 scripts/lifecycle.py --list            # 打印全表
  python3 scripts/lifecycle.py --check 8.8       # 打印单行判定
  python3 scripts/lifecycle.py --supported       # 打印仍支持的版本线（空格分隔）
  python3 scripts/lifecycle.py --newest-lts      # 打印仍支持的最新 LTS(Extended) 线
"""

import argparse
import datetime
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config" / "lifecycle.json"

# 本仓库实际构建的变体（<line>/<variant>/Dockerfile）。
# 上游 docker-library 模板产物（alpine/debian）不参与，脚本扫描时必须排除。
BUILD_VARIANTS = ("uos", "kylin")


def vkey(line):
    return tuple(int(x) for x in line.split("."))


def load():
    with CONFIG.open(encoding="utf-8") as f:
        return json.load(f)


def today():
    return datetime.date.today()


def info(line, table=None):
    table = table or load()
    return table.get("versions", {}).get(line)


def is_supported(line, table=None, on=None):
    it = info(line, table)
    if it is None:
        # 表里没有的版本线：保守起见视为“未知”，不自动构建
        return False
    eol = it.get("eol")
    if not eol:
        return True
    return datetime.date.fromisoformat(eol) >= (on or today())


def is_lts(line, table=None):
    it = info(line, table)
    return bool(it and it.get("type") == "extended")


def supported_lines(table=None, on=None):
    table = table or load()
    lines = [l for l in table.get("versions", {}) if is_supported(l, table, on)]
    return sorted(lines, key=vkey)


def newest_supported(table=None, on=None):
    lines = supported_lines(table, on)
    return lines[-1] if lines else None


def newest_lts_supported(table=None, on=None):
    table = table or load()
    lines = [l for l in supported_lines(table, on) if is_lts(l, table)]
    return lines[-1] if lines else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--check", metavar="LINE")
    ap.add_argument("--supported", action="store_true")
    ap.add_argument("--newest-lts", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    table = load()

    if args.check:
        it = info(args.check, table)
        if it is None:
            print(f"{args.check}: 不在官方生命周期表中（未跟踪）")
            return 2
        ok = is_supported(args.check, table)
        print(f"{args.check}: supported={ok} type={it['type']} lts={is_lts(args.check, table)} eol={it.get('eol') or 'TBD'}")
        return 0 if ok else 1

    if args.supported:
        print(" ".join(supported_lines(table)))
        return 0

    if args.newest_lts:
        print(newest_lts_supported(table) or "")
        return 0

    if args.json:
        print(json.dumps(table, ensure_ascii=False, indent=2))
        return 0

    # --list（默认）
    print(f"来源: {table.get('source')}  同步日期: {table.get('retrieved')}")
    print(f"{'版本线':8} {'类型':10} {'状态':10} EOL")
    for line in sorted(table.get("versions", {}), key=vkey, reverse=True):
        it = table["versions"][line]
        typ = "Extended/LTS" if it.get("type") == "extended" else "Standard"
        ok = is_supported(line, table)
        print(f"{line:8} {typ:10} {'支持' if ok else '已EOL':10} {it.get('eol') or 'TBD'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
