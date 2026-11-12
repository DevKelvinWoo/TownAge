#!/usr/bin/env bash
set -euo pipefail

if (( $# < 1 )); then
    printf '%s\n' 'Usage: bash start-townage-server.sh /path/to/TownAgeServer [server arguments...]' >&2
    exit 2
fi

executable=$1
shift
map=${TOWNAGE_MAP:-/Game/Maps/L_VillageTerrain_01}
port=${TOWNAGE_PORT:-7777}

if [[ ! $map =~ ^/Game(/[A-Za-z0-9_]+)+$ ]]; then
    printf '%s\n' 'TOWNAGE_MAP must be a cooked /Game package path.' >&2
    exit 2
fi

if [[ ! $port =~ ^[0-9]{1,5}$ ]] || (( 10#$port < 1 || 10#$port > 65535 )); then
    printf '%s\n' 'TOWNAGE_PORT must be an integer from 1 through 65535.' >&2
    exit 2
fi

if [[ ! -f $executable || ! -x $executable ]]; then
    printf 'Server executable is missing or not executable: %s\n' "$executable" >&2
    exit 2
fi

# Resolve a bare filename to a local path so exec does not search PATH.
case $executable in
    /*) ;;
    *) executable="./$executable" ;;
esac

exec -- "$executable" "$map" "-port=$((10#$port))" -unattended -stdout -FullStdOutLogOutput "$@"
