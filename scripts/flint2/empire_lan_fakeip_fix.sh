#!/bin/sh
# DEPRECATED entrypoint — old slim FakeIP script wiped Telegram routes.
# Always delegate to the safe fixer.
exec /etc/podkop/empire-lan-fix.sh "$@"
