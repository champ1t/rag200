#!/bin/bash
# Restore Production Freeze State
# Returns codebase to last known frozen state

set -e

echo "🔄 Restoring Production Freeze State..."
echo ""

# Find latest freeze tag
FREEZE_TAG=$(git tag -l "v1.0-production-freeze-*" | sort -V | tail -1)

if [ -z "$FREEZE_TAG" ]; then
    echo "❌ No freeze tag found!"
    echo "Available tags:"
    git tag -l
    exit 1
fi

echo "Found freeze tag: $FREEZE_TAG"
echo ""

# Confirm action
echo "⚠️  This will reset your working directory to frozen state"
echo "Current branch: $(git branch --show-current)"
echo "Current commit: $(git rev-parse --short HEAD)"
echo ""
read -p "Continue? (y/N): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
fi

# Restore
echo ""
echo "Checking out $FREEZE_TAG..."
git checkout "$FREEZE_TAG"

echo ""
echo "✅ Restored to frozen state!"
echo ""
echo "Verifying state..."
python3 verify_production_suite.py

echo ""
echo "To return to main branch later:"
echo "  git checkout main"
echo ""
