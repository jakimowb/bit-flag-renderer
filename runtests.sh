#!/bin/bash
export QT_QPA_PLATFORM=offscreen
export CI=True
rm -Rf test-outputs
rm -Rf test-reports
export PYTHONPATH="$(pwd);$(pwd)/tests/qgispluginsupport$PYTHONPATH"
echo $PYTHONPATH

# export PYTHONPATH="$(pwd)":tests/qgispluginsupport
pytest
#coverage-badge -o coverage.svg