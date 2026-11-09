#!/usr/bin/env bash
# Build the site, run checks, and refresh docs/ (served by GitHub Pages). Does not commit or push.
set -euo pipefail
cd "$(dirname "$0")"
python3 build.py
python3 check.py
find docs -mindepth 1 -maxdepth 1 ! -name CNAME ! -name .nojekyll -exec rm -rf {} +
cp -r dist/. docs/
echo "www.allfoodmach.com" > docs/CNAME
touch docs/.nojekyll
echo "docs/ updated. Review with: git status && git diff --stat"
