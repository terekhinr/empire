# gdepar via neverretire (188.114) when gdepar zone anycast (104.21) is unreachable
location = /gdepar { return 301 /gdepar/; }
location /gdepar/ {
    proxy_pass http://127.0.0.1:8001/;
    proxy_http_version 1.1;
    proxy_set_header Host gdepar.ru;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Accept-Encoding "";
    proxy_read_timeout 90s;
    sub_filter_types text/html;
    sub_filter_once off;
    sub_filter 'href="/static/' 'href="/static/';
    sub_filter 'src="/static/' 'src="/static/';
    sub_filter 'href="/api/' 'href="/api/';
    sub_filter 'href="/' 'href="/gdepar/';
    sub_filter 'action="/' 'action="/gdepar/';
}
location /api/banya/ {
    proxy_pass http://127.0.0.1:8001;
    proxy_set_header Host gdepar.ru;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_read_timeout 90s;
}
location /api/gdepar/ {
    proxy_pass http://127.0.0.1:8001;
    proxy_set_header Host gdepar.ru;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_read_timeout 90s;
}
