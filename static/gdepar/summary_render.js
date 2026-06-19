/**
 * Рендер блока «Дай саммари» (API reviews-block, include_summary=1).
 */
(function (global) {
    function esc(t) {
        if (!t) return '';
        var d = document.createElement('div');
        d.textContent = String(t);
        return d.innerHTML;
    }

    function metaHtml(lastAt, variant) {
        if (!lastAt) return '';
        try {
            var d = new Date(lastAt);
            if (isNaN(d.getTime())) return '';
            var cls = variant === 'popup' ? 'banya-popup-reviews-asof' : 'gdepar-spot-summary-asof';
            return '<p class="' + cls + '">По данным сайта новых одобренных отзывов после <strong>' +
                d.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric' }) +
                '</strong> не было — ориентируйтесь на эту дату; перед визитом перепроверьте часы по телефону бани или на картах.</p>';
        } catch (e) {
            return '';
        }
    }

    function attributionHtml(yandexUrl) {
        var yu = (yandexUrl || '').trim();
        if (yu) {
            return '<p class="gdepar-spot-reviews-source">Тексты отзывов — мнение авторов на площадках. Оригинал: <a href="' +
                esc(yu) + '" target="_blank" rel="noopener">Яндекс.Карты</a>. «Где Пар» публикует отзывы после модерации, смысл авторов не искажается.</p>';
        }
        return '<p class="gdepar-spot-reviews-source muted">Тексты отзывов собираются с внешних площадок; при наличии ссылок на карты выше можно открыть карточку организации там.</p>';
    }

    function renderFromParts(data) {
        var intro = (data && data.summary) ? String(data.summary) : '';
        if (!intro) return '';
        var muted = 'gdepar-spot-summary-text';
        return '<p class="' + muted + '">' + esc(intro).replace(/\n/g, '<br>') + '</p>';
    }

    function renderSummaryBody(data) {
        if (data && typeof data.summary_html === 'string' && data.summary_html.trim()) {
            return data.summary_html.trim();
        }
        return renderFromParts(data);
    }

    global.gdeparRenderReviewsSummary = function (data, options) {
        options = options || {};
        var html = '';
        var body = renderSummaryBody(data);
        if (body) {
            html += body;
        } else {
            html += '<p class="muted">Сводки нет — нечего обобщать по одобренным отзывам.</p>';
        }
        if (data && typeof data.transparency_note === 'string' && data.transparency_note) {
            html += '<p class="gdepar-transparency-note">' + esc(data.transparency_note) + '</p>';
        }
        if (data && data.last_review_at) {
            html += metaHtml(data.last_review_at, options.variant);
        }
        if (options.includeAttribution) {
            html += attributionHtml(options.yandexUrl);
        }
        return html;
    };
})(typeof window !== 'undefined' ? window : this);
