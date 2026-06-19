# Streamlit «Око Саурона» на neverretire.ru/hub/ (basic auth)
# Streamlit слушает 127.0.0.1:8501 без baseUrlPath; nginx снимает префикс /hub/.

location = /hub {
    return 301 /hub/;
}

location /hub/ {
    auth_basic "Empire Dashboard";
    auth_basic_user_file /etc/empire/dashboard.htpasswd;

    rewrite ^/hub/(.*)$ /$1 break;
    proxy_pass http://127.0.0.1:8501;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_read_timeout 86400;
    proxy_buffering off;
}
