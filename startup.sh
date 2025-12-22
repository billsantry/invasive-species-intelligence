#!/bin/bash
gunicorn --bind=0.0.0.0 --timeout 600 backend.main:app -k uvicorn.workers.UvicornWorker
