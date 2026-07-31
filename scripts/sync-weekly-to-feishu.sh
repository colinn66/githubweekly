#!/usr/bin/env bash
set -euo pipefail

DEFAULT_FOLDER_TOKEN="GHUCfebcXlIgTgdSnRDcEdeunCe"
FOLDER_TOKEN="${FEISHU_WEEKLY_FOLDER_TOKEN:-$DEFAULT_FOLDER_TOKEN}"
IDENTITY="${LARK_IDENTITY:-user}"

usage() {
  cat <<'USAGE'
Usage:
  scripts/sync-weekly-to-feishu.sh [issue]

Examples:
  scripts/sync-weekly-to-feishu.sh        # sync latest _weekly/*.md
  scripts/sync-weekly-to-feishu.sh 121    # sync _weekly/121.md

Environment:
  FEISHU_WEEKLY_FOLDER_TOKEN  Override the default Feishu folder token.
  LARK_IDENTITY               lark-cli identity, default: user.

Note:
  This imports the markdown file as a Feishu docx document. It creates a new
  document each time; it does not overwrite or delete existing remote files.
USAGE
}

die() {
  printf 'Error: %s\n' "$*" >&2
  exit 1
}

latest_issue() {
  find _weekly -maxdepth 1 -type f -name '*.md' \
    | sed -n 's#^_weekly/\([0-9][0-9]*\)\.md$#\1#p' \
    | sort -n \
    | tail -n 1
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if ! command -v lark-cli >/dev/null 2>&1; then
  die "lark-cli is required but was not found in PATH."
fi

ISSUE="${1:-}"
if [[ -z "$ISSUE" ]]; then
  ISSUE="$(latest_issue)"
fi

[[ -n "$ISSUE" ]] || die "No weekly markdown files found under _weekly/."
[[ "$ISSUE" =~ ^[0-9]+$ ]] || die "Issue must be a number, got: $ISSUE"

FILE="_weekly/${ISSUE}.md"
[[ -f "$FILE" ]] || die "Weekly file not found: $FILE"

NAME="GitHub一周热点第${ISSUE}期"
LOG_FILE="$(mktemp)"
trap 'rm -f "$LOG_FILE"' EXIT

printf 'Importing %s to Feishu folder %s as "%s"...\n' "$FILE" "$FOLDER_TOKEN" "$NAME"

lark-cli drive +import \
  --as "$IDENTITY" \
  --file "$FILE" \
  --type docx \
  --folder-token "$FOLDER_TOKEN" \
  --name "$NAME" | tee "$LOG_FILE"

URL="$(grep -Eo 'https://[^"]+/docx/[^"]+' "$LOG_FILE" | tail -n 1 || true)"
if [[ -n "$URL" ]]; then
  printf '\nFeishu document: %s\n' "$URL"
fi
