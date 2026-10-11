#!/usr/bin/env bash
# Usage: build_fixture.sh <go-billing|ts-app|ts-app-v2> <dest>
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)/fixtures"
name="$1"
dest="$2"
[ -e "$dest" ] && { echo "build_fixture: $dest already exists" >&2; exit 1; }

base="$name"
[ "$name" = ts-app-v2 ] && base=ts-app
mkdir -p "$dest"
cp -R "$here/$base/base/." "$dest/"
g() { git -C "$dest" -c user.name=fixture -c user.email=fixture@example.com "$@"; }
g init -q -b main
g add -A
g commit -q -m "base: invoices"

case "$name" in
  go-billing) branch=feat/void-invoices ;;
  ts-app) branch=feat/apply-credit ;;
  ts-app-v2) g am -q "$here/ts-app-v2/base.patch"; exit 0 ;;
  *) echo "build_fixture: unknown fixture $name" >&2; exit 1 ;;
esac
g switch -q -c "$branch"
g am -q "$here/$name/pr.patch"
g switch -q main
