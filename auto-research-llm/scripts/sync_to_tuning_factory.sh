#!/bin/bash
# scripts/sync_to_tuning_factory.sh: Sync experimental changes to TuningFactory submodule branch

# Check if we are inside git repository
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "Error: Not a git repository."
    exit 1
fi

SUBMODULE_DIR="TuningFactory"
BRANCH_NAME="openlm"

if [ ! -d "$SUBMODULE_DIR" ]; then
    echo "Error: Submodule directory $SUBMODULE_DIR does not exist."
    exit 1
fi

echo "Syncing experimental changes in $SUBMODULE_DIR..."
cd "$SUBMODULE_DIR" || exit 1

# Check current branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
echo "Current submodule branch: $CURRENT_BRANCH"

if [ "$CURRENT_BRANCH" != "$BRANCH_NAME" ]; then
    echo "Switching submodule to branch $BRANCH_NAME..."
    git checkout "$BRANCH_NAME" || git checkout -b "$BRANCH_NAME"
fi

# Stage and commit changes in submodule
git add .
if ! git diff-index --quiet HEAD --; then
    git commit -m "Auto-commit: experimental sync at $(date)"
    echo "Pushing changes to origin/$BRANCH_NAME..."
    git push origin "$BRANCH_NAME"
else
    echo "No changes to commit in submodule."
fi

cd ..
echo "Submodule sync completed."
