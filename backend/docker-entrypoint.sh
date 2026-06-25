#!/bin/sh
set -e
PORT="$(python3 -c "import sys; sys.path.insert(0, '/app/src'); from infrastructure.application_properties import get_backend_port; print(get_backend_port())")"
exec uvicorn main:app --host 0.0.0.0 --port "${PORT}"
