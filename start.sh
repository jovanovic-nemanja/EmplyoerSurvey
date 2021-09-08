#!/usr/bin/env bash

direnv allow
source .envrc
"$HIYER_PYTHON_PATH" "$HIYER_MAIN_PATH"
