#!/usr/bin/env python3
"""根据仓库目录结构 + 各 Dockerfile 的 ARG，重写 README.md 里的版本矩阵区块。

目录约定：<major.minor>/<variant>/Dockerfile，例如 8.8/uos/Dockerfile、8.8/kylin/Dockerfile

README 中需要存在这对标记（脚本只替换它们之间的内容，其余文字不动）：
    <!-- BEGIN REDIS-MATRIX -->
    <!-- END REDIS-MATRIX -->

状态列取自 config/lifecycle.json：
    LTS   = 官方 Extended 版本
    标准   = 官方 Standard 版本
    EOL   = 官方 EOL 已过期（保留目录，但不再构建）

用法：
  python3 scripts/sync_readme.py            # 重写 README（内容没变则不落盘）
  python3 scripts/sync_readme.py --check    # 只检查，需要更新时返回 1
"""

import argparse
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import lifecycle  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
BEGIN = "<!-- BEGIN REDIS-MATRIX -->"
END = "<!-- END REDIS-MATRIX -->"
LINE_RE = re.compile(r"^\d+\.\d+$")
ARG_RE = re.compile(r"^ARG\s+([A-Za-z_][A-Za-z0-9_]*)=(.*)$")
FROM_RE = re.compile(r"^FROM\s+(\S+)", re.IGNORECASE)
VARIANT_ORDER = {v: i for i, v in enumerate(lifecycle.BUILD_VARIANTS)}


def vkey(line):
    return tuple(int(x) for x in line.split("."))


def parse_dockerfile(path):
    """返回 (redis_version, base_image)。"""
    args, from_ref = {}, None
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = ARG_RE.match(line)
        if m and m.group(1) not in args:
            args[m.group(1)] = m.group(2).strip()
            continue
        if from_ref is None:
            fm = FROM_RE.match(line)
            if fm:
                from_ref = fm.group(1)

    def expand(s):
        return re.sub(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}",
                      lambda m: args.get(m.group(1), m.group(0)), s)

    base = expand(from_ref) if from_ref else "(unknown)"
    return args.get("REDIS_VERSION", "(unset)"), base


def collect(table):
    rows = []
    for line_dir in sorted(ROOT.iterdir(),
                           key=lambda p: vkey(p.name) if LINE_RE.match(p.name) else (0,)):
        if not line_dir.is_dir() or not LINE_RE.match(line_dir.name):
            continue
        line = line_dir.name
        supported = lifecycle.is_supported(line, table)
        lts = lifecycle.is_lts(line, table)
        info = lifecycle.info(line, table) or {}
        if not supported:
            status = "EOL"
        elif lts:
            status = "LTS"
        else:
            status = "标准"
        for variant_dir in sorted(line_dir.iterdir(), key=lambda p: VARIANT_ORDER.get(p.name, 9)):
            if variant_dir.name not in VARIANT_ORDER:
                continue  # 跳过上游模板产物（alpine/debian）
            dockerfile = variant_dir / "Dockerfile"
            if not variant_dir.is_dir() or not dockerfile.is_file():
                continue
            version, base = parse_dockerfile(dockerfile)
            rows.append({
                "line": line,
                "variant": variant_dir.name,
                "version": version,
                "base": base,
                "status": status,
                "eol": info.get("eol") or "TBD",
                "supported": supported,
            })
    return rows


def render(rows, image_repo):
    if not rows:
        return "_（暂无构建变体）_"
    out = [
        "| 版本线 | Redis | 变体 | 状态 | EOL | 基础镜像 | 镜像 tag |",
        "|--------|-------|------|------|-----|----------|----------|",
    ]
    for r in rows:
        if r["supported"]:
            tags = f"`{image_repo}:{r['line']}-{r['variant']}`<br>`{image_repo}:{r['version']}-{r['variant']}`"
        else:
            tags = "（已停止构建）"
        out.append(
            f"| `{r['line']}` | `{r['version']}` | {r['variant']} | {r['status']} "
            f"| {r['eol']} | `{r['base']}` | {tags} |"
        )
    return "\n".join(out)


def run(image_repo="ghcr.io/blueapple168/redis", check=False):
    """重写 README 的版本矩阵。返回 0=已是最新/已更新，1=需要更新(--check)，2=标记缺失。"""
    text = README.read_text(encoding="utf-8")
    if BEGIN not in text or END not in text:
        print(f"ERROR: README.md 缺少标记 {BEGIN} / {END}", file=sys.stderr)
        return 2

    head, rest = text.split(BEGIN, 1)
    _, tail = rest.split(END, 1)

    table = lifecycle.load()
    rows = collect(table)
    new_text = head + f"{BEGIN}\n{render(rows, image_repo)}\n{END}" + tail

    if new_text == text:
        print(f"README 版本矩阵已是最新（{len(rows)} 条）")
        return 0

    if check:
        print("README 版本矩阵需要更新", file=sys.stderr)
        return 1

    README.write_text(new_text, encoding="utf-8", newline="")
    print(f"README 版本矩阵已更新（{len(rows)} 条）")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--image", default="ghcr.io/blueapple168/redis")
    args = ap.parse_args()
    return run(args.image, args.check)


if __name__ == "__main__":
    sys.exit(main())
