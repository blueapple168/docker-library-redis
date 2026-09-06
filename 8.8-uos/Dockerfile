# ==============================================
# Redis 8.8.2 (with RedisJSON) UOS Server 20 1070a
# 基于官方alpine Dockerfile逻辑改写，多阶段构建
# entrypoint 使用官方原版脚本，自动扫描加载modules目录下所有so模块
# ==============================================

ARG REDIS_VERSION=8.8.2
ARG BASE_IMAGE_TAG=uos-server-20-1070a:latest

FROM ghcr.io/blueapple168/${BASE_IMAGE_TAG} AS builder

LABEL maintainer="blueapple" \
      version="1.0" \
      description="Redis 8.8.2 with RedisJSON on UOS 1070a" \
      org.opencontainers.image.base.name="registry.uniontech.com/uos-server-base/uos-server-20-1070a:latest"

ARG REDIS_VERSION
ENV REDIS_VERSION=${REDIS_VERSION}
ENV REDIS_DOWNLOAD_URL=https://github.com/redis/redis/archive/refs/tags/${REDIS_VERSION}.tar.gz
ENV REDIS_DOWNLOAD_SHA=b58d3b51a93a05221fe0a835e915f9e472bb53db100af190e4259c33638d9a52

ENV TZ=Asia/Shanghai

RUN set -eux; \
    echo "${TZ}" > /etc/timezone; \
    sed -i 's/\$StateMode/ufu/g' /etc/yum.repos.d/UnionTechOS.repo; \
    yum makecache; \
    yum install -y --setopt=install_weak_deps=false --nogpgcheck --nodocs \
        tar gzip wget curl ca-certificates make gcc gcc-c++ glibc-devel openssl-devel libcap git which rsync xz unzip; \
    \
    ARCH=$(uname -m); \
    BUILD_WITH_MODULES="no"; \
    INSTALL_RUST_TOOLCHAIN="no"; \
    case "$ARCH" in \
        x86_64|aarch64) BUILD_WITH_MODULES="yes"; INSTALL_RUST_TOOLCHAIN="yes" ;; \
        *) echo >&2 "Modules are NOT supported! unsupported architecture: '$ARCH'" ;; \
    esac; \
    \
    if [ "$INSTALL_RUST_TOOLCHAIN" = "yes" ]; then \
        curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain stable --profile minimal; \
        source "$HOME/.cargo/env"; \
        yum install -y --setopt=install_weak_deps=false --nogpgcheck --nodocs \
            autoconf automake cmake libffi-devel libtool ncurses-devel clang lld llvm-devel python3 python3-devel; \
        PIP_BREAK_SYSTEM_PACKAGES=1 pip3 install -q --upgrade setuptools pip addict toml jinja2 ramp-packer; \
    fi; \
    \
    mkdir -p /usr/src/redis; \
    wget -q -O /tmp/redis.tar.gz "$REDIS_DOWNLOAD_URL"; \
    echo "$REDIS_DOWNLOAD_SHA */tmp/redis.tar.gz" | sha256sum -c -; \
    tar -xzf /tmp/redis.tar.gz -C /usr/src/redis --strip-components=1; \
    rm -f /tmp/redis.tar.gz; \
    \
    # 关闭 protected‑mode，与官方原版逻辑完全一致
    grep -E '^ *createBoolConfig\("protected-mode",.*, *1 *,.*\),' /usr/src/redis/src/config.c; \
    sed -ri 's!^( *createBoolConfig\("protected-mode",.*, *)1( *,.*\),)$!\10\2!' /usr/src/redis/src/config.c; \
    grep -E '^ *createBoolConfig\("protected-mode",.*, *0 *,.*\),' /usr/src/redis/src/config.c; \
    \
    # jemalloc configure 参数补丁，复刻官方alpine逻辑
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
        export LTO=1; \
        make -C /usr/src/redis/modules/redisjson get_source; \
        sed -i 's/^RUST_FLAGS=$/RUST_FLAGS += -C target-feature=-crt-static/' /usr/src/redis/modules/redisjson/src/Makefile; \
        grep 'RUST_FLAGS' /usr/src/redis/modules/redisjson/src/Makefile; \
    fi; \
    \
    make -C /usr/src/redis -j"$(nproc)" all; \
    make -C /usr/src/redis install; \
    \
    # 统一输出到/dist，后续拷贝到最终镜像，规避目录不存在报错
    mkdir -p /dist/bin /dist/modules; \
    cp -a /usr/local/bin/redis-* /dist/bin/; \
    if [ "$BUILD_WITH_MODULES" = "yes" ] && [ -f /usr/src/redis/modules/redisjson/src/target/release/rejson.so ]; then \
        cp /usr/src/redis/modules/redisjson/src/target/release/rejson.so /dist/modules/rejson.so; \
    fi; \
    \
    make -C /usr/src/redis distclean; \
    rm -rf /usr/src/redis /root/.cargo /root/.cache

# -------------------------- 最终运行镜像阶段 --------------------------
FROM ghcr.io/blueapple168/${BASE_IMAGE_TAG}

ARG REDIS_VERSION
LABEL maintainer="blueapple" \
      version="1.0" \
      description="Redis 8.8.2 with RedisJSON on UOS 1070a" \
      org.opencontainers.image.base.name="registry.uniontech.com/uos-server-base/uos-server-20-1070a:latest" \
      org.opencontainers.image.title="Redis" \
      org.opencontainers.image.version="${REDIS_VERSION}"

ENV TZ=Asia/Shanghai

# 用户创建：优先尝试gid=1000 uid=999；UOS镜像冲突则自动分配id；id redis强校验，禁止掩盖创建失败
RUN set -eux; \
    echo "${TZ}" > /etc/timezone; \
    if ! groupadd -r redis -g 1000; then groupadd -r redis; fi; \
    if ! useradd -r -g redis -u 999 redis; then useradd -r -g redis redis; fi; \
    id redis; \
    mkdir -p /data /usr/local/lib/redis/modules; \
    chown redis:redis /data; \
    sed -i 's/\$StateMode/ufu/g' /etc/yum.repos.d/UnionTechOS.repo; \
    yum makecache; \
    yum install -y --setopt=install_weak_deps=false --nogpgcheck --nodocs util-linux curl findutils; \
    yum clean all; rm -rf /var/cache/yum/*

# 从builder复制编译产物
COPY --from=builder /dist/bin/redis-* /usr/local/bin/
COPY --from=builder /dist/modules/* /usr/local/lib/redis/modules/

RUN set -eux; \
    chmod +x /usr/local/bin/redis-*; \
    redis-cli --version; redis-server --version

WORKDIR /data

# 使用官方原版entrypoint脚本
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

EXPOSE 6379

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["redis-server"]
