#!/bin/sh -e

# mkdir "$SIMWORKER_TMPFS_PATH"
chown celery: "$SIMWORKER_TMPFS_PATH"

exec tini -- gosu "$USER" "$@"

exit 1
