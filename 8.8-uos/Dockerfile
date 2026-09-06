# ============================================================
# Redis 8.8.2 + RedisJSON for UOS Server 20 (1070a)
# Base: uos-server-20-1070a:latest (x86_64/arm64)
# ============================================================
# 使用说明：
#   构建: docker buildx build --platform linux/amd64,linux/arm64 -t redis-uos:8.8.2 .
#   运行: docker run -d --name redis redis-uos:8.8.2
# ============================================================
ARG REDIS_VERSION=8.8.2
ARG YQ_VERSION=v4.53.6
ARG BASE_IMAGE_TAG=uos-server-20-1070a:latest

FROM ghcr.io/blueapple168/${BASE_IMAGE_TAG} AS builder
LABEL maintainer="blueapple" \
      version="1.0" \
      description="Redis 8.8.2 with RedisJSON on UOS 1070a" \
      org.opencontainers.image.base.name="registry.uniontech.com/uos-server-base/uos-server-20-1070a:latest" \
      org.opencontainers.image.title="Redis" \
      org.opencontainers.image.version="${REDIS_VERSION}"

ENV REDIS_VERSION=${REDIS_VERSION} \
    TZ=Asia/Shanghai \
    APP_USER=redis \
    REDIS_DOWNLOAD_URL=https://github.com/redis/redis/archive/refs/tags/${REDIS_VERSION}.tar.gz \
    REDIS_DOWNLOAD_SHA=b58d3b51a93a05221fe0a835e915f9e472bb53db100af190e4259c33638d9a52 \
    PATH=/root/.cargo/bin:/usr/local/bin:/usr/bin:/usr/sbin:/sbin

RUN set -eux && \
    sed -i 's/\$StateMode/ufu/g' /etc/yum.repos.d/UnionTechOS.repo && \
    ln -sf /usr/share/zoneinfo/${TZ} /etc/localtime && \
    echo "${TZ}" > /etc/timezone && \
    yum makecache && \
    yum install -y --setopt=install_weak_deps=false --nogpgcheck --nodocs \
        tar gzip curl ca-certificates git procps-ng wget which \
        make gcc gcc-c++ glibc-devel glibc-headers kernel-headers openssl-devel libcap && \
    ARCH=$(uname -m | sed -e 's/x86_64/amd64/' -e 's/aarch64/arm64/') && \
    echo "Building for architecture: $ARCH" && \
    if [ "$ARCH" = "amd64" ] || [ "$ARCH" = "arm64" ]; then \
        curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain stable --profile minimal; \
        yum install -y --setopt=install_weak_deps=false --nogpgcheck --nodocs \
            autoconf automake cmake libffi-devel libtool ncurses-devel \
            python3 python3-devel clang lld clang-devel llvm-devel rsync unzip xz && \
        pip3 install --upgrade pip setuptools wheel --quiet; \
    fi && \
    mkdir -p /usr/src/redis && \
    cd /usr/src/redis && \
    wget -q -O redis.tar.gz "$REDIS_DOWNLOAD_URL" && \
    echo "$REDIS_DOWNLOAD_SHA *redis.tar.gz" | sha256sum -c - && \
    tar -xzf redis.tar.gz --strip-components=1 && \
    rm redis.tar.gz && \
    sed -ri 's!^( *createBoolConfig\("protected-mode",.*, *)1( *,.*\),)$!\10\2!' /usr/src/redis/src/config.c || true && \
    gnuArch=$(gcc -dumpmachine | awk -F- '{ print $1 }') && \
    extraJemallocConfigureFlags="--build=$gnuArch" && \
    case "$(uname -m)" in \
        amd64 | i386 | x32) extraJemallocConfigureFlags="$extraJemallocConfigureFlags --with-lg-page=12" ;; \
        *) extraJemallocConfigureFlags="$extraJemallocConfigureFlags --with-lg-page=16" ;; \
    esac && \
    extraJemallocConfigureFlags="$extraJemallocConfigureFlags --with-lg-hugepage=21" && \
    sed -ri 's!cd jemalloc && ./configure !&'"$extraJemallocConfigureFlags"' !' /usr/src/redis/deps/Makefile || true && \
    export BUILD_TLS=yes && \
    if [ "$ARCH" = "amd64" ] || [ "$ARCH" = "arm64" ]; then \
        export LTO=1 RUST_DYN_CRT=1; \
        cd /usr/src/redis/modules/redisjson && \
        make get_source && \
        sed -i 's/^RUST_FLAGS=$/RUST_FLAGS += -C target-feature=-crt-static/' /usr/src/redis/modules/redisjson/src/Makefile 2>/dev/null || true; \
        make -j "$(nproc)"; \
    fi && \
    cd /usr/src/redis && \
    make -j "$(nproc)" all && \
    make install && \
    # ==========================================
    # 输出目录：改用 /output，避开 /tmp/* 清理误伤
    # ==========================================
    mkdir -p /output/{bin,share,etc,lib,modules} && \
    cp -a /usr/local/bin/redis-* /output/bin/ && \
    cp -a /usr/local/share/redis /output/share/ 2>/dev/null || true && \
    cp -a /usr/local/etc/redis /output/etc/ 2>/dev/null || true && \
    cp -a /usr/local/lib/redis /output/lib/ 2>/dev/null || true && \
    if [ "$ARCH" = "amd64" ] || [ "$ARCH" = "arm64" ]; then \
        cp /usr/src/redis/modules/redisjson/src/target/release/*.so /output/modules/; \
    fi && \
    make distclean || true

# builder阶段清理：不触碰/output目录！只清理/tmp，保留/output
RUN set -eux; \
    yum clean all; \
    rm -rf \
        /var/cache/yum/* \
        /var/tmp/* \
        /tmp/* \
        /root/.cargo/registry/* \
        /root/.cargo/git/* \
        /root/.cache \
        /root/.gitconfig \
        /usr/src/redis

# ---------------- 最终镜像 ----------------
FROM ghcr.io/blueapple168/${BASE_IMAGE_TAG}
LABEL maintainer="blueapple" version="1.0" description="Redis 8.8.2 with RedisJSON on UOS 1070a"

ENV TZ=Asia/Shanghai APP_USER=redis PATH=/usr/local/bin:/usr/bin:/usr/sbin:/sbin

# 最终镜像创建redis用户（builder的用户不会继承过来，必须在最终镜像创建）
RUN set -eux; \
    groupadd -r "${APP_USER}" -g 1000 || true; \
    useradd -r -u 1000 -g "${APP_USER}" -d "/data" -s /bin/bash "${APP_USER}" || true; \
    mkdir -p /data && chown redis:redis /data

# 从builder复制编译产物
COPY --from=builder /output/bin/redis-* /usr/local/bin/
COPY --from=builder /output/share/redis /usr/local/share/redis
COPY --from=builder /output/etc/redis /usr/local/etc/redis
COPY --from=builder /output/lib/redis /usr/local/lib/redis
COPY --from=builder /output/modules /usr/local/lib/redis/modules

COPY --from=builder /data /data

RUN set -eux; \
    chmod +x /usr/local/bin/redis-*; \
    yum clean all 2>/dev/null || true

WORKDIR /data
EXPOSE 6379

COPY --chmod=755 docker-entrypoint.sh /usr/local/bin/
ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["redis-server"]
