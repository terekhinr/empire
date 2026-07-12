/** Рендер блока YouTube-ссылок на лендинге (без мультиков). */
(function () {
  function esc(s) {
    const d = document.createElement("div");
    d.textContent = s || "";
    return d.innerHTML;
  }

  function renderLinks(yt) {
    if (!yt || !yt.length) return "";
    return yt
      .map(function (v) {
        const lang = v.lang === "ru" ? "RU" : "EN";
        const note = v.note ? " · " + esc(v.note) : "";
        return (
          '<a class="ref-yt-link" href="' +
          esc(v.url) +
          '" target="_blank" rel="noopener noreferrer">' +
          esc(v.title) +
          ' <span class="ref-yt-meta">(' +
          esc(v.channel) +
          " · " +
          lang +
          ")" +
          note +
          "</span></a>"
        );
      })
      .join("");
  }

  function renderTrack(title, items) {
    if (!items.length) return "";
    const rows = items
      .map(function (ref) {
        return (
          '<details class="ref-row"><summary><span class="ref-id">' +
          esc(ref.ids[0]) +
          '</span> ' +
          esc(ref.name) +
          "</summary><div class=\"ref-links\">" +
          renderLinks(ref.youtube) +
          "</div></details>"
        );
      })
      .join("");
    return '<div class="ref-track"><h3 class="ref-track-title">' + esc(title) + "</h3>" + rows + "</div>";
  }

  function init() {
    const root = document.getElementById("refs-grid");
    if (!root) return;
    fetch("data/exercise_refs.json")
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        const s = [];
        const k = [];
        for (const key in data) {
          if (key.charAt(0) === "_") continue;
          const ref = data[key];
          ref.ids = ref.ids || [];
          if (ref.track === "S") s.push(ref);
          else k.push(ref);
        }
        s.sort(function (a, b) {
          return (a.ids[0] || "").localeCompare(b.ids[0] || "");
        });
        k.sort(function (a, b) {
          return (a.ids[0] || "").localeCompare(b.ids[0] || "");
        });
        root.innerHTML = renderTrack("Трек S · McGill", s) + renderTrack("Трек K · Гиря", k);
      })
      .catch(function () {
        root.innerHTML = "<p class=\"ref-fallback\">Список ссылок временно недоступен.</p>";
      });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
