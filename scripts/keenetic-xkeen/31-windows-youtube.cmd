@echo off
REM YouTube + nfqws2 на Windows: включить TCP timestamps (GitHub nfqws2-keenetic #7)
netsh interface tcp set global timestamps=enabled
ipconfig /flushdns
echo OK. Chrome: Ctrl+Shift+N -^> youtube.com
