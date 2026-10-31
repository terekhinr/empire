# JustHost temporary site front

Пока из РФ режут Aeza/`138.124.90.47` и глючит CF — публичный вход сайтов на JustHost Vienna `132.243.254.241`.

Приложения остаются на Aeza. На JustHost: nginx SNI-split на `:443` (сайты + VLESS Reality не мешают друг другу).

## DNS (делает владелец)

Во Cloudflare / регистраторе, **серый облачко** (DNS only), A-записи → `132.243.254.241`:

| Имя | Тип | Значение | Proxy |
|-----|-----|----------|-------|
| `gdepar.ru` | A | `132.243.254.241` | DNS only |
| `www` (gdepar) | A | `132.243.254.241` | DNS only |
| `neverretire.ru` | A | `132.243.254.241` | DNS only |
| `www` (neverretire) | A | `132.243.254.241` | DNS only |
| `par` (neverretire) | A | `132.243.254.241` | DNS only |
| `snegirinegiri.ru` | A | `132.243.254.241` | DNS only (опц.) |

CNAME на Cloudflare orange **убрать** для этих имён на время.

После DNS: на JustHost `bash issue-certs.sh`.

Откат: A обратно на `138.124.90.47` / CF orange как было.
