#!/bin/bash
gunicorn ServerPart:app --bind 0.0.0.0:$PORT
