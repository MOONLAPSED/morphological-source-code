#!/usr/bin/env bash
# Idempotent import-only script: import branch trees into imports/<branch>/
# - Always imports the branch tree into `imports/<sanitized-branch>/` unless already present
# - Does NOT attempt merges into the working tree other than importing under the prefix
# - Supports DRY_RUN and an optional FORCE_UPDATE to replace an existing import

set -euo pipefail

# Config
TARGET_BRANCH="${TARGET_BRANCH:-production}"
BRANCHES=(
  "checkpoint0"
  "revert-99-quantum-13e271a2"
  "quine"
  "quantum-13e271a2"
  "kitchen"
  "cognosis2"
  "checkpoint10"
  "checkpoint9"
  "checkpoint8"
  "checkpoint7"
  "checkpoint6"
  "checkpoint5"
  "checkpoint4"
  "checkpoint2"
  "checkpoint1"
  "staging"
)
IMPORT_ROOT="${IMPORT_ROOT:-imports}"
REMOTE="${REMOTE:-origin}"
DRY_RUN="${DRY_RUN:-false}"
FORCE_UPDATE="${FORCE_UPDATE:-false}"   # set to true to replace an existing import
BACKUP_PREFIX="backup/import-$(date +%Y%m%d-%H%M%S)"

# Helpers
log() { printf '\033[1;34m[INFO]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[WARN]\033[0m %s\n' "$*"; }
err() { printf '\033[1;31m[ERROR]\033[0m %s\n' "$*"; }
san_dirname() { echo "$1" | sed -E 's/[^a-zA-Z0-9._-]/_/g'; }

run() {
  if [ "$DRY_RUN" = "true" ]; then
    echo "DRYRUN: $*"
  else
    eval "$@"
  fi
}

# Preflight
if ! git rev-parse --git-dir >/dev/null 2>&1; then
  err "Not a git repository (or not inside one)."
  exit 1
fi

log "Fetching remote refs from '$REMOTE'..."
if [ "$DRY_RUN" = "true" ]; then
  echo "DRYRUN: git fetch --all --prune"
else
  git fetch --all --prune
fi

# Ensure target exists locally and switch to it (we commit imports onto this branch)
if ! git show-ref --verify --quiet "refs/heads/$TARGET_BRANCH"; then
  if git show-ref --verify --quiet "refs/remotes/$REMOTE/$TARGET_BRANCH"; then
    log "Creating local tracking branch '$TARGET_BRANCH' from '$REMOTE/$TARGET_BRANCH'..."
    run git checkout -b "$TARGET_BRANCH" "$REMOTE/$TARGET_BRANCH"
  else
    warn "Target branch '$TARGET_BRANCH' doesn't exist locally or on remote — creating empty branch."
    run git checkout --orphan "$TARGET_BRANCH"
    run git rm -rf . || true
    run git commit --allow-empty -m "Create target branch $TARGET_BRANCH"
  fi
else
  run git checkout "$TARGET_BRANCH"
fi

# Create a backup branch
BACKUP="$BACKUP_PREFIX"
log "Creating backup branch '$BACKUP' from current HEAD..."
run git branch "$BACKUP"

# Ensure import root exists in working tree (not strictly necessary, read-tree will create files)
if [ "$DRY_RUN" != "true" ]; then
  mkdir -p "$IMPORT_ROOT"
  git add --intent-to-add "$IMPORT_ROOT" >/dev/null 2>&1 || true
fi

for BRANCH in "${BRANCHES[@]}"; do
  log "Processing branch: '$BRANCH'"

  # Resolve ref: prefer local, then remote
  if git show-ref --verify --quiet "refs/heads/$BRANCH"; then
    REF="refs/heads/$BRANCH"
  elif git show-ref --verify --quiet "refs/remotes/$REMOTE/$BRANCH"; then
    REF="refs/remotes/$REMOTE/$BRANCH"
  else
    warn "Branch '$BRANCH' not found locally or on '$REMOTE'. Skipping."
    continue
  fi

  BR_REF=$(git rev-parse --verify "$REF")
  if [ -z "$BR_REF" ]; then
    warn "Couldn't resolve ref for '$BRANCH'. Skipping."
    continue
  fi

  SAN_NAME=$(san_dirname "$BRANCH")
  IMPORT_PATH="$IMPORT_ROOT/$SAN_NAME"

  # If import already exists and not forcing update, skip to keep idempotence
  if git rev-parse --verify --quiet "HEAD:$IMPORT_PATH" >/dev/null 2>&1; then
    if [ "$FORCE_UPDATE" = "true" ]; then
      warn "Import path '$IMPORT_PATH' exists and FORCE_UPDATE=true — replacing import."
    else
      log "Import path '$IMPORT_PATH' already exists in target. Skipping."
      continue
    fi
  fi

  log "Importing tree of '$BRANCH' into prefix '$IMPORT_PATH'..."
  if [ "$DRY_RUN" = "true" ]; then
    echo "DRYRUN: git read-tree --prefix=$IMPORT_PATH/ -u $BR_REF"
    echo "DRYRUN: git add -A $IMPORT_PATH"
    echo "DRYRUN: git commit -m \"Import branch '$BRANCH' into '$IMPORT_PATH' (import-only)\""
    continue
  fi

  # If forcing update and path exists, remove old path first
  if [ "$FORCE_UPDATE" = "true" ] && git rev-parse --verify --quiet "HEAD:$IMPORT_PATH" >/dev/null 2>&1; then
    git rm -r --cached --ignore-unmatch "$IMPORT_PATH" || true
    rm -rf "$IMPORT_PATH" || true
  fi

  # Stage the branch tree under the prefix
  git read-tree --prefix="$IMPORT_PATH/" -u "$BR_REF"

  # Add and commit the imported files
  git add -A "$IMPORT_PATH"
  git commit -m "Import branch '$BRANCH' into '$IMPORT_PATH' (import-only)"

  log "✅ Imported '$BRANCH' into '$IMPORT_PATH'."
done

log "All done. Target branch: '$TARGET_BRANCH'."
log "Backup branch created: '$BACKUP' (you can reset if needed)."

cat <<EOF
Notes:
- Dry run: set DRY_RUN=true environment variable to only print actions.
  Example: DRY_RUN=true ./gitmerger-import-all.sh
- Force update: set FORCE_UPDATE=true to replace an existing import path.
  Example: FORCE_UPDATE=true ./gitmerger-import-all.sh
- This script does NOT push any changes. After reviewing, push manually:
  git push origin $TARGET_BRANCH
  git push origin $BACKUP
EOF
