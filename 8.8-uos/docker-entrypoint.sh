#!/bin/bash
set -e

SETPRIV="/usr/sbin/setpriv"
IS_REDIS_SENTINEL=""
IS_REDIS_SERVER=""
CONFIG=""

has_cap() {
    $SETPRIV -d 2>/dev/null | grep -q "Capability bounding set:.*\b$1\b"
}

check_for_sentinel() {
    local CMD="$1"
    shift
    if [ "$CMD" = '/usr/local/bin/redis-server' ]; then
        for arg in "$@"; do
            [ "$arg" = "--sentinel" ] && return 0
        done
    fi
    [ "$CMD" = '/usr/local/bin/redis-sentinel' ] && return 0
    return 1
}

fix_perms_and_owner() {
    local mode="$1"
    while IFS= read -r -d '' file; do
        if [ "$mode" = "rw" ] && $SETPRIV --reuid redis --regid redis --clear-groups test -r "$file" -a -w "$file" 2>/dev/null; then
            continue
        elif [ "$mode" = "r" ] && $SETPRIV --reuid redis --regid redis --clear-groups test -r "$file" 2>/dev/null; then
            continue
        fi
        new_mode=$mode
        [ -d "$file" ] && new_mode=${mode}x
        chown redis "$file" 2>/dev/null || true
        chmod "u+$new_mode" "$file" 2>/dev/null || true
    done
}

fix_data_dir_perms() {
    unknown_file="$(find . -mindepth 1 -maxdepth 1 \
        -not \( -name '*.rdb' -o -type d -name 'appendonlydir' \) -print -quit)"
    [ -z "$unknown_file" ] && find . -print0 | fix_perms_and_owner rw
}

fix_config_perms() {
    local config="$1"
    local mode="$2"
    [ ! -f "$config" ] && return 0
    local confdir="$(dirname "$config")"
    [ ! -d "$confdir" ] && return 0
    printf '%s\0%s\0' "$confdir" "$config" | fix_perms_and_owner "$mode"
}

# 处理参数
if [ "${1#-}" != "$1" ] || [ "${1%.conf}" != "$1" ]; then
    set -- redis-server "$@"
fi
CMD=$(command -v "$1" 2>/dev/null || :)
[ "$(readlink -f "$CMD")" = '/usr/local/bin/redis-server' ] && IS_REDIS_SERVER=1
check_for_sentinel "$CMD" "$@" && IS_REDIS_SENTINEL=1
[ "$IS_REDIS_SERVER" ] && [ "${2#-}" = "$2" ] && CONFIG="$2"

# 降权
if [ "$IS_REDIS_SERVER" ] && [ -z "$SKIP_DROP_PRIVS" ] && [ "$(id -u)" = '0' ] && has_cap setuid && has_cap setgid; then
    [ -z "$SKIP_FIX_PERMS" ] && {
        if [ "$IS_REDIS_SENTINEL" ]; then
            fix_config_perms "$CONFIG" rw
        else
            fix_data_dir_perms
            fix_config_perms "$CONFIG" r
        fi
    }
    CAPS_TO_KEEP=""
    has_cap sys_resource && CAPS_TO_KEEP=",+sys_resource"
    exec $SETPRIV \
        --nnp \
        --reuid redis --regid redis --clear-groups \
        --inh-caps=-all$CAPS_TO_KEEP \
        --ambient-caps=-all$CAPS_TO_KEEP \
        --bounding-set=-all$CAPS_TO_KEEP \
        "$0" "$@"
fi

# umask
[ "$(umask)" = '0022' ] && umask 0077

# 加载模块
if [ "$IS_REDIS_SERVER" ] && [ ! "$IS_REDIS_SENTINEL" ]; then
    echo "Starting Redis Server"
    modules_dir="/usr/local/lib/redis/modules/"
    if [ -d "$modules_dir" ] && [ -n "$(ls -A "$modules_dir" 2>/dev/null)" ]; then
        for module in "$modules_dir"/*.so; do
            [ -s "$module" ] && [ ! -d "$module" ] && [ -r "$module" ] && \
                set -- "$@" --loadmodule "$module"
        done
    fi
fi

exec "$@"
