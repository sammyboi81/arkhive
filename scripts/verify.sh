#!/usr/bin/env bash
# One command to prove ArkHive is tamper-evident. No API key, no network.
# Writes a throwaway hash-chained ledger, verifies it, forges one block, and
# shows verification CATCH the forgery.
#
#   ./scripts/verify.sh
#
set -euo pipefail
cd "$(dirname "$0")/.."
exec python -m benchmark
