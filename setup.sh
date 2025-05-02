#!/usr/bin/env bash

root_dir=$(cd -P -- "$(dirname -- "$0")" && pwd -P)


os=$(uname -s)
os_hardware=$(uname -m)
venv_dir="$root_dir/.venv-$os-$os_hardware"

# make sure we have mysqld
command -v mysqld >/dev/null 2>&1
if [ $? -ne 0 ]
then
    if [ "$os" == "Darwin" ]
    then
        >&2 echo "mysqld missing - installing ..."
        brew update && brew install mysql || exit 1
    else
        >&2 echo "mysqld missing - please install"
        exit 1
    fi
fi


if [ ! -f "$venv_dir/bin/python" ]
then
    echo "configuring venv $venv_dir ..."
    python -m venv "$venv_dir" || { echo >&2 "unable to configure the venv for the project in $venv_dir"; exit 1; }
fi

"$venv_dir/bin/python" -m pip install --upgrade pip
if [ $? -ne 0 ]
then
    >&2 echo "failed to upgrade pip"
    exit 1
fi


"$venv_dir/bin/pip" install -q -r "$root_dir/dev-requirements.txt"

if [ $? -ne 0 ]
then
    >&2 echo "failed to install pip packages"
    exit 1
fi
