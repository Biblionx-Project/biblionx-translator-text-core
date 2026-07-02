#!/usr/bin/env bash

LINUX_PACKAGES="build-essential default-jre libhunspell-dev git-lfs"
VENV_DIR=".venv"
VLIBRAS_TRANSLATOR_VERSION="1.3.0rc1"

function install_system_dependencies {
  echo "Installing required system dependencies..."
  (sudo apt --assume-yes --no-install-recommends install $LINUX_PACKAGES) || return 1
  return 0
}

function install_python_packages {
  echo -e "\nInstalling required python packages..."
  if [[ ! -x "${VENV_DIR}/bin/python" ]]; then
    python3 -m venv "${VENV_DIR}" || return 1
  fi

  ("${VENV_DIR}/bin/python" -m pip install --upgrade pip setuptools wheel && \
    "${VENV_DIR}/bin/python" -m pip install Cython -r requirements.txt) || return 1

  ("${VENV_DIR}/bin/python" -m pip install \
    --index-url https://test.pypi.org/simple/ \
    --extra-index-url https://pypi.org/simple \
    "vlibras-translator[neural]==${VLIBRAS_TRANSLATOR_VERSION}") || return 1
  return 0
}

install_system_dependencies &&\
install_python_packages &&\

echo -e "\nSuccessful installation!" || echo -e "\nInstallation failed!"
