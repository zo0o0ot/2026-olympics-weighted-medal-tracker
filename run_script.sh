#!/bin/bash
export GOOGLE_CREDENTIALS=$(gh secret view GOOGLE_CREDENTIALS -R zo0o0ot/2026-olympics-weighted-medal-tracker)
python3 graph_results.py
