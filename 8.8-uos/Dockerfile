# ============================================================
# Redis 8.8.2 + RedisJSON for UOS Server 20 (1070a)
# Base: uos-server-20-1070a:latest (x86_64/arm64)
# ============================================================
# 使用说明：
#   构建: docker build -t redis-uos:8.8.2 .
#   运行: docker run -d --name redis redis-uos:8.8.2
#   自定义配置: docker run -d -v /path/to/redis.conf:/usr/local/etc/redis/redis.conf redis-uos:8.8.2 redis-server /usr/local/etc/redis/redis.conf
# ============================================================

# 全局构建参数
ARG REDIS_VERSION=8.8.2
ARG YQ_VERSION=v4.53.6
ARG BASE_IMAGE_TAG=uos-server-20-1070a:latest

# ============================================================
# 第一阶段：基础镜像
# ============================================================
FROM ghcr.io/blueapple168/${BASE_IMAGE_TAG} AS builder

# 维护者信息
LABEL maintainer="blueapple" \
      version="1.0" \
      description="Redis 8.8.2 with RedisJSON on UOS 1070a" \
      org.opencontainers.image.base.name="registry.uniontech.com/uos-server-base/uos-server-20-1070a:latest" \
      org.opencontainers.image.description="Redis packaged on UOS 10700a" \
      org.opencontainers.image.title="Redis" \
      org.opencontainers.image.version="${REDIS_VERSION}"

# ============================================================
# 环境变量
# ============================================================
ENV REDIS_VERSION=${REDIS_VERSION} \
    TZ=Asia/Shanghai \
    APP_USER=redis \
    REDIS_DOWNLOAD_URL=https://github.com/redis/redis/archive/refs/tags/${REDIS_VERSION}.tar.gz \
    REDIS_DOWNLOAD_SHA=b58d3b51a93a05221fe0a835e915f9e472bb53db100af190e4259c33638d9a52 \
    PATH=/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin:/sbin:/bin

# ============================================================
# 构建阶段：编译 Redis + RedisJSON
# ============================================================
RUN set -eux && \
    # 修复 UOS yum repo
    sed -i 's/\$StateMode/ufu/g' /etc/yum.repos.d/UnionTechOS.repo && \
    yum -y update && \
    # 时区配置
    ln -sf /usr/share/zoneinfo/${TZ} /etc/localtime && \
    echo "${TZ}" > /etc/timezone && \
    # 更新 yum 缓存
    yum makecache && \
    # ==========================================
    # 安装编译依赖（基础工具链）
    # ==========================================
    yum install -y \
        --setopt=install_weak_deps=false \
        --nogpgcheck \
        --nodocs \
        tar \
        gzip \
        curl \
        ca-certificates \
        git \
        procps-ng \
        wget \
        which \
        make \
        gcc \
        gcc-c++ \
        glibc-devel \
        glibc-headers \
        kernel-headers \
        openssl-devel \
        && \
    # ==========================================
    # 架构检测（适配 x86_64/arm64）
    # ==========================================
    ARCH=$(uname -m | sed -e 's/x86_64/amd64/' -e 's/aarch64/arm64/') && \
    echo "Building for architecture: $ARCH" && \
    # ==========================================
    # 安装 Rust 工具链（用于 RedisJSON 模块）
    # ==========================================
    if [ "$ARCH" = "amd64" ] || [ "$ARCH" = "arm64" ]; then \
        curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain stable --profile minimal; \
        export PATH="/root/.cargo/bin:$PATH"; \
        # 安装 Rust 依赖包
        yum install -y \
            --setopt=install_weak_deps=false \
            --nogpgcheck \
            --nodocs \
            autoconf \
            automake \
            cmake \
            libffi-devel \
            libtool \
            ncurses-devel \
            python3 \
            python3-devel \
            cargo \
            clang \
            lld \
            clang-devel \
            llvm-devel \
            openssh \
            rsync \
            unzip \
            xz \
            && \
        # pip 升级
        pip3 install --upgrade pip setuptools wheel; \
    fi && \
    # ==========================================
    # 下载并编译 Redis
    # ==========================================
    mkdir -p /usr/src/redis && \
    cd /usr/src/redis && \
    wget -O redis.tar.gz "$REDIS_DOWNLOAD_URL" && \
    echo "$REDIS_DOWNLOAD_SHA *redis.tar.gz" | sha256sum -c - && \
    tar -xzf redis.tar.gz --strip-components=1 && \
    rm redis.tar.gz && \
    # ==========================================
    # 禁用 protected-mode（Docker 场景无需）
    # ==========================================
    grep -E '^ *createBoolConfig[(]"protected-mode",.*, *1 *,.*[)],$' /usr/src/redis/src/config.c && \
    sed -ri 's!^( *createBoolConfig[(]"protected-mode",.*, *)1( *,.*[)],)$!\10\2!' /usr/src/redis/src/config.c && \
    grep -E '^ *createBoolConfig[(]"protected-mode",.*, *0 *,.*[)],$' /usr/src/redis/src/config.c && \
    # ==========================================
    # jemalloc 配置优化
    # ==========================================
    gnuArch=$(gcc -dumpmachine | awk -F- '{ print $1 }') && \
    extraJemallocConfigureFlags="--build=$gnuArch" && \
    dpkgArch=$(uname -m) && \
    case "${dpkgArch}" in \
        amd64 | i386 | x32) extraJemallocConfigureFlags="$extraJemallocConfigureFlags --with-lg-page=12" ;; \
        *) extraJemallocConfigureFlags="$extraJemallocConfigureFlags --with-lg-page=16" ;; \
    esac && \
    extraJemallocConfigureFlags="$extraJemallocConfigureFlags --with-lg-hugepage=21" && \
    grep -F 'cd jemalloc && ./configure ' /usr/src/redis/deps/Makefile && \
    sed -ri 's!cd jemalloc && ./configure !&'"$extraJemallocConfigureFlags"' !' /usr/src/redis/deps/Makefile && \
    grep -F "cd jemalloc && ./configure $extraJemallocConfigureFlags " /usr/src/redis/deps/Makefile && \
    # ==========================================
    # RedisJSON 模块编译
    # ==========================================
    export PATH="/root/.cargo/bin:$PATH" && \
    export BUILD_TLS=yes && \
    if [ "$ARCH" = "amd64" ] || [ "$ARCH" = "arm64" ]; then \
        export LTO=1; \
        export RUST_DYN_CRT=1; \
        cd /usr/src/redis/modules/redisjson && \
        make get_source; \
        sed -i 's/^RUST_FLAGS=$/RUST_FLAGS += -C target-feature=-crt-static/' /usr/src/redis/modules/redisjson/src/Makefile; \
        grep -E 'RUST_FLAGS' /usr/src/redis/modules/redisjson/src/Makefile; \
        make -j "$(nproc)"; \
    fi && \
    # ==========================================
    # 编译 Redis 主程序
    # ==========================================
    cd /usr/src/redis && \
    make -j "$(nproc)" all && \
    make install && \
    make distclean && \
    # ==========================================
    # 清理源码
    # ==========================================
    rm -rf /usr/src/redis && \
    # ==========================================
    # 安装 setpriv（用于降权）
    # ==========================================
    yum install -y \
        --setopt=install_weak_deps=false \
        --nogpgcheck \
        --nodocs \
        libcap && \
    # ==========================================
    # 创建 redis 用户和目录
    # ==========================================
    groupadd -r "${APP_USER}" -g 1000 || true && \
    useradd -r -u 1000 -g "${APP_USER}" -d "/data" -s /bin/bash "${APP_USER}" || true && \
    mkdir -p /data && \
    chown redis:redis /data && \
    # ==========================================
    # 复制 entrypoint 脚本
    # ==========================================
    mkdir -p /usr/local/bin && \
    # 注意：entrypoint.sh 需要单独 COPY
    # ==========================================
    # 清理缓存和临时文件
    # ==========================================
    yum clean all && \
    rm -rf \
        /var/cache/yum/* \
        /var/tmp/* \
        /tmp/* \
        /root/.cargo/registry/* \
        /root/.cargo/git/* \
        ~/.cache/* \
        ~/.gitconfig

WORKDIR /data

EXPOSE 6379

COPY --chmod=755 docker-entrypoint.sh /usr/local/bin/
ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["redis-server"]
