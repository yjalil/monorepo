# Oh-My-Zsh
export ZSH="$HOME/.oh-my-zsh"
ZSH_THEME="robbyrussell"

plugins=(
  git
  gitfast
  last-working-dir
  common-aliases
  zsh-syntax-highlighting
  zsh-history-substring-search
)

ZSH_DISABLE_COMPFIX="true"
source $ZSH/oh-my-zsh.sh

# Unalias problematic
unalias rm 2>/dev/null || true
unalias lt 2>/dev/null || true

# aliases
alias em='printf "%s\n" ✅ ❌ ⚠️ 🔍 📊 🏗️ 🔧 📝 🚀 🧪 ℹ️ 💡 🎯 🔥 ⚡ | fzf --no-sort --layout=reverse | xclip -selection clipboard'

# PATH
export PATH="./bin:./node_modules/.bin:$PATH"
export PATH="$HOME/.local/bin:$PATH"

# Locale
export LC_ALL=C.UTF-8
export LANG=C.UTF-8

# Container greeting
echo "🐳 devcontainer ready"
echo "📁 workspace: /workspace"

# History
HISTFILE=/home/vscode/.zsh_history
HISTSIZE=50000
SAVEHIST=50000
[[ -f "$HISTFILE.LOCK" ]] && rm -f "$HISTFILE.LOCK" # Remove stale lock file on startup
setopt INC_APPEND_HISTORY           # Write immediately, don't wait for exit
setopt HIST_IGNORE_ALL_DUPS
setopt HIST_FIND_NO_DUPS
setopt SHARE_HISTORY
setopt EXTENDED_HISTORY             # Timestamps

# Navigation
setopt AUTO_CD
setopt AUTO_PUSHD
setopt PUSHD_IGNORE_DUPS
setopt PUSHD_SILENT

# Completion
setopt COMPLETE_IN_WORD
setopt ALWAYS_TO_END

