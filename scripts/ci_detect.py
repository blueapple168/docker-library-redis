#!/usr/bin/env python3
"""CI 检测引擎：把「上游版本 + 官方 EOL 策略 + 仓库目录」三者对齐。

它做四件事：
  1. 解析 redis/redis 上游 GA 版本（调用 resolve_upstream）
  2. 按官方 EOL 表决定「该构建哪些版本线」
       - 已跟踪且仍支持 -> 保留
       - 最新 GA 线（默认纳入）
       - 最新 LTS/Extended 线（--track-lts，默认纳入）
       - 已 EOL          -> 从构建矩阵剔除（目录保留，README 标 EOL）
  3. 落盘：缺失的 <line>/<variant> 目录按模板补齐、ARG REDIS_VERSION 升到上游最新
  4. 输出构建矩阵 JSON，并刷新 README 版本矩阵

用法：
  python3 scripts/ci_detect.py                  # 执行（CI 用）
  python3 scripts/ci_detect.py --dry-run        # 只报告将要做的改动，不写文件
  python3 scripts/ci_detect.py --lines 8.8 --variants uos
  python3 scripts/ci_detect.py --force-version 8.8.9
  python3 scripts/ci_detect.py --no-track-lts   # 只跟踪最新 GA，不自动纳入 LTS 线
"""

import argparse
import json
import pathlib
import re
import shutil
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import lifecycle  # noqa: E402
import resolve_upstream  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
LINE_RE = re.compile(r"^\d+\.\d+$")
ARG_VER_RE = re.compile(r"^(ARG\s+REDIS_VERSION=)(\S+)\s*$", re.MULTILINE)
DEFAULT_VARIANTS = list(lifecycle.BUILD_VARIANTS)


def vkey(line):
    return tuple(int(x) for x in line.split("."))


def tracked_dirs():
    """{line: [variant, ...]}"""
    out = {}
    for p in ROOT.iterdir():
        if not p.is_dir() or not LINE_RE.match(p.name):
            continue
        variants = sorted(v.name for v in p.iterdir()
                          if v.name in lifecycle.BUILD_VARIANTS
                          and v.is_dir() and (v / "Dockerfile").is_file())
        if variants:
            out[p.name] = variants
    return out


def current_version(dockerfile):
    m = ARG_VER_RE.search(dockerfile.read_text(encoding="utf-8", errors="replace"))
    return m.group(2) if m else None


def set_version(dockerfile, version, dry):
    text = dockerfile.read_text(encoding="utf-8", errors="replace")
    new, n = ARG_VER_RE.subn(lambda m: f"{m.group(1)}{version}", text, count=1)
    if n != 1:
        raise RuntimeError(f"{dockerfile}: 未找到 ARG REDIS_VERSION 行")
    if new != text:
        if not dry:
            nl = "\r\n" if "\r\n" in text else "\n"
            dockerfile.write_bytes(new.replace("\r\n", "\n").replace("\n", nl).encode("utf-8"))
        return True
    return False


def scaffold(line, variant, version, source_line, source_variant, dry):
    """从已有的 <source_line>/<source_variant> 复制出 <line>/<variant>。"""
    src = ROOT / source_line / source_variant
    dst = ROOT / line / variant
    if not src.is_dir():
        raise RuntimeError(f"模板目录不存在: {src}")
    if dry:
        return [f"{dst} (来自 {src})"]
    dst.mkdir(parents=True, exist_ok=True)
    for f in src.iterdir():
        if f.is_file():
            shutil.copy2(f, dst / f.name)
    df = dst / "Dockerfile"
    set_version(df, version, dry=False)
    return [f"{dst} (来自 {src})"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--lines", default="", help="只处理这些版本线（空格分隔）")
    ap.add_argument("--variants", default="", help="只处理这些变体（空格分隔）")
    ap.add_argument("--force-version", default="", help="强制指定 Redis 版本号")
    ap.add_argument("--no-scaffold", action="store_true", help="不自动创建新目录")
    ap.add_argument("--matrix-file", default="", help="把构建矩阵写入该文件")
    ap.add_argument("--upstream-json", default="", help="离线：从本地 JSON 读取上游版本（测试用）")
    args = ap.parse_args()

    line_filter = set(args.lines.split()) if args.lines else None
    variant_filter = args.variants.split() if args.variants else DEFAULT_VARIANTS

    table = lifecycle.load()
    if args.upstream_json:
        cached = json.loads(pathlib.Path(args.upstream_json).read_text(encoding="utf-8"))
        upstream = {k: v if isinstance(v, dict) else {"version": v}
                    for k, v in cached.get("lines", cached).items()}
        print(f"(离线模式) 上游版本取自 {args.upstream_json}")
    else:
        try:
            upstream = resolve_upstream.resolve_index()
        except RuntimeError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            return 1

    tracked = tracked_dirs()
    tracked_lines = sorted(tracked, key=vkey)
    print(f"上游 GA 版本线: {' '.join(sorted(upstream, key=vkey))}")
    print(f"仓库已跟踪:     {' '.join(tracked_lines) or '(无)'}")

    # ---------- 1. 计算目标版本线集合 ----------
    # 策略：构建官方「安全支持期（Security Support）未过期」的全部版本线，
    # 也就是所有仍在维护的 stable + LTS，直到官方宣布 EOL 为止。
    #   - 在 lifecycle.json 里且 EOL 未过期 -> 构建
    #   - 在 lifecycle.json 里且已 EOL     -> 跳过（目录保留，README 标 EOL）
    #   - 不在表里但上游有 GA              -> 视为刚发布的新线，先构建并提示补表
    desired, untracked, eol_lines = set(), [], []
    for line in upstream:
        it = lifecycle.info(line, table)
        if it is None:
            untracked.append(line)
        elif lifecycle.is_supported(line, table):
            desired.add(line)
        else:
            eol_lines.append((line, it.get("eol")))
    if eol_lines:
        print("::notice::官方已 EOL，不再构建: "
              + ", ".join(f"{l}({e})" for l, e in sorted(eol_lines, key=lambda x: vkey(x[0]))))
    if untracked:
        print("::warning::上游有 GA 但不在 config/lifecycle.json 的版本线: "
              + " ".join(sorted(untracked, key=vkey))
              + "（本次按新发布处理并构建，请把它们的 EOL 补进表里）")
        desired |= set(untracked)

    if line_filter:
        desired &= line_filter

    # ---------- 2. EOL 闸门（兜底：filter / 表里已 EOL 的一律剔除） ----------
    buildable, eol_skipped = [], []
    for line in sorted(desired, key=vkey):
        if line not in upstream:
            print(f"::notice::{line}: 上游没有该线的 GA 版本，跳过")
            continue
        it = lifecycle.info(line, table)
        if it is not None and not lifecycle.is_supported(line, table):
            eol_skipped.append(line)
            print(f"::warning::{line}: 官方已 EOL（{it.get('eol')}），不再构建")
            continue
        buildable.append(line)

    # ---------- 3. 补齐目录 + 升版本 ----------
    # 注意：构建矩阵按「计划」生成，而不是按文件系统现状 —— 否则 dry-run 下
    # 尚未 scaffold 的新版本线会漏出矩阵。
    changes = []
    planned = []  # [(line, variant, version)]
    source_line = max(tracked_lines, key=vkey) if tracked_lines else None
    for line in buildable:
        version = args.force_version or upstream[line]["version"]
        for variant in variant_filter:
            df = ROOT / line / variant / "Dockerfile"
            if not df.is_file():
                if args.no_scaffold:
                    print(f"::notice::{line}/{variant}: 目录缺失且已禁用 scaffold，跳过")
                    continue
                if source_line is None:
                    print(f"::error::{line}/{variant}: 没有可用于 scaffold 的模板目录", file=sys.stderr)
                    return 1
                src_variant = variant if (ROOT / source_line / variant).is_dir() else tracked[source_line][0]
                changes += scaffold(line, variant, version, source_line, src_variant, args.dry_run)
                print(f"::notice::scaffold {line}/{variant} <- {source_line}/{src_variant}")
                planned.append((line, variant, version))
                continue
            if set_version(df, version, args.dry_run):
                changes.append(f"{df}: REDIS_VERSION -> {version}")
                print(f"::notice::{line}/{variant}: REDIS_VERSION -> {version}")
            planned.append((line, variant, version))

    # ---------- 4. 刷新 README ----------
    import sync_readme  # noqa: E402
    if args.dry_run:
        print(f"(dry-run) README 版本矩阵待刷新（将覆盖 {len(planned)} 条），不落盘")
        readme_rc = 0
    else:
        readme_rc = sync_readme.run()

    # ---------- 5. 输出构建矩阵 ----------
    matrix = [{
        "line": line,
        "variant": variant,
        "version": version,
        "lts": lifecycle.is_lts(line, table),
    } for line, variant, version in planned]

    payload = {"include": matrix}
    if args.matrix_file:
        pathlib.Path(args.matrix_file).write_text(json.dumps(payload), encoding="utf-8")
    print("MATRIX=" + json.dumps(payload))
    skipped = sorted({l for l, _ in eol_lines} | set(eol_skipped), key=vkey)
    print(f"待构建 {len(matrix)} 个镜像；EOL 跳过 {len(skipped)} 条线 {skipped or ''}")
    print(f"文件改动 {len(changes)} 处")
    return 0 if readme_rc == 0 else readme_rc


if __name__ == "__main__":
    sys.exit(main())
