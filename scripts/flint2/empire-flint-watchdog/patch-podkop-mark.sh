#!/bin/sh
# Вставить default_mark ВНУТРЬ sing_box_save_config.
P=/usr/bin/podkop
[ -f "$P" ] || exit 1

sed -i '/EMPIRE default_mark/d' "$P"
sed -i '/rm "$temp_file_path"/a\
    jq '\''.route.default_mark = 2097152'\'' "$sing_box_config_path" > /tmp/sb-empire-mark.json 2>/dev/null \&\& mv /tmp/sb-empire-mark.json "$sing_box_config_path" # EMPIRE default_mark
' "$P"
echo "fixed $P"
