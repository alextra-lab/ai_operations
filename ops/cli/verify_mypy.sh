#!/bin/bash

# Verify mypy and dmypy installation and accessibility
echo "Checking mypy installation..."
which mypy
if [ $? -eq 0 ]; then
    echo "✅ mypy is installed and in PATH"
    mypy --version
else
    echo "❌ mypy is not found in PATH"
fi

echo -e "\nChecking dmypy installation..."
which dmypy
if [ $? -eq 0 ]; then
    echo "✅ dmypy is installed and in PATH"
    dmypy --version
else
    echo "❌ dmypy is not found in PATH"
    echo "Current PATH: $PATH"
fi

echo -e "\nChecking for type checking functionality..."
echo "import os
from typing import Dict, List

def example_function(param: str) -> Dict[str, List[int]]:
    return {'result': [1, 2, 3]}
" > /tmp/test_typing.py

echo "Running mypy on test file..."
mypy /tmp/test_typing.py

echo -e "\nRunning dmypy on test file..."
dmypy check /tmp/test_typing.py || echo "dmypy check failed, but this may be because the daemon is not started"

echo -e "\nStarting dmypy daemon..."
dmypy start

echo -e "\nRunning dmypy check again..."
dmypy check /tmp/test_typing.py

echo -e "\nStopping dmypy daemon..."
dmypy stop
