#!/usr/bin/bash
# Launch VSCode directly in devcontainer without vscode prompt

set -e

SSD_ROOT="$(cd "$(dirname "$0")" && pwd)"

# Get the folder to open
FOLDER="${1:-.}"
FOLDER=$(cd "$FOLDER" && pwd)

echo "🚀 Opening $FOLDER in devcontainer..."

# Open in devcontainer using the Remote-Containers extension
code --folder-uri "vscode-remote://dev-container+$(printf "%s" "$FOLDER" | xxd -p | tr -d '\n')/workspaces/$(basename "$FOLDER")"