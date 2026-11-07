#!/usr/bin/env bash
# Symlink each skill in skills/ into a tool's skill folder, so edits made from
# any session land in this repo.
#
#   ./install.sh <tool> [--force] [--uninstall]
#
#   <tool>        claude, codex, antigravity, or all (every installed tool)
#   --force       replace copied folders and foreign links in the way
#   --uninstall   remove links that point into this repo
set -euo pipefail

usage() { sed -n '2,10s/^# \{0,1\}//p' "$0"; }

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
skills="$repo/skills"

# name : config folder that marks it installed : skills folder
tools=(
  "claude:$HOME/.claude:$HOME/.claude/skills"
  "codex:$HOME/.codex:$HOME/.codex/skills"
  "antigravity:$HOME/.gemini/antigravity:$HOME/.gemini/antigravity/skills"
)

mode=install
force=0
tool=""
for arg in "$@"; do
  case "$arg" in
    --uninstall) mode=uninstall ;;
    --force) force=1 ;;
    -h|--help) usage; exit 0 ;;
    claude|codex|antigravity|all)
      if [[ -n "$tool" ]]; then
        echo "pick one tool, or all" >&2; exit 1
      fi
      tool="$arg" ;;
    *) echo "unknown argument: $arg" >&2; usage >&2; exit 1 ;;
  esac
done
if [[ -z "$tool" ]]; then
  echo "missing tool: claude, codex, antigravity, or all" >&2
  usage >&2
  exit 1
fi

for entry in "${tools[@]}"; do
  IFS=: read -r name root dest <<< "$entry"
  [[ "$tool" == all || "$tool" == "$name" ]] || continue
  # "all" only touches installed tools. A named tool is set up even if missing.
  if [[ "$tool" == all && ! -d "$root" ]]; then
    echo "skip $name (${root/#$HOME/\~} not found)"
    continue
  fi
  echo "$name: ${dest/#$HOME/\~}"

  # Remove links into this repo: all of them on uninstall, dead ones otherwise.
  if [[ -d "$dest" ]]; then
    for link in "$dest"/*; do
      [[ -L "$link" ]] || continue
      target="$(readlink "$link")"
      [[ "$target" == "$skills/"* ]] || continue
      if [[ "$mode" == uninstall || ! -e "$target" ]]; then
        rm "$link"
        echo "  removed $(basename "$link")"
      fi
    done
  fi
  [[ "$mode" == uninstall ]] && continue

  mkdir -p "$dest"
  for src in "$skills"/*/; do
    src="${src%/}"
    skill="$(basename "$src")"
    link="$dest/$skill"
    if [[ -L "$link" && "$(readlink "$link")" == "$src" ]]; then
      continue
    elif [[ -e "$link" || -L "$link" ]]; then
      if (( ! force )); then
        what="folder"; [[ -L "$link" ]] && what="link to $(readlink "$link")"
        echo "  kept $skill: existing $what (use --force to replace)"
        continue
      fi
      rm -rf "$link"
      echo "  replaced $skill"
    else
      echo "  linked $skill"
    fi
    ln -s "$src" "$link"
  done
done
