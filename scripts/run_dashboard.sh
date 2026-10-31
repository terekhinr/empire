#!/bin/bash
# Streamlit «Око Саурона» на 127.0.0.1:8501
# Снаружи: http://193.233.232.48:8503/  (nginx sauron_direct.conf, без Cloudflare)
exec /root/projects/empire/venv/bin/streamlit run /root/projects/empire/dashboard.py \
  --server.port=8501 \
  --server.address=127.0.0.1 \
  --server.headless=true \
  --server.enableCORS=false \
  --server.enableXsrfProtection=false \
  --server.enableWebsocketCompression=false \
  --browser.gatherUsageStats=false
