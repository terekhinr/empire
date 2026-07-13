/** DOM render helpers */
(function (global) {
  function el(tag, cls, html) {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (html != null) n.innerHTML = html;
    return n;
  }

  function activeTrack() {
    return global.SnegiriStore.activeTrackMode();
  }

  function activeDay() {
    const s = global.SnegiriStore.get();
    return activeTrack() === "K" ? s.kDay : s.currentDay;
  }

  function currentDayPlan() {
    const track = activeTrack();
    const day = activeDay();
    const phase = global.SnegiriStore.unlockedPhase(track);
    return global.SnegiriProgram.buildDay(day, track, phase);
  }

  function renderHome(root) {
    const s = global.SnegiriStore.get();
    const track = activeTrack();
    const plan = currentDayPlan();
    global.SnegiriStore.checkUnlockK();
    global.SnegiriStore.checkPhaseUnlock(track);
    const avg = global.SnegiriStore.avgScore();
    const phaseHint = global.SnegiriStore.phaseUnlockHint(track);
    const done = plan.exercises.filter(function (ex) {
      return global.SnegiriStore.isExerciseDone(plan.day, ex.exerciseId, track);
    }).length;
    const pct = plan.exercises.length ? Math.round((done / plan.exercises.length) * 100) : 0;

    let kBlock = "";
    if (!s.trackKUnlocked) {
      kBlock =
        '<div class="card track-lock"><div class="card-tag">Трек K</div>' +
        '<div class="card-title">Гиря · 18 шагов · ~27 нед</div>' +
        '<div class="card-desc">Откроется после 3 нед McGill или при самооценке спины. Дальше: hinge → свинг → заброс → турлиш → complex.</div></div>';
    } else if (track === "S" && s.profile.goal !== "spine") {
      kBlock =
        '<div class="card"><div class="card-tag">Трек K</div>' +
        '<div class="card-title">Разблокирован</div>' +
        '<button type="button" class="btn btn-ghost btn-sm" data-action="switch-k">Перейти к гирям</button></div>';
    }

    const rows = plan.exercises
      .map(function (ex) {
        const ok = global.SnegiriStore.isExerciseDone(plan.day, ex.exerciseId, track);
        return (
          '<div class="exercise-row" data-action="workout" data-exercise-id="' +
          ex.exerciseId +
          '">' +
          '<div class="exercise-icon">' +
          ex.exerciseId +
          "</div>" +
          '<div class="exercise-info"><div class="exercise-name">' +
          ex.name +
          '</div><div class="exercise-meta">' +
          ex.meta +
          (ex.cv ? " · + разбор" : "") +
          "</div></div>" +
          '<span class="badge' +
          (ok ? " badge-ok" : "") +
          '">' +
          (ok ? "✓" : "→") +
          "</span></div>"
        );
      })
      .join("");

    let phaseBlock = "";
    if (plan.waitingUnlock) {
      phaseBlock =
        '<div class="card track-lock"><div class="card-tag">Фаза ' +
        (plan.phase + 1) +
        '</div><div class="card-desc">Следующая фаза закрыта. Дожмите текущую по CV.</div></div>';
    } else if (phaseHint && !phaseHint.ready) {
      phaseBlock =
        '<div class="card"><div class="card-tag">Разблокировка</div>' +
        '<div class="card-desc">До фазы ' +
        (plan.phase + 1) +
        ": " +
        phaseHint.sessions +
        "/" +
        phaseHint.requiredSessions +
        " разборов ≥7 · босс " +
        phaseHint.bossName +
        " " +
        phaseHint.bossSessions +
        "/" +
        phaseHint.requiredBoss +
        "</div></div>";
    }

    root.innerHTML =
      '<p class="card-tag">Трек ' +
      track +
      " · " +
      (track === "S" ? "Корпус" : "Гиря") +
      '</p>' +
      "<h1>" +
      plan.title +
      "</h1>" +
      '<div class="progress-bar"><div class="progress-fill" style="width:' +
      pct +
      '%"></div></div>' +
      '<p class="sub">' +
      plan.weekLabel +
      " · " +
      done +
      "/" +
      plan.exercises.length +
      " упражнений</p>" +
      '<div class="stat-grid">' +
      '<div class="stat-box"><div class="stat-val">' +
      (avg != null ? avg : "—") +
      '</div><div class="stat-key">Средняя техника</div></div>' +
      '<div class="stat-box"><div class="stat-val">' +
      s.analyses.length +
      '</div><div class="stat-key">Разборов ИИ</div></div></div>' +
      "<h2>Сегодня</h2>" +
      rows +
      phaseBlock +
      kBlock;
  }

  function comicBlockHtml(slug) {
    const refs = global.SnegiriExerciseRefs;
    if (!refs) return "";
    const ref = refs.bySlug(slug);
    if (!ref || !ref.comic) return "";
    const pk = refs.performerKey();
    const label = pk === "f" ? "женщина" : "мужчина";
    const hasPlayer = global.SnegiriComicPhases && global.SnegiriComicPhases.bySlug(slug);
    if (hasPlayer) {
      return (
        '<div class="card comic-etalon" data-comic-slug="' +
        slug +
        '">' +
        '<div class="card-tag">Эталон · ' +
        label +
        "</div>" +
        '<div class="comic-player-mount" data-comic-mount="' +
        slug +
        '"></div></div>'
      );
    }
    const src = refs.comicSrc(ref);
    return (
      '<div class="card comic-etalon" data-comic-slug="' +
      slug +
      '">' +
      '<div class="card-tag">Эталон · мультик · ' +
      label +
      "</div>" +
      '<picture class="comic-frame">' +
      '<img src="' +
      src +
      '" alt="Эталон выполнения" loading="lazy" decoding="async" ' +
      'onerror="this.closest(\'.comic-etalon\').classList.add(\'comic-etalon--pending\')">' +
      "</picture>" +
      '<p class="card-desc comic-pending">Мультик генерируется. Пока ориентируйтесь на подсказку и камеру.</p>' +
      '<p class="card-desc comic-caption">Панелей: ' +
      (ref.comic.panels || 4) +
      " · стиль Снегири · CV-линии</p></div>"
    );
  }

  function mountComicPlayers(root) {
    if (!root || !global.SnegiriComicPlayer) return;
    root.querySelectorAll("[data-comic-mount]").forEach(function (el) {
      global.SnegiriComicPlayer.mount(el, el.dataset.comicMount);
    });
  }

  function renderWorkout(root, exerciseId) {
    const ex = global.SnegiriProgram.getExercise(exerciseId);
    const plan = currentDayPlan();
    const item = plan.exercises.find(function (e) {
      return e.exerciseId === exerciseId;
    });
    if (!ex || !item) {
      root.innerHTML = "<p>Упражнение не найдено.</p>";
      return;
    }
    root.innerHTML =
      '<p class="card-tag">' +
      (ex.track === "S" ? "McGill" : "Гиря") +
      " · " +
      ex.id +
      "</p>" +
      "<h1>" +
      ex.name +
      "</h1>" +
      '<p class="sub">' +
      item.meta +
      "</p>" +
      comicBlockHtml(ex.slug) +
      '<div class="card"><p class="card-desc instr">' +
      ex.hint +
      "<br><br>① Поставьте телефон на штатив.<br>② Выполните подход.<br>③ Отправьте видео — разбор ~30 сек.</p></div>" +
      (item.cv
        ? '<button type="button" class="btn" data-action="record">Снять подход</button>'
        : "") +
      '<button type="button" class="btn btn-ghost" data-action="mark-done">Отметить без видео</button>' +
      '<button type="button" class="btn btn-ghost" data-action="home">Назад</button>';
    root.dataset.exerciseId = exerciseId;
    mountComicPlayers(root);
  }

  function renderResult(root, result, exerciseId) {
    const ex = global.SnegiriProgram.getExercise(exerciseId);
    const issues = (result.issues || []).map(function (i) {
      const t = typeof i === "string" ? i : i.text;
      return '<div class="feedback-item"><strong style="color:var(--err)">' + t + "</strong></div>";
    });
    const pos = (result.positives || []).map(function (i) {
      const t = typeof i === "string" ? i : i.text;
      return '<div class="feedback-item ok"><strong>' + t + "</strong></div>";
    });
    root.innerHTML =
      '<div class="score-ring"><span class="score-num">' +
      Math.round(result.score) +
      '</span><span class="score-label">из ' +
      (result.max || 10) +
      "</span></div>" +
      "<h2 style=\"text-align:center;margin-bottom:16px\">" +
      (ex ? ex.name : result.exercise) +
      "</h2>" +
      issues.join("") +
      pos.join("") +
      '<div class="card result-frame-card"><div class="card-tag">Разбор · ' +
      (result.engine || "ИИ") +
      '</div><picture class="result-frame"><source srcset="assets/app-result.webp?v=9" type="image/webp">' +
      '<img src="assets/app-result.png?v=9" alt="Кадр разбора"></picture></div>' +
      '<button type="button" class="btn" data-action="home">На экран дня</button>';
  }

  function renderProgress(root) {
    const s = global.SnegiriStore.get();
    const avg = global.SnegiriStore.avgScore();
    const m = s.metrics[0] || {};
    const bars = s.analyses
      .slice(0, 12)
      .reverse()
      .map(function (a) {
        const h = Math.max(15, (a.score / 10) * 100);
        return '<div class="chart-bar" style="height:' + h + '%" title="' + a.score + '"></div>';
      })
      .join("");
    root.innerHTML =
      "<h1>Динамика</h1>" +
      '<form class="metric-form" data-action="metric-form">' +
      '<div class="form-row"><label>Вес, кг<input name="weight" type="number" step="0.1" value="' +
      (s.profile.weightKg || "") +
      '"></label></div>' +
      '<div class="form-row"><label>Талия, см<input name="waist" type="number" step="0.1" value="' +
      (s.profile.waistCm || "") +
      '"></label></div>' +
      '<button type="submit" class="btn btn-ghost btn-sm">Сохранить</button></form>' +
      '<div class="stat-grid">' +
      '<div class="stat-box"><div class="stat-val">' +
      (m.weightKg || s.profile.weightKg || "—") +
      '</div><div class="stat-key">кг</div></div>' +
      '<div class="stat-box"><div class="stat-val">' +
      (m.waistCm || s.profile.waistCm || "—") +
      '</div><div class="stat-key">см талия</div></div>' +
      '<div class="stat-box"><div class="stat-val">' +
      (avg != null ? avg : "—") +
      '</div><div class="stat-key">техника</div></div></div>' +
      '<div class="card"><div class="card-tag">Последние разборы</div>' +
      '<div class="chart-bars">' +
      (bars || '<span class="sub">Пока нет данных</span>') +
      "</div></div>" +
      (s.trackKUnlocked
        ? ""
        : '<div class="card track-lock"><div class="card-title">Трек K</div><div class="card-desc">Нужно 12 разборов ≥7 или день 21</div></div>');
  }

  function renderSubscribe(root) {
    const s = global.SnegiriStore.get();
    let status =
      s.subscription === "trial"
        ? "Пробный период активен (7 дней)"
        : s.subscription === "active"
          ? "Подписка активна"
          : "1 бесплатный разбор · далее подписка";
    root.innerHTML =
      "<h1>Снегири</h1>" +
      '<p class="sub">' +
      status +
      "</p>" +
      '<div class="card featured-plan"><div class="card-tag">Выгодно</div>' +
      '<div class="pricing-row"><span>1 год</span><strong>3 990 ₽</strong></div>' +
      '<p class="card-desc">332 ₽/мес · полный доступ</p>' +
      '<button type="button" class="btn" data-action="trial">Начать 7 дней бесплатно</button></div>' +
      '<div class="card"><div class="pricing-row"><span>3 месяца</span><strong>1 490 ₽</strong></div>' +
      '<div class="pricing-row"><span>1 месяц</span><strong>590 ₽</strong></div>' +
      '<p class="card-desc pay-note">Оплата ЮKassa — подключим на домене. Пробный период доступен сейчас.</p></div>';
  }

  function renderSettings(root) {
    const p = global.SnegiriStore.get().profile;
    const perf = p.performer === "f" ? "f" : "m";
    root.innerHTML =
      "<h1>Настройки</h1>" +
      '<div class="card"><div class="card-tag">Эталон в мультиках</div>' +
      '<label class="form-row">Модель выполнения' +
      '<select name="performer" data-action="performer-select">' +
      '<option value="m"' +
      (perf === "m" ? " selected" : "") +
      ">Мужчина (M)</option>" +
      '<option value="f"' +
      (perf === "f" ? " selected" : "") +
      ">Женщина (F)</option>" +
      "</select></label>" +
      '<p class="card-desc">Влияет на картинку «Эталон · мультик» в упражнениях.</p></div>' +
      '<div class="card"><div class="card-tag">Профиль</div>' +
      "<p class=\"card-desc\">Цель: " +
      (p.goal || "—") +
      "<br>Гиря: " +
      (p.kettleKg || "—") +
      " кг<br>Опыт: " +
      (p.experience || "—") +
      "</p></div>" +
      '<a href="comics.html" class="btn btn-ghost">Галерея мультиков</a>' +
      '<button type="button" class="btn btn-ghost" data-action="edit-profile">Изменить профиль</button>' +
      '<button type="button" class="btn btn-err btn-ghost" data-action="reset">Сбросить прогресс</button>' +
      '<p class="disclaimer">Видео хранятся на сервере для разбора. Удаление по запросу на support@snegirinegiri.ru</p>";
  }

  global.SnegiriUi = {
    activeTrack,
    activeDay,
    currentDayPlan,
    renderHome,
    renderWorkout,
    renderResult,
    renderProgress,
    renderSubscribe,
    renderSettings,
    mountComicPlayers,
  };
})(window);
