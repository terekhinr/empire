# /hub/ на neverretire.ru → Око Саурона на отдельном порту (не путать с сайтом).

location = /hub {
    return 302 http://193.233.232.48:8503/;
}

location /hub/ {
    return 302 http://193.233.232.48:8503/;
}
