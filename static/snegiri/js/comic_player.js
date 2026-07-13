/** Плеер: статическая лента + анимация фаз с фиксацией. */
(function (global) {
  var timers = {};

  function performerKey() {
    try {
      var p = global.SnegiriStore && global.SnegiriStore.get().profile.performer;
      return p === "f" ? "f" : "m";
    } catch (e) {
      return "m";
    }
  }

  function highlightClass(zone) {
    var map = {
      lumbar: "comic-hl--lumbar",
      hips: "comic-hl--hips",
      core: "comic-hl--core",
      elbows: "comic-hl--elbows",
      grip: "comic-hl--grip",
      error: "comic-hl--error",
    };
    return map[zone] || "comic-hl--core";
  }

  function mount(container, slug) {
    if (!container) return;
    stop(container);

    var phasesApi = global.SnegiriComicPhases;
    var refs = global.SnegiriExerciseRefs;
    if (!phasesApi || !refs) {
      container.innerHTML = "<p class=\"card-desc\">Загрузка…</p>";
      return;
    }

    var spec = phasesApi.bySlug(slug);
    var ref = refs.bySlug(slug);
    var pk = performerKey();
    var strip = spec ? phasesApi.stripSrc(spec, pk) : refs.comicSrc(ref);

    if (!strip && !spec) {
      container.innerHTML = "";
      return;
    }

    var hasAnim = spec && spec.phases && spec.phases.length;
    var uid = "cp-" + slug + "-" + Math.random().toString(36).slice(2, 8);

    var html =
      '<div class="comic-player" id="' +
      uid +
      '" data-slug="' +
      slug +
      '">' +
      '<div class="comic-mode-tabs" role="tablist">' +
      '<button type="button" class="comic-mode-tab active" data-mode="static" role="tab">Статика</button>';

    if (hasAnim) {
      html +=
        '<button type="button" class="comic-mode-tab" data-mode="anim" role="tab">Анимация</button>';
    }

    html +=
      "</div>" +
      '<div class="comic-mode comic-mode--static active" data-mode-panel="static">' +
      '<picture class="comic-frame"><img src="' +
      strip +
      '" alt="Эталон · все фазы" loading="lazy" decoding="async"></picture>' +
      '<p class="card-desc comic-caption">Вся последовательность на одном кадре — для первого знакомства.</p>' +
      "</div>";

    if (hasAnim) {
      html +=
        '<div class="comic-mode comic-mode--anim" data-mode-panel="anim" hidden>' +
        '<div class="comic-anim-stage">' +
        '<img class="comic-anim-img" src="" alt="" decoding="async">' +
        '<div class="comic-anim-badge" aria-live="polite"></div>' +
        "</div>" +
        '<div class="comic-phase-dots"></div>' +
        '<p class="comic-phase-term"></p>' +
        '<p class="comic-phase-source card-desc"></p>' +
        '<div class="comic-phase-cue card"><div class="card-tag">На что смотреть</div><p class="card-desc comic-phase-watch"></p></div>' +
        '<div class="comic-phase-controls">' +
        '<button type="button" class="btn btn-ghost btn-sm comic-btn-play">▶ Смотреть цикл</button>' +
        '<button type="button" class="btn btn-ghost btn-sm comic-btn-step">След. фаза</button>' +
        "</div></div>";
    }

    html += "</div>";
    container.innerHTML = html;

    var root = document.getElementById(uid);
    if (!root) return;

    root.querySelectorAll(".comic-mode-tab").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var mode = btn.dataset.mode;
        root.querySelectorAll(".comic-mode-tab").forEach(function (b) {
          b.classList.toggle("active", b === btn);
        });
        root.querySelectorAll("[data-mode-panel]").forEach(function (panel) {
          var on = panel.dataset.modePanel === mode;
          panel.hidden = !on;
          panel.classList.toggle("active", on);
        });
        if (mode === "anim") {
          goPhase(root, slug, spec, pk, 0, false);
        } else {
          stop(root);
        }
      });
    });

    if (!hasAnim) return;

    var playBtn = root.querySelector(".comic-btn-play");
    var stepBtn = root.querySelector(".comic-btn-step");
    var state = { index: 0, playing: false };

    function setState(i, playing) {
      state.index = i;
      state.playing = playing;
      playBtn.textContent = playing ? "⏸ Пауза" : "▶ Смотреть цикл";
    }

    playBtn.addEventListener("click", function () {
      if (state.playing) {
        stop(root);
        setState(state.index, false);
      } else {
        setState(0, true);
        goPhase(root, slug, spec, pk, 0, true);
      }
    });

    stepBtn.addEventListener("click", function () {
      stop(root);
      var next = (state.index + 1) % spec.phases.length;
      setState(next, false);
      goPhase(root, slug, spec, pk, next, false);
    });

    buildDots(root, spec, function (i) {
      stop(root);
      setState(i, false);
      goPhase(root, slug, spec, pk, i, false);
    });
  }

  function buildDots(root, spec, onPick) {
    var wrap = root.querySelector(".comic-phase-dots");
    if (!wrap) return;
    wrap.innerHTML = spec.phases
      .map(function (ph, i) {
        return (
          '<button type="button" class="comic-phase-dot' +
          (ph.is_error ? " comic-phase-dot--err" : "") +
          '" data-i="' +
          i +
          '" title="' +
          ph.term +
          '"></button>'
        );
      })
      .join("");
    wrap.querySelectorAll(".comic-phase-dot").forEach(function (dot) {
      dot.addEventListener("click", function () {
        onPick(parseInt(dot.dataset.i, 10));
      });
    });
  }

  function goPhase(root, slug, spec, pk, index, autoPlay) {
    var ph = spec.phases[index];
    if (!ph) return;

    var img = root.querySelector(".comic-anim-img");
    var badge = root.querySelector(".comic-anim-badge");
    var termEl = root.querySelector(".comic-phase-term");
    var srcEl = root.querySelector(".comic-phase-source");
    var watchEl = root.querySelector(".comic-phase-watch");
    var frameSrc = global.SnegiriComicPhases.frameSrc(spec, pk, ph.index);

    img.style.opacity = "0";
    img.onload = function () {
      requestAnimationFrame(function () {
        img.style.opacity = "1";
      });
    };
    img.src = frameSrc;
    img.alt = ph.term;

    badge.textContent = ph.term;
    badge.className = "comic-anim-badge " + highlightClass(ph.highlight);

    termEl.innerHTML =
      "<strong>" +
      ph.term +
      "</strong>" +
      (ph.term_alt && ph.term_alt !== "ERROR" ? ' <span class="sub">(' + ph.term_alt + ")</span>" : "");

    srcEl.textContent = ph.source ? "Термин: " + ph.source : "";
    watchEl.innerHTML = "<strong>" + ph.cue + "</strong><br>" + ph.watch;

    root.querySelectorAll(".comic-phase-dot").forEach(function (dot, i) {
      dot.classList.toggle("active", i === index);
    });

    stop(root);
    if (autoPlay) {
      var hold = ph.hold_ms || 2200;
      var fade = ph.fade_ms || 450;
      var next = (index + 1) % spec.phases.length;
      timers[root.id] = setTimeout(function () {
        img.style.transition = "opacity " + fade + "ms ease";
        goPhase(root, slug, spec, pk, next, true);
      }, hold);
    }
  }

  function stop(container) {
    var root =
      container.classList && container.classList.contains("comic-player")
        ? container
        : container.querySelector(".comic-player");
    if (!root) return;
    if (timers[root.id]) {
      clearTimeout(timers[root.id]);
      delete timers[root.id];
    }
  }

  function unmount(container) {
    stop(container);
    if (container) container.innerHTML = "";
  }

  global.SnegiriComicPlayer = {
    mount: mount,
    stop: stop,
    unmount: unmount,
  };
})(typeof window !== "undefined" ? window : globalThis);
