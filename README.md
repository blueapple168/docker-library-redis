# Redis 容器镜像（UOS / Kylin V11 双系统）

面向信创环境的 Redis 8 镜像构建仓库：基于**统信 UOS Server 20** 与 **银河麒麟 V11** 两个国产化基础镜像，
从源码编译 Redis（含 RedisJSON 模块、TLS），按官方 EOL 策略自动跟踪上游版本并构建。

- 上游来源：[redis/redis](https://github.com/redis/redis/releases)（官方 GA 版本）
- 基础镜像：`ghcr.io/blueapple168/uos-server-20-1070a:latest` / `cr.kylinos.cn/kylin/kylin-server-minimal:v11-2503`
- 镜像仓库：`ghcr.io/blueapple168/redis`

---

## 1. 镜像 tag 约定

| tag | 含义 |
|-----|------|
| `8.8-uos` / `8.8-kylin` | 该版本线在对应系统上的最新构建（随上游补丁自动更新） |
| `8.8.3-uos` / `8.8.3-kylin` | 固定到具体版本，生产环境建议用这个 |

> 早期用过 `ghcr.io/blueapple168/redis-uos:8.8-uos` 这套命名，现已统一到 `redis` 单仓库 + 变体后缀。
> 旧 tag 不再更新，请迁移到新命名。

---

## 2. 版本支持策略

构建范围**完全跟随官方的安全支持期（Security Support）**：`config/lifecycle.json` 是
[Redis Open Source version management](https://redis.io/docs/latest/operate/oss_and_stack/install/version-mgmt/)
的机器可读副本，并对照 [endoflife.date/redis](https://endoflife.date/redis) 交叉校验。

| 官方分类 | 含义 | 支持期 |
|----------|------|--------|
| **Extended（本项目标为 LTS）** | 系列里第二个小版本（如 8.2）与最后一个小版本 | 自发布起 **5 年**安全与关键修复 |
| **Standard（标准）** | 大版本首个版本（如 8.0）与中间小版本（如 8.4/8.6） | 下一个 minor 发布后 **6 个月** |

自动构建规则：

1. **构建全部仍在安全支持期的版本线** —— 只要官方 EOL 未过期，stable 与 LTS 一视同仁全部出镜像，
   而不是只跟「最新一条」。
2. **已 EOL 的线立刻停手** —— 从构建矩阵剔除，README 标 `EOL`，目录保留不删。构建日志会明确列出
   「官方已 EOL，不再构建: 5.0(2022-04-27), 6.0(2022-05-31), 7.0(2024-07-29)」。
3. **新版本线自动补齐** —— 上游出现新的 GA 线时，自动按模板创建 `<版本线>/uos`、`<版本线>/kylin`；
   若该线还没写进 `lifecycle.json`，会先构建并告警提示补表。
4. **补丁自动升级** —— 同一版本线内出现新 patch（如 8.8.3 → 8.8.4），自动改 `ARG REDIS_VERSION` 并重建。
5. **RC / milestone 一律不构建** —— 只认 `x.y.z` 形式的 GA tag。

> **RedisJSON 的版本差异**：模块自 Redis 8.0 起才并入主仓库，6.2 / 7.2 / 7.4 的源码树里没有
> `modules/redisjson`。Dockerfile 会按版本自动跳过模块编译（也可用 `--build-arg WITH_MODULES=no` 强制关闭）。

---

## 3. 版本矩阵

<!-- BEGIN REDIS-MATRIX -->
| 版本线 | Redis | 变体 | 状态 | EOL | 基础镜像 | 镜像 tag |
|--------|-------|------|------|-----|----------|----------|
| `6.2` | `6.2.24` | uos | LTS | 2027-04-01 | `ghcr.io/blueapple168/uos-server-20-1070a:latest` | `ghcr.io/blueapple168/redis:6.2-uos`<br>`ghcr.io/blueapple168/redis:6.2.24-uos` |
| `6.2` | `6.2.24` | kylin | LTS | 2027-04-01 | `cr.kylinos.cn/kylin/kylin-server-minimal:v11-2503` | `ghcr.io/blueapple168/redis:6.2-kylin`<br>`ghcr.io/blueapple168/redis:6.2.24-kylin` |
| `7.2` | `7.2.17` | uos | LTS | 2029-12-01 | `ghcr.io/blueapple168/uos-server-20-1070a:latest` | `ghcr.io/blueapple168/redis:7.2-uos`<br>`ghcr.io/blueapple168/redis:7.2.17-uos` |
| `7.2` | `7.2.17` | kylin | LTS | 2029-12-01 | `cr.kylinos.cn/kylin/kylin-server-minimal:v11-2503` | `ghcr.io/blueapple168/redis:7.2-kylin`<br>`ghcr.io/blueapple168/redis:7.2.17-kylin` |
| `7.4` | `7.4.12` | uos | LTS | 2029-12-01 | `ghcr.io/blueapple168/uos-server-20-1070a:latest` | `ghcr.io/blueapple168/redis:7.4-uos`<br>`ghcr.io/blueapple168/redis:7.4.12-uos` |
| `7.4` | `7.4.12` | kylin | LTS | 2029-12-01 | `cr.kylinos.cn/kylin/kylin-server-minimal:v11-2503` | `ghcr.io/blueapple168/redis:7.4-kylin`<br>`ghcr.io/blueapple168/redis:7.4.12-kylin` |
| `8.0` | `8.0.6` | uos | 标准 | 2026-12-01 | `ghcr.io/blueapple168/uos-server-20-1070a:latest` | `ghcr.io/blueapple168/redis:8.0-uos`<br>`ghcr.io/blueapple168/redis:8.0.6-uos` |
| `8.0` | `8.0.6` | kylin | 标准 | 2026-12-01 | `cr.kylinos.cn/kylin/kylin-server-minimal:v11-2503` | `ghcr.io/blueapple168/redis:8.0-kylin`<br>`ghcr.io/blueapple168/redis:8.0.6-kylin` |
| `8.2` | `8.2.11` | uos | LTS | 2030-09-01 | `ghcr.io/blueapple168/uos-server-20-1070a:latest` | `ghcr.io/blueapple168/redis:8.2-uos`<br>`ghcr.io/blueapple168/redis:8.2.11-uos` |
| `8.2` | `8.2.11` | kylin | LTS | 2030-09-01 | `cr.kylinos.cn/kylin/kylin-server-minimal:v11-2503` | `ghcr.io/blueapple168/redis:8.2-kylin`<br>`ghcr.io/blueapple168/redis:8.2.11-kylin` |
| `8.4` | `8.4.8` | uos | 标准 | TBD | `ghcr.io/blueapple168/uos-server-20-1070a:latest` | `ghcr.io/blueapple168/redis:8.4-uos`<br>`ghcr.io/blueapple168/redis:8.4.8-uos` |
| `8.4` | `8.4.8` | kylin | 标准 | TBD | `cr.kylinos.cn/kylin/kylin-server-minimal:v11-2503` | `ghcr.io/blueapple168/redis:8.4-kylin`<br>`ghcr.io/blueapple168/redis:8.4.8-kylin` |
| `8.6` | `8.6.8` | uos | 标准 | TBD | `ghcr.io/blueapple168/uos-server-20-1070a:latest` | `ghcr.io/blueapple168/redis:8.6-uos`<br>`ghcr.io/blueapple168/redis:8.6.8-uos` |
| `8.6` | `8.6.8` | kylin | 标准 | TBD | `cr.kylinos.cn/kylin/kylin-server-minimal:v11-2503` | `ghcr.io/blueapple168/redis:8.6-kylin`<br>`ghcr.io/blueapple168/redis:8.6.8-kylin` |
| `8.8` | `8.8.4` | uos | 标准 | TBD | `ghcr.io/blueapple168/uos-server-20-1070a:latest` | `ghcr.io/blueapple168/redis:8.8-uos`<br>`ghcr.io/blueapple168/redis:8.8.4-uos` |
| `8.8` | `8.8.4` | kylin | 标准 | TBD | `cr.kylinos.cn/kylin/kylin-server-minimal:v11-2503` | `ghcr.io/blueapple168/redis:8.8-kylin`<br>`ghcr.io/blueapple168/redis:8.8.4-kylin` |
| `8.10` | `8.10.3` | uos | 标准 | TBD | `ghcr.io/blueapple168/uos-server-20-1070a:latest` | `ghcr.io/blueapple168/redis:8.10-uos`<br>`ghcr.io/blueapple168/redis:8.10.3-uos` |
| `8.10` | `8.10.3` | kylin | 标准 | TBD | `cr.kylinos.cn/kylin/kylin-server-minimal:v11-2503` | `ghcr.io/blueapple168/redis:8.10-kylin`<br>`ghcr.io/blueapple168/redis:8.10.3-kylin` |
<!-- END REDIS-MATRIX -->

> 上表由 `scripts/sync_readme.py` 根据目录结构 + 各 Dockerfile 的 ARG 自动生成，CI 每次运行会刷新并提交。

---

## 4. 目录结构

```
.
├── 8.8/                      # 版本线 = Redis 的 major.minor
│   ├── uos/                  # 变体 = 基础镜像
│   │   ├── Dockerfile        # 多阶段：builder 编译 → 运行镜像
│   │   └── docker-entrypoint.sh
│   └── kylin/
│       ├── Dockerfile
│       └── docker-entrypoint.sh
├── config/
│   └── lifecycle.json        # 官方 EOL 表（机器可读副本，手工同步）
├── scripts/
│   ├── resolve_upstream.py   # 解析 redis/redis 的 GA 版本
│   ├── lifecycle.py          # EOL 判定（是否支持 / 是否 LTS）
│   ├── ci_detect.py          # CI 策略引擎：算矩阵、补目录、升版本
│   ├── sync_readme.py        # 生成 README 版本矩阵
│   └── build-images.sh       # 本地批量构建
├── .github/workflows/docker-publish.yml
│
├── 6.2/ 7.0/ 7.2/ 7.4/ 7.4-rc/   # 上游 docker-library 模板产物（alpine/debian），不参与本仓库 CI
├── Dockerfile.template  versions.json  apply-templates.sh  update.sh ...  # 上游同步工具
└── README.md  BUILD.md
```

约定：**目录结构就是状态**。要新增一个版本线，建 `<line>/<variant>/Dockerfile` 即可，CI 会自动识别。

---

## 5. 快速开始

```bash
# UOS
docker run -d --name redis -p 6379:6379 \
  -v redis-data:/data \
  ghcr.io/blueapple168/redis:8.8.3-uos

# Kylin V11
docker run -d --name redis -p 6379:6379 \
  -v redis-data:/data \
  ghcr.io/blueapple168/redis:8.8.3-kylin

docker exec -it redis redis-cli ping
```

带密码与持久化：

```bash
docker run -d --name redis -p 6379:6379 \
  -v redis-data:/data \
  -e REDIS_PASSWORD='<强口令>' \
  ghcr.io/blueapple168/redis:8.8.3-uos \
  redis-server --appendonly yes
```

加载 RedisJSON：

```bash
docker run -d --name redis -p 6379:6379 \
  ghcr.io/blueapple168/redis:8.8.3-uos \
  redis-server --loadmodule /usr/local/lib/redis/modules/rejson.so
```

---

## 6. 构建

### 6.1 本地单版本

```bash
# 构建上下文就是变体目录，直接 docker build
docker build -t redis:8.8-uos 8.8/uos
docker build -t redis:8.8-kylin 8.8/kylin

# 指定版本 / 关闭 RedisJSON 模块（Rust 编译失败时的逃生口）
docker build --build-arg REDIS_VERSION=8.8.4 -t redis:8.8-uos 8.8/uos
docker build --build-arg WITH_MODULES=no  -t redis:8.8-kylin 8.8/kylin
```

### 6.2 本地批量构建

```bash
./scripts/build-images.sh                        # 全部版本线 × 全部变体
./scripts/build-images.sh --lines 8.8            # 只构建 8.8
./scripts/build-images.sh --variants kylin       # 只构建 kylin 变体
IMAGE=registry.local/redis ./scripts/build-images.sh
```

### 6.3 本地预演 CI 的策略决策（不写文件）

```bash
python3 scripts/ci_detect.py --dry-run
```

### 6.4 CI（GitHub Actions）

`.github/workflows/docker-publish.yml`：

| 触发 | 行为 |
|------|------|
| push 到 master（改到 `*/uos/**`、`*/kylin/**`、`scripts/**`、workflow） | 检测 + 构建改动涉及的镜像 |
| 每周一 06:00 UTC 定时 | 检查上游新版本，自动升版/补目录/更新 README，并构建 |
| 手动触发 | 可指定版本线、变体、强制版本号、是否跟踪 LTS、是否推送 |

CI 的 `detect` 作业会把版本号变更与 README 更新**提交回 master**（提交信息以 `chore(auto)` 开头），
随后 `build` 作业按矩阵构建并推送，最后 Trivy 扫描。

---

## 7. 维护指南

### 7.1 新增版本线

两种方式，任选：

- **自动**：等上游发新 GA，CI 会按模板自动创建 `<line>/uos`、`<line>/kylin`。
- **手动**：`cp -r 8.8/uos 8.9/uos`、`cp -r 8.8/kylin 8.9/kylin`，把两处 `ARG REDIS_VERSION` 改掉，
  然后 `python3 scripts/sync_readme.py` 刷新 README。

### 7.2 更新 EOL 表

官方 [version-mgmt](https://redis.io/docs/latest/operate/oss_and_stack/install/version-mgmt/) 页面更新后，
改 `config/lifecycle.json` 的 `versions` 与 `retrieved` 日期即可。已 EOL 的线会自动停止构建。

### 7.3 校验脚本行为

```bash
python3 scripts/lifecycle.py --list          # 看 EOL 全表
python3 scripts/lifecycle.py --check 8.8     # 单行判定
python3 scripts/resolve_upstream.py          # 上游 GA 版本（需网络；CI 里带 GITHUB_TOKEN 免限流）
python3 scripts/sync_readme.py --check       # README 是否需要刷新
```

### 7.4 已知坑

| 坑 | 说明 |
|----|------|
| Kylin 的包管理器是 **dnf5** | 没有 yum/microdnf；且 dnf5 只认 `--no-gpgchecks`，不认 `--nogpgcheck` |
| Kylin minimal 缺编译链 | tar/gzip/xz/make/gcc/useradd 都没有，Dockerfile 里必须先装 |
| RedisJSON 需要 Rust | 首次构建会拉 rustup 与 clang/lld，耗时较长；失败时可用 `WITH_MODULES=no` 跳过 |
| 两个变体的 entrypoint 需保持一致 | 目前各自一份副本（构建上下文自包含），改动时两边同步 |
| 上游 release 无 SHA256 | redis/redis 的 release 没有 uploaded assets，默认不做 tar.gz 校验；需要时传 `REDIS_DOWNLOAD_SHA` 并打开注释 |

---

## 8. 与官方 `redis` 镜像的差异

| 维度 | 官方 `redis:8.x` | 本仓库 |
|------|------------------|--------|
| 基础镜像 | `debian` / `alpine` | UOS Server 20 / Kylin V11 |
| 构建方式 | 官方 Dockerfile + 预编译包 | 源码编译（含 RedisJSON、TLS） |
| 版本范围 | 全历史版本 | 仅官方仍支持的版本线（按 EOL 表） |
| 适用场景 | 通用 / 公网 | 内网、信创、等保环境 |

---

## 9. 许可证

沿用上游 [LICENSE](LICENSE)。Redis 7.4 之前为 BSD-3-Clause，7.4 起为 RSALv2 / SSPLv1 双许可，
商用前请自行确认授权。
