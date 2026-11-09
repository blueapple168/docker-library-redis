# 构建说明（本仓库的信创变体）

本仓库是 [docker-library/redis](https://github.com/docker-library/redis) 的 fork，在上游模板产物
（`<版本>/debian`、`<版本>/alpine`）之外，新增了手工维护的 **uos / kylin** 变体。

上游那套 `versions.sh` / `apply-templates.sh` / `update.sh` 仍然保留，但它们**只影响 debian/alpine**；
`apply-templates.sh` 已改为只清理 `$version/debian`、`$version/alpine`，不会动 `uos` / `kylin`。

---

## 1. 目录约定

```
<major.minor>/<variant>/Dockerfile
<major.minor>/<variant>/docker-entrypoint.sh
```

- `variant` 只允许 `uos`、`kylin`（白名单写在 `scripts/lifecycle.py` 的 `BUILD_VARIANTS`）
- 构建上下文 = 变体目录本身，所以 `docker build 8.8/uos` 直接可用，不依赖仓库根目录
- 目录结构就是状态：新增版本线 = 新增目录，CI 会自动识别

## 2. 本地构建

```bash
docker build -t redis:8.8-uos   8.8/uos
docker build -t redis:8.8-kylin 8.8/kylin

# 指定版本 / 关闭 RedisJSON（Rust 编译失败时的逃生口，仅 kylin 变体支持该 ARG）
docker build --build-arg REDIS_VERSION=8.8.4 -t redis:8.8-uos 8.8/uos
docker build --build-arg WITH_MODULES=no    -t redis:8.8-kylin 8.8/kylin

# 批量
./scripts/build-images.sh --lines 8.8 --variants uos
```

构建耗时参考：x86_64 上首次全量约 20~30 分钟（含 rustup + clang 编译 RedisJSON）。

## 3. CI 流程

`.github/workflows/docker-publish.yml`，四个作业：

| 作业 | 作用 |
|------|------|
| `detect` | 解析上游 GA 版本 → 按 EOL 表算构建矩阵 → 补目录 / 升 `ARG REDIS_VERSION` → 刷新 README → 提交回 master |
| `build` | 按矩阵构建并推送（`max-parallel: 2`，GHA 层缓存） |
| `scan` | Trivy 扫描，`continue-on-error`，不阻断 |
| `release` | 打 `v*` tag 时创建 Release |

不同触发面的策略差异：

| 触发 | scaffold 新版本线 | 写文件/提交 | 推送镜像 |
|------|------------------|-------------|----------|
| push 到 master | ✗（只重建已有版本线） | ✓ | ✓ |
| pull_request | ✗ | ✗（`--dry-run`） | ✗ |
| schedule（每周一） | ✓ | ✓ | ✓ |
| workflow_dispatch | 可勾选 | ✓ | 可勾选 |

## 4. 版本策略

构建范围由 `config/lifecycle.json`（官方 EOL 表）决定：

1. EOL 已过期的版本线 → 从矩阵剔除，README 标 `EOL`，目录保留
2. 上游新 GA 版本线 → 定时任务自动补 `<line>/uos`、`<line>/kylin` 并构建
3. 默认跟踪：最新 GA 线 + 最新 LTS(Extended) 线 + 已跟踪且未 EOL 的线
4. 同一线内新 patch → 自动改 `ARG REDIS_VERSION`

RC / milestone 不构建。

## 5. 脚本

| 脚本 | 用途 |
|------|------|
| `scripts/resolve_upstream.py` | 解析 redis/redis 的 GA 版本（releases API，失败回退 tags；支持 `--from-file` 离线） |
| `scripts/lifecycle.py` | EOL 判定：`--list` / `--check 8.8` / `--supported` / `--newest-lts` |
| `scripts/ci_detect.py` | 策略引擎：算矩阵、补目录、升版本、刷新 README（`--dry-run` 可预演） |
| `scripts/sync_readme.py` | 只重写 README 的版本矩阵区块 |
| `scripts/build-images.sh` | 本地批量构建 |

CI 里调用 `resolve_upstream.py` 时带了 `GITHUB_TOKEN`（5000 次/小时）；本地裸跑是 60 次/小时，
被限流时脚本会明确提示，可用 `--from-file` 喂本地缓存。

## 6. 上游同步（可选）

```bash
./update.sh                       # 拉上游 versions.json 并重建 debian/alpine 变体（不影响 uos/kylin）
./generate-stackbrew-library.sh   # 生成 stackbrew 元数据（仅上游用途）
```

同步上游后，`git diff` 里只应出现 `debian/`、`alpine/`、`versions.json` 的改动；
如果出现 `uos/`、`kylin/` 被删，说明 `apply-templates.sh` 的保护被改坏了。
