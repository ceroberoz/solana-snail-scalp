#!/usr/bin/env bash
set -euo pipefail

# Create a disposable working directory for one verification run.
# Usage: verify_init.sh <repo-root> <new-workdir>
REPO=${1:?repo root is required}
WORKDIR=${2:?new workdir is required}

if [[ -e "$WORKDIR" ]]; then
  echo "Refusing to reuse an existing workdir: $WORKDIR" >&2
  exit 1
fi

mkdir -p "$WORKDIR/data"
for seed in sample_price_data.csv top10_solana_coins.json live_screened_tokens.json; do
  cp "$REPO/data/$seed" "$WORKDIR/data/$seed"
done

printf '%s\n' "$WORKDIR"
