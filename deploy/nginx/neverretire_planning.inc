# Empire Tasks PWA на neverretire.ru/tasks/ → 127.0.0.1:8502
# uvicorn слушает корень; nginx снимает префикс /tasks/.

location = /tasks {
    return 301 /tasks/;
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
}
