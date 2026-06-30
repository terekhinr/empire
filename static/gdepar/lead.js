/**
 * Gdepar B2B leads: «Показать телефон» → POST /api/banya/lead
 */
(function () {
  "use strict";

  function sessionId() {
    try {
      var k = "gdepar_lead_sid";
      var v = sessionStorage.getItem(k);
      if (!v) {
        v = "s_" + Math.random().toString(36).slice(2) + Date.now().toString(36);
        sessionStorage.setItem(k, v);
      }
      return v;
    } catch (e) {
      return "";
    }
  }

  function metrikaReach(goal, params) {
    if (typeof window.gdeparMetrikaReach === "function") {
      window.gdeparMetrikaReach(goal, params || {});
    }
  }

  function postLead(spotId, leadType, source) {
    return fetch("/api/banya/lead", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify({
        spot_id: spotId,
        lead_type: leadType,
        source: source || "site",
        session_id: sessionId(),
      }),
    }).then(function (r) {
      if (!r.ok) throw new Error("lead_failed");
      return r.json();
    });
  }

  function onShowPhoneClick(ev) {
    var btn = ev.target.closest(".gdepar-show-phone");
    if (!btn || btn.disabled) return;
    var spotId = parseInt(btn.getAttribute("data-spot-id"), 10);
    if (!spotId) return;
    btn.disabled = true;
    btn.textContent = "Загрузка…";
    postLead(spotId, "phone_reveal", btn.getAttribute("data-lead-source") || "site")
      .then(function (data) {
        var wrap = btn.closest(".gdepar-phone-lead-wrap");
        var out = wrap && wrap.querySelector(".gdepar-phone-revealed");
        if (data.phone_blocked) {
          var msg = data.message || "Нужен пакет звонков";
          var link = data.pay_url
            ? ' <a href="' + String(data.pay_url).replace(/"/g, "&quot;") + '">Подробнее</a>'
            : "";
          if (out) {
            out.innerHTML = "<span class=\"gdepar-phone-blocked\">" + msg + link + "</span>";
            out.hidden = false;
          }
          btn.remove();
          metrikaReach("gdepar_phone_blocked", { spot_id: spotId });
          return;
        }
        if (data.phone && out) {
          var digits = String(data.phone).replace(/\D/g, "");
          out.innerHTML =
            '<a href="tel:' +
            digits +
            '" data-gdepar-spot-external="phone" data-gdepar-spot-id="' +
            spotId +
            '">' +
            String(data.phone).replace(/</g, "&lt;") +
            "</a>";
          out.hidden = false;
          btn.remove();
          metrikaReach("gdepar_phone_click", { spot_id: spotId });
        } else {
          btn.textContent = "Телефон не указан";
        }
      })
      .catch(function () {
        btn.disabled = false;
        btn.textContent = "Показать телефон";
      });
  }

  document.addEventListener("click", onShowPhoneClick);
})();
