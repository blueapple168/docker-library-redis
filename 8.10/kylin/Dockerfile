# syntax=docker/dockerfile:1.4
# ==============================================
# Redis 8（含 RedisJSON 模块）—— Kylin Server V11 Minimal
#
# 与 8.8/uos 变体同源：同样的多阶段构建、同样的上游逻辑改写，差异只在
#   1. 基础镜像：cr.kylinos.cn/kylin/kylin-server-minimal:v11-2503
#   2. 包管理器：dnf5（无 yum / microdnf / dnf），按 dnf5 -> dnf -> microdnf -> yum 探测
#   3. Kylin minimal 层缺 tar/gzip/xz/make/gcc/useradd 等，必须先装包
#   4. dnf5 不认 --nogpgcheck（只认 --no-gpgchecks），因此不加该参数
#
# 构建逻辑与官方 alpine 版一致：
#   - 关掉 protected-mode 默认值（与官方 Dockerfile 相同的 sed）
#   - 给 jemalloc 补 --build/--with-lg-page/--with-lg-hugepage 参数
#   - BUILD_TLS=yes 启用 TLS
#   - x86_64/aarch64 额外编译 RedisJSON（Rust，LTO），产物放 /usr/local/lib/redis/modules
#
# SHA 校验说明：redis/redis 的 GitHub release 不带 uploaded assets，拿不到官方
# 发布的 SHA256，因此默认不做 tar.gz 校验（与 8.8/uos 变体一致）。
# 需要校验时：--build-arg REDIS_DOWNLOAD_SHA=<sha256>，并把下面两处注释打开。
#
# 版本号由 CI 从上游 releases 自动解析后通过 build-arg 覆盖，一般无需改本文件。
# ==============================================

ARG BASE_IMAGE_REPO=cr.kylinos.cn/kylin/kylin-server-minimal
ARG BASE_IMAGE_TAG=v11-2503

FROM ${BASE_IMAGE_REPO}:${BASE_IMAGE_TAG} AS builder

# 重新声明，供 LABEL 等指令展开（ARG 在 FROM 之后失效）
ARG BASE_IMAGE_REPO
ARG BASE_IMAGE_TAG
# buildx 注入的目标架构
ARG TARGETARCH

ARG REDIS_VERSION=8.10.3
# ARG REDIS_DOWNLOAD_SHA=
# auto = x86_64/aarch64 编译 RedisJSON，其它架构跳过；yes/no 可强制
ARG WITH_MODULES=auto

LABEL maintainer="blueapple" \
      version="1.0" \
      description="Redis ${REDIS_VERSION} (with RedisJSON) on Kylin Linux V11" \
      org.opencontainers.image.source="https://github.com/blueapple168/docker-library-redis" \
      org.opencontainers.image.base.name="${BASE_IMAGE_REPO}:${BASE_IMAGE_TAG}" \
      org.opencontainers.image.title="Redis" \
      org.opencontainers.image.version="${REDIS_VERSION}" \
      os="Kylin Linux" \
      os.version="${BASE_IMAGE_TAG}" \
      os.arch="amd64,arm64"

ENV TZ=Asia/Shanghai
ENV REDIS_VERSION=${REDIS_VERSION}
ENV REDIS_DOWNLOAD_URL=https://github.com/redis/redis/archive/refs/tags/${REDIS_VERSION}.tar.gz
# ENV REDIS_DOWNLOAD_SHA=${REDIS_DOWNLOAD_SHA}

RUN set -euxo pipefail; \
    echo "${TZ}" > /etc/timezone; \
    \
    : "=== 包管理器探测（Kylin V11 是 dnf5，不写死单一命令） ===" ; \
    PKG_MGR=""; \
    for m in dnf5 dnf microdnf yum; do \
        if command -v "$m" >/dev/null 2>&1; then PKG_MGR="$(command -v "$m")"; break; fi; \
        for d in /usr/bin /bin /usr/sbin /sbin; do \
            if [ -x "${d}/${m}" ]; then PKG_MGR="${d}/${m}"; break 2; fi; \
        done; \
    done; \
    if [ -z "$PKG_MGR" ]; then echo "ERROR: 未找到可用的包管理器 (dnf5/dnf/microdnf/yum)" >&2; exit 1; fi; \
    echo "==> 使用包管理器: ${PKG_MGR}"; \
    install_any() { \
        for p in "$@"; do \
            if "$PKG_MGR" install -y --setopt=install_weak_deps=False "$p" >/dev/null 2>&1; then \
                echo "  installed: $p"; return 0; \
            fi; \
        done; \
        echo "  WARN: 候选包均未安装成功: $*" >&2; return 0; \
    }; \
    \
    : "=== 编译依赖（Kylin minimal 层缺编译链，必须显式装） ===" ; \
    HARD_PKGS="tar gzip xz curl wget ca-certificates make gcc gcc-c++ glibc-devel openssl-devel git which rsync unzip findutils coreutils bash procps-ng"; \
    if ! "$PKG_MGR" install -y --setopt=install_weak_deps=False $HARD_PKGS; then \
        echo "WARN: 批量安装失败，改为逐包安装以定位缺包" >&2; \
        for _p in $HARD_PKGS; do install_any "$_p"; done; \
    fi; \
    install_any libcap libcap-devel; \
    install_any perl-Data-Dumper; \
    for c in tar xz curl make gcc g++ git awk sed grep find nproc sha256sum; do \
        command -v "$c" >/dev/null 2>&1 \
            || { echo "ERROR: 缺少命令 ${c}，请确认麒麟仓库源可用" >&2; exit 1; }; \
    done; \
    \
    : "=== 架构判定：x86_64/aarch64 才编译 RedisJSON（Rust） ===" ; \
    ARCH=$(uname -m); \
    BUILD_WITH_MODULES="no"; \
    case "$ARCH" in \
        x86_64|aarch64) BUILD_WITH_MODULES="yes" ;; \
        *) echo >&2 "Modules are NOT supported! unsupported architecture: '$ARCH'" ;; \
    esac; \
    case "${WITH_MODULES}" in \
        yes) BUILD_WITH_MODULES="yes" ;; \
        no)  BUILD_WITH_MODULES="no" ;; \
        auto) : ;; \
        *) echo "ERROR: WITH_MODULES 只能是 auto/yes/no，收到 '${WITH_MODULES}'" >&2; exit 1 ;; \
    esac; \
    : "=== 版本闸门：RedisJSON 自 8.0 起才并入主仓库，6.x/7.x 源码树里没有 modules/redisjson ===" ; \
    REDIS_MAJOR="${REDIS_VERSION%%.*}"; \
    case "$REDIS_MAJOR" in ''|*[!0-9]*) REDIS_MAJOR=0 ;; esac; \
    if [ "$REDIS_MAJOR" -lt 8 ]; then \
        BUILD_WITH_MODULES="no"; \
        echo "==> Redis ${REDIS_VERSION} 不含内置模块，跳过 RedisJSON 编译"; \
    fi; \
    echo "==> ARCH=${ARCH} BUILD_WITH_MODULES=${BUILD_WITH_MODULES}"; \
    \
    if [ "$BUILD_WITH_MODULES" = "yes" ]; then \
        : "=== Rust 工具链（RedisJSON 用） ===" ; \
        curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain stable --profile minimal; \
        . "$HOME/.cargo/env"; \
        "$PKG_MGR" install -y --setopt=install_weak_deps=False \
            autoconf automake cmake libffi-devel libtool ncurses-devel clang lld llvm-devel \
            python3 python3-devel python3-pip; \
        PIP_BREAK_SYSTEM_PACKAGES=1 pip3 install -q --upgrade setuptools pip addict toml jinja2 ramp-packer; \
    fi; \
    \
    : "=== 下载 Redis 源码 ===" ; \
    mkdir -p /usr/src/redis; \
    curl -fsSL --connect-timeout 20 --retry 5 --retry-delay 5 -o /tmp/redis.tar.gz "$REDIS_DOWNLOAD_URL"; \
    : "=== SHA 校验默认关闭：上游 release 无 digest；需要时传 REDIS_DOWNLOAD_SHA 并取消注释 ===" ; \
    : 'echo "$REDIS_DOWNLOAD_SHA */tmp/redis.tar.gz" | sha256sum -c -' ; \
    tar -xzf /tmp/redis.tar.gz -C /usr/src/redis --strip-components=1; \
    rm -f /tmp/redis.tar.gz; \
    : "=== 兜底：源码树里确实没有 modules/redisjson 时不编译模块 ===" ; \
    if [ "$BUILD_WITH_MODULES" = "yes" ] && [ ! -d /usr/src/redis/modules/redisjson ]; then \
        echo >&2 "WARN: 未找到 modules/redisjson，改为不编译模块"; \
        BUILD_WITH_MODULES="no"; \
    fi; \
    \
    : "=== 关闭 protected-mode 默认值（与官方原版逻辑一致） ===" ; \
    grep -E '^ *createBoolConfig\("protected-mode",.*, *1 *,.*\),' /usr/src/redis/src/config.c; \
    sed -ri 's!^( *createBoolConfig\("protected-mode",.*, *)1( *,.*\),)$!\10\2!' /usr/src/redis/src/config.c; \
    grep -E '^ *createBoolConfig\("protected-mode",.*, *0 *,.*\),' /usr/src/redis/src/config.c; \
    \
    : "=== jemalloc configure 参数补丁（复刻官方逻辑） ===" ; \
    gnuArch=$(gcc -dumpmachine); \
    extraJemallocConfigureFlags="--build=$gnuArch"; \
    case "$ARCH" in \
        x86_64|i686) extraJemallocConfigureFlags="$extraJemallocConfigureFlags --with-lg-page=12" ;; \
        *) extraJemallocConfigureFlags="$extraJemallocConfigureFlags --with-lg-page=16" ;; \
    esac; \
    extraJemallocConfigureFlags="$extraJemallocConfigureFlags --with-lg-hugepage=21"; \
    grep -F 'cd jemalloc && ./configure ' /usr/src/redis/deps/Makefile; \
    sed -ri 's!cd jemalloc && ./configure !&'"$extraJemallocConfigureFlags"' !' /usr/src/redis/deps/Makefile; \
    grep -F "cd jemalloc && ./configure $extraJemallocConfigureFlags " /usr/src/redis/deps/Makefile; \
    \
    export PATH="/root/.cargo/bin:$PATH"; \
    export RUST_DYN_CRT=1; \
    export BUILD_TLS=yes; \
    \
    if [ "$BUILD_WITH_MODULES" = "yes" ]; then \
        : "=== 取 RedisJSON 源码并关闭静态 CRT（避免与系统 glibc 冲突） ===" ; \
        export LTO=1; \
        make -C /usr/src/redis/modules/redisjson get_source; \
        sed -i 's/^RUST_FLAGS=$/RUST_FLAGS += -C target-feature=-crt-static/' /usr/src/redis/modules/redisjson/src/Makefile; \
        grep 'RUST_FLAGS' /usr/src/redis/modules/redisjson/src/Makefile; \
    fi; \
    \
    : "=== 编译并安装（产物先收拢到 /dist，再拷进最终镜像） ===" ; \
    make -C /usr/src/redis -j"$(nproc)" all; \
    make -C /usr/src/redis install; \
    mkdir -p /dist/bin /dist/modules; \
    cp -a /usr/local/bin/redis-* /dist/bin/; \
    if [ "$BUILD_WITH_MODULES" = "yes" ] && [ -f /usr/src/redis/modules/redisjson/src/target/release/rejson.so ]; then \
        cp /usr/src/redis/modules/redisjson/src/target/release/rejson.so /dist/modules/rejson.so; \
    fi; \
    : "=== 占位文件：模块为空时 COPY /dist/modules/* 仍然成立 ===" ; \
    [ -n "$(ls -A /dist/modules)" ] || touch /dist/modules/.placeholder; \
    \
    make -C /usr/src/redis distclean; \
    rm -rf /usr/src/redis /root/.cargo /root/.cache

# -------------------------- 最终运行镜像 --------------------------

FROM ${BASE_IMAGE_REPO}:${BASE_IMAGE_TAG}

# 第二阶段同样要重新声明，否则 LABEL 里的 ${BASE_IMAGE_REPO}/${BASE_IMAGE_TAG} 会展开成空
ARG BASE_IMAGE_REPO
ARG BASE_IMAGE_TAG
ARG REDIS_VERSION

LABEL maintainer="blueapple" \
      version="1.0" \
      description="Redis ${REDIS_VERSION} (with RedisJSON) on Kylin Linux V11" \
      org.opencontainers.image.source="https://github.com/blueapple168/docker-library-redis" \
      org.opencontainers.image.base.name="${BASE_IMAGE_REPO}:${BASE_IMAGE_TAG}" \
      org.opencontainers.image.title="Redis" \
      org.opencontainers.image.version="${REDIS_VERSION}" \
      os="Kylin Linux" \
      os.version="${BASE_IMAGE_TAG}" \
      os.arch="amd64,arm64"

ENV TZ=Asia/Shanghai

# 运行期只留必要组件：setpriv(util-linux) 供 entrypoint 降权，find 供权限修复
RUN set -euxo pipefail; \
    echo "${TZ}" > /etc/timezone; \
    PKG_MGR=""; \
    for m in dnf5 dnf microdnf yum; do \
        if command -v "$m" >/dev/null 2>&1; then PKG_MGR="$(command -v "$m")"; break; fi; \
        for d in /usr/bin /bin /usr/sbin /sbin; do \
            if [ -x "${d}/${m}" ]; then PKG_MGR="${d}/${m}"; break 2; fi; \
        done; \
    done; \
    if [ -z "$PKG_MGR" ]; then echo "ERROR: 未找到可用的包管理器" >&2; exit 1; fi; \
    "$PKG_MGR" install -y --setopt=install_weak_deps=False util-linux curl findutils shadow ca-certificates; \
    \
    : "=== redis 用户：优先 gid=1000 / uid=999，冲突则自动分配；id 强校验 ===" ; \
    if ! groupadd -r redis -g 1000; then groupadd -r redis; fi; \
    if ! useradd -r -g redis -u 999 redis; then useradd -r -g redis redis; fi; \
    id redis; \
    mkdir -p /data /usr/local/lib/redis/modules; \
    chown redis:redis /data; \
    "$PKG_MGR" clean all || true; \
    rm -rf /var/cache/dnf/* /var/cache/libdnf5/* /var/cache/yum/* /var/tmp/*

COPY --from=builder /dist/bin/redis-* /usr/local/bin/
COPY --from=builder /dist/modules/* /usr/local/lib/redis/modules/

RUN set -eux; \
    chmod +x /usr/local/bin/redis-*; \
    redis-cli --version; \
    redis-server --version

WORKDIR /data

COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

EXPOSE 6379

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["redis-server"]
