#!/bin/bash
exec /root/projects/empire/venv/bin/streamlit run /root/projects/empire/dashboard.py \
  --server.port=8501 \
  --server.address=127.0.0.1 \
  --server.headless=true \
  --browser.gatherUsageStats=false
