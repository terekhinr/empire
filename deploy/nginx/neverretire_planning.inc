# Empire Tasks PWA на neverretire.ru/tasks/ → 127.0.0.1:8502
# uvicorn слушает корень; nginx снимает префикс /tasks/.


# Сброс SW (вне /tasks-)
location = /go-reset { return 301 https://neverretire.ru/go-reset/; }
location /go-reset/ {
    alias /var/www/empire-tasks-reset/;
    index index.html;
    default_type text/html;
    add_header Cache-Control "no-cache, no-store, must-revalidate" always;
}

# Старые закладки: exact-match, иначе /tasks-* уходит в catch-all → 404.
location = /tasks-reset { return 302 https://neverretire.ru/go-reset/; }
location = /tasks-reset/ { return 302 https://neverretire.ru/go-reset/; }
location ^~ /go-tasks/app { return 302 https://neverretire.ru/x/; }

# Только HTML-вход /tasks → /x/. Ассеты и API под /tasks/ оставляем —
# иначе 301 на HTML ломает app.js у старых вкладок/SW.
location = /tasks {
    return 301 https://neverretire.ru/x/;
}
location = /tasks/ {
    return 301 https://neverretire.ru/x/;
}
location /tasks/ {
    client_max_body_size 32m;
    rewrite ^/tasks/(.*)$ /$1 break;
    proxy_pass http://127.0.0.1:8502;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_read_timeout 300;
    proxy_send_timeout 300;
    add_header Cache-Control "no-cache, no-store, must-revalidate";
}

# Канон SPA вне scope старого Service Worker (/tasks/).
location = /x {
    return 301 https://neverretire.ru/x/;
}
location /x/ {
    client_max_body_size 32m;
    rewrite ^/x/(.*)$ /$1 break;
    proxy_pass http://127.0.0.1:8502;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_read_timeout 300;
    proxy_send_timeout 300;
    add_header Cache-Control "no-cache, no-store, must-revalidate";
}

# UI зала ВНЕ /tasks/ (вне scope service worker).
location = /gym {
    return 301 /gym/;
}
location /gym/api/ {
    client_max_body_size 32m;
    rewrite ^/gym/api/(.*)$ /api/planning/$1 break;
    proxy_pass http://127.0.0.1:8502;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_connect_timeout 10s;
    proxy_read_timeout 60s;
    proxy_send_timeout 60s;
}
location /gym/ {
    client_max_body_size 4m;
    proxy_pass http://127.0.0.1:8502;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_connect_timeout 10s;
    proxy_read_timeout 60s;
    add_header Cache-Control "no-cache, no-store, must-revalidate";
}

# API зала ВНЕ /tasks/ — иначе старый service worker глушит fetch (таймаут у клиента).
location /gym-api/ {
    client_max_body_size 32m;
    rewrite ^/gym-api/(.*)$ /api/planning/$1 break;
    proxy_pass http://127.0.0.1:8502;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_connect_timeout 10s;
    proxy_read_timeout 60s;
    proxy_send_timeout 60s;
}
