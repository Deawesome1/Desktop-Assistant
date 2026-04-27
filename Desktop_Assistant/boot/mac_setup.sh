#!/usr/bin/env bash
set -euo pipefail

# Only run on macOS
if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "mac_setup: not macOS; skipping"
  exit 0
fi

echo "mac_setup: ensuring Xcode command line tools"
if ! xcode-select -p >/dev/null 2>&1; then
  xcode-select --install || true
  echo "mac_setup: please accept Xcode CLI install dialog if shown"
fi

echo "mac_setup: ensuring Homebrew and PortAudio"
if ! command -v brew >/dev/null 2>&1; then
  echo "mac_setup: Homebrew not found; installing"
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi
brew update
brew install portaudio || true

echo "mac_setup: upgrading packaging tools in venv"
# Adjust VENV_PY to point to your venv python (relative to repo root)
VENV_PY="${VENV_PY:-./venv/bin/python}"
if [[ ! -x "$VENV_PY" ]]; then
  # try common path used on mac venvs
  VENV_PY="./venv/bin/python3"
fi
"$VENV_PY" -m pip install --upgrade pip setuptools wheel build

echo "mac_setup: exporting PortAudio flags for pip builds"
PA_PREFIX="$(brew --prefix portaudio)"
export LDFLAGS="-L${PA_PREFIX}/lib"
export CPPFLAGS="-I${PA_PREFIX}/include"
export PKG_CONFIG_PATH="${PA_PREFIX}/lib/pkgconfig:${PKG_CONFIG_PATH:-}"

echo "mac_setup: installing mac-specific Python requirements"
"$VENV_PY" -m pip install -r Desktop_Assistant/requirements/mac.txt

echo "mac_setup: done"
