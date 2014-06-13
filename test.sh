#!/bin/bash
PYTHONPATH=.:$PYTHONPATH py.test ./tests -s --tb=short --showlocals "$@"
