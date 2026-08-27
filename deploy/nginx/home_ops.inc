# Include inside HTTPS server block (neverretire.ru / hub).
# Auth token is enforced by home_ops_proxy.py (same as Flint UI token).

location = /home-ops {
    return 301 /home-ops/;
}

location /home-ops/ {
    proxy_pass http://127.0.0.1:8767/home-ops/;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_read_timeout 120s;
    # PWA / SW
    add_header Cache-Control "no-store" always;
    add_header Service-Worker-Allowed "/home-ops/";
}
