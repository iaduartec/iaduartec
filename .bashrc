export PATH="/home/ubuntu/.nvm/versions/node/v24.20.0/bin:$PATH"
# Keep user-installed command-line tools available in interactive shells.
case ":${PATH:-}:" in
  *":$HOME/.local/bin:"*) ;;
  *) PATH="$HOME/.local/bin${PATH:+:$PATH}" ;;
esac
export PATH

# Keep OpenClaw CLI runs aligned with the managed gateway on this host.
export NODE_COMPILE_CACHE=/var/tmp/openclaw-compile-cache
export OPENCLAW_NO_RESPAWN=1

export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"

# NVM
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
[ -s "$NVM_DIR/bash_completion" ] && . "$NVM_DIR/bash_completion"

# Use the selected nvm default in new interactive shells.
nvm use --silent default >/dev/null

# ASTRA CODEX
alias astra='/home/ubuntu/astra'
alias astra-audit='/home/ubuntu/astra-audit'
alias astra-migrate='/home/ubuntu/astra-migrate'
alias astra-repos='/home/ubuntu/.astra/scan-repos.sh'

# OpenClaw Completion
[ -f '/home/ubuntu/.openclaw/completions/openclaw.bash' ] && source '/home/ubuntu/.openclaw/completions/openclaw.bash'

# usage-manager opencode quota wrapper
opencode() {
  if [ "$1" = "quota" ]; then
    ~/.local/bin/usage-manager "$@"
  else
    command "$HOME/.nvm/versions/node/v24.20.0/bin/opencode" "$@"
  fi
}
