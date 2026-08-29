# Keep user-installed command-line tools available in login shells.
case ":${PATH:-}:" in
  *":$HOME/.local/bin:"*) ;;
  *) PATH="$HOME/.local/bin${PATH:+:$PATH}" ;;
esac
export PATH

# Keep OpenClaw CLI runs aligned with the managed gateway on this host.
export NODE_COMPILE_CACHE=/var/tmp/openclaw-compile-cache
export OPENCLAW_NO_RESPAWN=1

if [ -f "$HOME/.bashrc" ]; then
    . "$HOME/.bashrc"
fi
