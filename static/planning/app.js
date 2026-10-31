// /tasks/, /x/, /go-tasks/app/ (последние вне scope сломанного SW)
const TASKS_MOUNT = (function () {
  try {
    const forced = window.__TASKS_MOUNT__;
    if (forced === "/go-tasks/app" || forced === "/x" || forced === "/tasks") {
      return forced;
    }
    const p = location.pathname || "";
    if (p === "/go-tasks/app" || p.startsWith("/go-tasks/app/")) return "/go-tasks/app";
    if (p === "/x" || p.startsWith("/x/")) return "/x";
  } catch (_) {}
  return "/tasks";
})();
const API_BASE = TASKS_MOUNT + "/api/planning";
const ASSET_BASE = TASKS_MOUNT + "/assets";
const TOKEN_KEY = "empire_planning_token";
const APP_VER = "91";
const FONT_SCALE_KEY = "empire_font_scale";
const FONT_SCALE_MIN = 85;
const FONT_SCALE_MAX = 140;
const FONT_SCALE_DEFAULT = 100;
const OFFLINE_SNAPSHOT_KEY = "empire_offline_snapshot";
const REST_TIMER_PRESETS = [60, 90, 120, 180];
const REPEAT_MAP = {
  daily: { freq: "daily", interval: 1 },
  weekdays: { freq: "weekdays", interval: 1 },
  weekly: { freq: "weekly", interval: 1 },
  biweekly: { freq: "weekly", interval: 2 },
  monthly: { freq: "monthly", interval: 1 },
  yearly: { freq: "yearly", interval: 1 },
};

const state = {
  tasks: [],
  doneTasks: [],
  checklists: [],
  projects: [],
  summary: {},
  measurements: [],
  workouts: [],
  healthSummary: {},
  healthSettings: { remind_measure_sunday: true, remind_measure_hour: 10 },
  exercises: {},
  taskStats: null,
  healthStats: null,
  statsPeriod: "month",
  programDate: todayStr(),
  workoutDiaryDate: todayStr(),
  calendarMonth: todayStr().slice(0, 8) + "01",
  calendarDay: null,
  datePickerMonth: null,
  datePickerSelected: null,
  googleCalendarUrl: "",
  settingsSection: "notifications",
  settingsReturnView: "today",
  programSession: null,
  programLogsForDate: [],
  programSaveTimer: null,
  programSaving: false,
  pendingTaskImage: null,
  pendingTaskImageRemove: false,
  workoutProgramSummary: null,
  programId: localStorage.getItem("empire_workout_program") || "gym_2026",
  workoutPrograms: [],
  insights: null,
  section: "tasks",
  taskView: "today",
  healthView: "measurements",
  currentView: "today",
  hideDoneInLists: localStorage.getItem("empire_hide_done") === "1",
  inboxOnly: false,
  tagFilter: localStorage.getItem("empire_tag_filter") || null,
  projectFilter: null,
  editingId: null,
  creatingTask: false,
  reminded: new Set(JSON.parse(localStorage.getItem("empire_reminded") || "[]")),
  fmPipelineTab: localStorage.getItem("empire_fm_tab") || "empire",
  restTimer: { endAt: null, pausedRemainingMs: null, intervalId: null, presetSec: 120 },
  holdTimer: { endAt: null, pausedRemainingMs: null, intervalId: null, idx: null, setNum: null, label: "" },
};

const TITLES = {
  today: "Сегодня",
  week: "Следующие 7 дней",
  calendar: "Календарь",
  "cal-day": "День",
  matrix: "Матрица Эйзенхауэра",
  "all-tasks": "Все задачи",
  search: "Поиск",
  projects: "Списки",
  lists: "Чеклисты",
  "finance-model": "Пайплайн",
  done: "Вся история",
  "task-stats": "Статистика задач",
  insights: "ИИ-выводы",
  measurements: "Замеры",
  workouts: "Тренировки",
  program: "Программа",
  "health-stats": "Статистика здоровья",
  detail: "Чеклист",
  "project-tasks": "Проект",
  settings: "Настройки",
};

const SETTINGS_SECTIONS = [
  { id: "notifications", icon: "bell", title: "Уведомления" },
  { id: "calendar", icon: "calendar", title: "Подписка на календарь" },
  { id: "appearance", icon: "insights", title: "Внешний вид" },
  { id: "data", icon: "import", title: "Данные" },
  { id: "about", icon: "stats", title: "О приложении" },
];

const TASK_VIEWS = new Set(["today", "week", "calendar", "cal-day", "matrix", "all-tasks", "search", "projects", "lists", "finance-model", "done", "task-stats", "insights", "detail", "project-tasks"]);
const SPLIT_TASK_VIEWS = new Set(["today", "week", "cal-day", "search", "all-tasks", "project-tasks", "done"]);
const HEALTH_VIEWS = new Set(["measurements", "workouts", "program", "health-stats"]);

const PIPELINE_TABS = [
  { view: "today", icon: "today", title: "Сегодня" },
  { view: "week", icon: "week", title: "Неделя" },
  { view: "calendar", icon: "calendar", title: "Календарь" },
  { view: "measurements", icon: "health", title: "Здоровье" },
  { view: "finance-model", icon: "pipeline", title: "Пайплайн" },
];

const HEALTH_TABS = [
  { view: "measurements", icon: "measurements", title: "Замеры" },
  { view: "workouts", icon: "workouts", title: "Тренировки" },
  { view: "program", icon: "program", title: "Программа" },
  { view: "health-stats", icon: "health-stats", title: "Статистика" },
  { view: "health-notify", icon: "bell", title: "Напомин.", action: "open-settings-notify" },
];

function isGymApp() {
  try {
    const q = new URLSearchParams(location.search);
    if (q.get("app") === "gym") {
      localStorage.setItem("empire_app_mode", "gym");
      return true;
    }
    if (q.get("app") === "tasks") {
      localStorage.setItem("empire_app_mode", "tasks");
      return false;
    }
    return localStorage.getItem("empire_app_mode") === "gym";
  } catch {
    return false;
  }
}

function applyGymChrome() {
  const gym = isGymApp();
  document.body.classList.toggle("gym-app", gym);
  document.documentElement.classList.toggle("gym-app", gym);
  if (gym) {
    document.title = "Зал";
    document.querySelectorAll(".sidebar-brand span, .mobile-drawer-brand span, #auth-screen h2").forEach((el) => {
      el.textContent = "Зал";
    });
    const authP = document.querySelector("#auth-screen .auth-card > p");
    if (authP) authP.textContent = "Тренировки, замеры и статистика. Токен: PLANNING_API_TOKEN.";
  }
}

function getTabbarMode(view = state.currentView) {
  if (isGymApp()) return "health";
  return HEALTH_VIEWS.has(view) ? "health" : "pipeline";
}

function isTabActive(tabView, currentView = state.currentView) {
  if (tabView === currentView) return true;
  if (tabView === "calendar" && currentView === "cal-day") return true;
  if (tabView === "measurements" && HEALTH_VIEWS.has(currentView)) return true;
  if (tabView === "today" && ["all-tasks", "project-tasks", "projects", "lists", "detail", "done", "search", "someday", "archive", "assistant"].includes(currentView)) {
    return true;
  }
  if (tabView === "week" && currentView === "week") return true;
  if (tabView === "finance-model" && ["finance-model", "task-stats", "insights"].includes(currentView)) return true;
  return false;
}

const WEEKDAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"];
const PROJECT_COLORS = ["#f97316", "#ec4899", "#3b82f6", "#22c55e", "#a855f7", "#14b8a6", "#eab308"];
const DISCLOSURE_CHEVRON = '<span class="disclosure-chevron" aria-hidden="true"><svg viewBox="0 0 24 24"><polyline points="9 6 15 12 9 18"/></svg></span>';
const MATRIX_META = {
  q1: { title: "Срочно и важно", hint: "Сделать в первую очередь" },
  q2: { title: "Важно, не срочно", hint: "Запланировать" },
  q3: { title: "Срочно, не важно", hint: "Быстро закрыть или делегировать" },
  q4: { title: "Не срочно и не важно", hint: "Потом или убрать" },
};

function projectColor(id) {
  return PROJECT_COLORS[(Number(id) || 0) % PROJECT_COLORS.length];
}

function activeTasksRaw() {
  return state.tasks.filter((t) => t.status !== "done" && t.status !== "cancelled");
}

function activeTasks() {
  return applyTagFilter(activeTasksRaw());
}

function applyTagFilter(items) {
  if (!state.tagFilter) return items;
  const needle = state.tagFilter.toLowerCase();
  return items.filter((t) => (t.tags || []).some((x) => String(x).toLowerCase() === needle));
}

function collectAllTags() {
  const counts = new Map();
  state.tasks.forEach((t) => {
    (t.tags || []).forEach((tag) => {
      const key = String(tag).trim();
      if (!key) return;
      counts.set(key, (counts.get(key) || 0) + 1);
    });
  });
  return [...counts.entries()]
    .map(([tag, count]) => ({ tag, count }))
    .sort((a, b) => b.count - a.count || a.tag.localeCompare(b.tag, "ru"));
}

function tagColor(tag) {
  const palette = ["#3b82f6", "#22c55e", "#f59e0b", "#ec4899", "#8b5cf6", "#14b8a6", "#f97316", "#64748b"];
  let h = 0;
  const s = String(tag || "");
  for (let i = 0; i < s.length; i += 1) h = (h * 31 + s.charCodeAt(i)) >>> 0;
  return palette[h % palette.length];
}

function parseTagsInput(str) {
  return String(str || "")
    .split(",")
    .map((x) => x.trim().replace(/^#/, ""))
    .filter(Boolean);
}

function getSheetTags() {
  return parseTagsInput(document.getElementById("tf-tags")?.value || "");
}

function setSheetTags(tags) {
  const input = document.getElementById("tf-tags");
  if (!input) return;
  const uniq = [];
  tags.forEach((tag) => {
    const t = String(tag).trim();
    if (!t) return;
    if (!uniq.some((x) => x.toLowerCase() === t.toLowerCase())) uniq.push(t);
  });
  input.value = uniq.join(", ");
  renderTagPillsFromInput();
  renderTagSuggestions(document.getElementById("tf-tag-add")?.value || "");
}

function addSheetTag(raw) {
  const tag = String(raw || "").trim().replace(/^#/, "");
  if (!tag) return;
  setSheetTags([...getSheetTags(), tag]);
  const addEl = document.getElementById("tf-tag-add");
  if (addEl) addEl.value = "";
  renderTagSuggestions("");
  persistSheetTagsIfEditing().catch((err) => showToast(err.message));
}

function removeSheetTag(tag) {
  const needle = String(tag || "").toLowerCase();
  setSheetTags(getSheetTags().filter((x) => x.toLowerCase() !== needle));
  persistSheetTagsIfEditing().catch((err) => showToast(err.message));
}

async function persistSheetTagsIfEditing() {
  const id = document.getElementById("tf-id")?.value;
  if (!id) return;
  await api(`/tasks/${id}`, { method: "PUT", body: JSON.stringify({ tags: getSheetTags() }) });
  await loadAll();
  renderTagPillsFromInput();
}

function openTagFilter(tag) {
  const t = String(tag || "").trim().replace(/^#/, "");
  if (!t) return;
  state.tagFilter = t;
  state.inboxOnly = false;
  localStorage.setItem("empire_tag_filter", t);
  closeSheet();
  showView("all-tasks");
  document.getElementById("page-title").textContent = `#${t}`;
}

function clearTagFilter() {
  state.tagFilter = null;
  localStorage.removeItem("empire_tag_filter");
  if (state.currentView === "all-tasks") renderAllTasks();
  else if (state.currentView === "today") renderToday();
  else if (state.currentView === "week") renderWeek();
  else if (state.currentView === "search") renderSearch(document.getElementById("search-input")?.value || "");
  else if (state.currentView === "project-tasks") renderProjectTasks(state.projectFilter);
  renderSidebarNav();
  document.getElementById("page-title").textContent = TITLES[state.currentView] || "Empire";
}

function tagFilterBarHtml() {
  if (!state.tagFilter) return "";
  return `<div class="tag-filter-bar">
    <span>Метка <strong>#${escapeHtml(state.tagFilter)}</strong></span>
    <button type="button" class="btn-link" data-action="clear-tag-filter">Сбросить</button>
  </div>`;
}

function taskNavCounts() {
  const today = todayStr();
  const weekEnd = addDays(7);
  const active = activeTasksRaw();
  const overdue = active.filter((t) => t.due_date && t.due_date < today);
  const todayTasks = active.filter((t) => t.due_date === today);
  const weekTasks = active.filter((t) => t.due_date && t.due_date <= weekEnd);
  const completedToday = state.doneTasks.filter((t) => (t.completed_at || "").slice(0, 10) === today);
  return {
    overdue,
    today: todayTasks,
    week: weekTasks,
    all: active.length,
    completedToday,
    todayNav: overdue.length + todayTasks.length,
    weekNav: weekTasks.length,
  };
}

function formatTaskDateShort(iso) {
  if (!iso) return "";
  const d = new Date(`${iso}T12:00:00`);
  return d.toLocaleDateString("ru-RU", { day: "numeric", month: "short" });
}

function formatTaskMetaDate(t) {
  if (!t?.due_date) return { text: "", overdue: false, today: false };
  const today = todayStr();
  const tomorrow = addDays(1);
  let datePart = formatTaskDateShort(t.due_date);
  if (t.due_date === today) datePart = "Сегодня";
  else if (t.due_date === tomorrow) datePart = "Завтра";
  const timePart = t.due_time ? `, ${String(t.due_time).slice(0, 5)}` : "";
  return {
    text: datePart + timePart,
    overdue: t.due_date < today && t.status !== "done",
    today: t.due_date === today,
  };
}

function formatSheetDueLine(dueDate, dueTime) {
  if (!dueDate) return "";
  const today = todayStr();
  const tomorrow = addDays(1);
  const d = new Date(`${dueDate}T12:00:00`);
  let dateLabel = d.toLocaleDateString("ru-RU", { day: "numeric", month: "short" });
  if (dueDate === today) dateLabel = "Сегодня";
  else if (dueDate === tomorrow) dateLabel = "Завтра";
  if (dueDate < today) {
    let overdueDays = 0;
    let cur = dueDate;
    while (cur < today) {
      cur = addDaysToDateStr(cur, 1);
      overdueDays += 1;
    }
    dateLabel = `${dateLabel}, Просрочено ${overdueDays}`;
  }
  if (dueTime) dateLabel += `, ${String(dueTime).slice(0, 5)}`;
  return dateLabel;
}

function dueDisplayText(dueDate, dueTime) {
  if (!dueDate) return "Без даты — нажмите для выбора";
  return formatSheetDueLine(dueDate, dueTime);
}

function openDatePicker() {
  const due = document.getElementById("tf-due-date")?.value || "";
  state.datePickerSelected = due || null;
  state.datePickerMonth = due ? `${due.slice(0, 7)}-01` : monthStartFromToday();
  document.getElementById("dp-due-time").value = document.getElementById("tf-due-time")?.value || "";
  document.getElementById("dp-remind").value = document.getElementById("tf-remind")?.value || "";
  document.getElementById("dp-repeat").value = document.getElementById("tf-repeat")?.value || "";
  const sheet = document.getElementById("date-picker-sheet");
  if (!sheet) return;
  sheet.classList.remove("hidden");
  sheet.setAttribute("aria-hidden", "false");
  renderDatePickerCalendar();
}

function closeDatePicker() {
  const sheet = document.getElementById("date-picker-sheet");
  sheet.classList.add("hidden");
  sheet.setAttribute("aria-hidden", "true");
}

function renderDatePickerCalendar() {
  state.datePickerMonth = state.datePickerMonth || monthStartFromToday();
  const range = calendarGridRange(state.datePickerMonth);
  const label = document.getElementById("dp-month-label");
  if (label) {
    label.textContent = new Date(`${state.datePickerMonth}T12:00:00`).toLocaleDateString("ru-RU", {
      month: "long",
      year: "numeric",
    });
  }
  const selected = state.datePickerSelected || document.getElementById("tf-due-date")?.value || "";
  const today = todayStr();
  const days = [];
  let cur = range.gridStart;
  while (cur <= range.gridEnd) {
    days.push(cur);
    cur = addDaysToDateStr(cur, 1);
  }
  const grid = document.getElementById("dp-calendar-grid");
  if (!grid) return;
  grid.innerHTML = days
    .map((day) => {
      const outside = !day.startsWith(range.monthKey);
      const isToday = day === today;
      const isSelected = day === selected;
      return `<button type="button" class="dp-day${outside ? " outside" : ""}${isToday ? " today" : ""}${isSelected ? " selected" : ""}" data-action="dp-pick-day" data-date="${day}">${Number(day.slice(8, 10))}</button>`;
    })
    .join("");
}

async function applyScheduleFromPicker({ persist = true } = {}) {
  const dueDate =
    state.datePickerSelected != null
      ? state.datePickerSelected
      : document.getElementById("tf-due-date")?.value || "";
  const dueTime = document.getElementById("dp-due-time")?.value || "";
  const remindOff = document.getElementById("dp-remind")?.value ?? "";
  const repeatKey = document.getElementById("dp-repeat")?.value || "";
  document.getElementById("tf-due-date").value = dueDate;
  document.getElementById("tf-due-time").value = dueTime;
  document.getElementById("tf-remind").value = remindOff;
  document.getElementById("tf-repeat").value = repeatKey;
  syncSheetMetaDisplay();
  if (!persist) return;
  const id = document.getElementById("tf-id")?.value;
  if (!id) return;
  const body = {
    due_date: dueDate || null,
    due_time: dueTime || null,
    clear_due: !dueDate,
    clear_time: !dueTime,
    repeat_rule: repeatKey ? REPEAT_MAP[repeatKey] : null,
    clear_repeat: !repeatKey,
    remind_at: computeRemindAt(dueDate, dueTime, remindOff),
    clear_remind: remindOff === "" || remindOff == null,
  };
  await api(`/tasks/${id}`, { method: "PUT", body: JSON.stringify(body) });
  await loadAll();
  if (state.editingId) {
    const t = [...state.tasks, ...state.doneTasks].find((x) => x.id === state.editingId);
    if (t) await openSheet(t);
  }
  showToast(dueDate ? "Дата обновлена" : "Дата снята");
}

async function confirmDatePicker() {
  await applyScheduleFromPicker({ persist: true });
  closeDatePicker();
}

async function clearDatePickerSelection() {
  state.datePickerSelected = "";
  document.getElementById("tf-due-date").value = "";
  document.getElementById("dp-due-time").value = "";
  document.getElementById("dp-remind").value = "";
  document.getElementById("tf-due-time").value = "";
  document.getElementById("tf-remind").value = "";
  await applyScheduleFromPicker({ persist: true });
  closeDatePicker();
}

function taskMetaIconsHtml(t) {
  const parts = [];
  if (t.remind_at) parts.push('<span class="task-icon task-icon--remind" aria-hidden="true"></span>');
  if (t.repeat_label && t.repeat_label !== "Без повтора") {
    parts.push('<span class="task-icon task-icon--repeat" aria-hidden="true"></span>');
  }
  return parts.join("");
}

function tagPillsHtml(tags, { limit = 3, clickable = true } = {}) {
  const list = (tags || []).filter(Boolean).slice(0, limit);
  if (!list.length) return "";
  return `<div class="tag-pills tag-pills--inline">${list
    .map((tag) => {
      const color = tagColor(tag);
      if (!clickable) {
        return `<span class="tag-pill" style="--tag-color:${color}">#${escapeHtml(tag)}</span>`;
      }
      return `<button type="button" class="tag-pill tag-pill--click" data-action="filter-tag" data-tag="${escapeHtml(tag)}" style="--tag-color:${color}">#${escapeHtml(tag)}</button>`;
    })
    .join("")}</div>`;
}

function renderTagSuggestions(query) {
  const el = document.getElementById("tf-tag-suggestions");
  if (!el) return;
  const q = String(query || "").trim().toLowerCase().replace(/^#/, "");
  const current = new Set(getSheetTags().map((x) => x.toLowerCase()));
  let items = collectAllTags().filter((x) => !current.has(x.tag.toLowerCase()));
  if (q) items = items.filter((x) => x.tag.toLowerCase().includes(q));
  items = items.slice(0, 8);
  if (!items.length) {
    el.classList.add("hidden");
    el.innerHTML = "";
    return;
  }
  el.classList.remove("hidden");
  el.innerHTML = items
    .map(
      (x) => `<button type="button" class="tag-suggestion" data-action="pick-sheet-tag" data-tag="${escapeHtml(x.tag)}">
        <span class="tag-dot" style="background:${tagColor(x.tag)}"></span>${escapeHtml(x.tag)}
        <span class="hint">${x.count}</span>
      </button>`
    )
    .join("");
}

function renderTagPillsFromInput() {
  const el = document.getElementById("tf-tag-pills");
  const input = document.getElementById("tf-tags");
  if (!el || !input) return;
  const tags = parseTagsInput(input.value);
  el.innerHTML = tags.length
    ? tags
        .map(
          (tag) => `<button type="button" class="tag-pill tag-pill--sheet" data-action="remove-sheet-tag" data-tag="${escapeHtml(tag)}" style="--tag-color:${tagColor(tag)}" title="Убрать метку">#${escapeHtml(tag)}<span class="tag-pill-x" aria-hidden="true">×</span></button>`
        )
        .join("")
    : "";
  const addBtn = `<button type="button" class="tag-pill tag-pill--add${tags.length ? "" : " tag-pill--empty"}" data-action="focus-tag-add">${tags.length ? "+" : "+ метка"}</button>`;
  el.innerHTML = (el.innerHTML || "") + addBtn;
}

function syncSheetMetaDisplay() {
  const dueDate = document.getElementById("tf-due-date")?.value || "";
  const dueTime = document.getElementById("tf-due-time")?.value || "";
  const dueEl = document.getElementById("tf-due-display");
  const repeatEl = document.getElementById("tf-repeat-display");
  const projEl = document.getElementById("tf-project-label");
  const priority = Number(document.getElementById("tf-priority")?.value || 0);
  const flagBtn = document.getElementById("tf-priority-flag");
  if (projEl) {
    const pid = document.getElementById("tf-project")?.value;
    const p = state.projects.find((x) => String(x.id) === String(pid));
    projEl.textContent = p?.title || "Входящие";
  }
  if (dueEl) {
    const line = dueDisplayText(dueDate, dueTime);
    dueEl.textContent = line;
    dueEl.className = "tt-due-display tt-due-display--clickable mobile-only";
    if (dueDate) {
      if (dueDate < todayStr()) dueEl.classList.add("overdue");
      else if (dueDate === todayStr()) dueEl.classList.add("today");
      else dueEl.classList.add("future");
    } else {
      dueEl.classList.add("empty");
    }
  }
  const dueText = document.getElementById("tf-due-display-text");
  const dueBtn = document.getElementById("tf-due-picker-btn");
  if (dueText) {
    dueText.textContent = dueDisplayText(dueDate, dueTime);
  }
  if (dueBtn) {
    dueBtn.classList.toggle("overdue", !!(dueDate && dueDate < todayStr()));
    dueBtn.classList.toggle("today", dueDate === todayStr());
    dueBtn.classList.toggle("empty", !dueDate);
  }
  if (repeatEl) {
    const repeatKey = document.getElementById("tf-repeat")?.value || "";
    const labels = {
      daily: "Ежедневно",
      weekdays: "По будням",
      weekly: "Еженедельно",
      biweekly: "Каждые 2 недели",
      monthly: "Ежемесячно",
      yearly: "Ежегодно",
    };
    repeatEl.textContent = labels[repeatKey] || "";
    repeatEl.classList.toggle("hidden", !repeatKey);
  }
  if (flagBtn) {
    flagBtn.classList.toggle("active", priority >= 2);
    flagBtn.classList.toggle("high", priority >= 3);
    flagBtn.title = priority >= 3 ? "Высокий приоритет" : priority >= 2 ? "Средний приоритет" : "Обычный приоритет";
  }
  renderTagPillsFromInput();
  hydrateNavIcons(document.getElementById("task-sheet"));
}

function syncTabbar() {
  renderMobileTabbar();
}

function renderMobileTabbar() {
  const el = document.getElementById("mobile-tabbar");
  if (!el) return;
  const mode = getTabbarMode();
  el.dataset.mode = mode;
  const tabs = mode === "health" ? HEALTH_TABS : PIPELINE_TABS;
  el.innerHTML = tabs
    .map((tab) => {
      const active = tab.action ? false : isTabActive(tab.view);
      if (tab.action) {
        return `<button class="tab tab-icon${active ? " active" : ""}" type="button" title="${escapeHtml(tab.title)}" data-action="${tab.action}"><span class="tab-icon-svg" data-icon="${tab.icon}"></span></button>`;
      }
      return `<button class="tab tab-icon${active ? " active" : ""}" data-view="${tab.view}" type="button" title="${escapeHtml(tab.title)}"><span class="tab-icon-svg" data-icon="${tab.icon}"></span></button>`;
    })
    .join("");
  hydrateNavIcons(el);
}

function drawerNavRow(view, label, count, { action, icon } = {}) {
  const active = view
    ? state.currentView === view || (view === "calendar" && state.currentView === "cal-day")
    : false;
  if (action) {
    return `<button class="drawer-row" type="button" data-action="${action}" data-drawer-close="1">${window.NavIcons ? NavIcons.badge(icon || "settings") : ""}<span class="drawer-row-label">${escapeHtml(label)}</span></button>`;
  }
  const iconKey = NAV_ICON_KEYS[view] || view;
  const countHtml = count != null && count !== "" ? `<span class="drawer-row-count">${count}</span>` : "";
  return `<button class="drawer-row${active ? " active" : ""}" data-view="${view}" type="button" data-drawer-close="1">${window.NavIcons ? NavIcons.badge(iconKey) : ""}<span class="drawer-row-label">${escapeHtml(label)}</span>${countHtml}</button>`;
}

function renderMobileDrawer() {
  const nav = document.getElementById("mobile-drawer-nav");
  if (!nav) return;
  if (isGymApp()) {
    nav.innerHTML = [
      drawerNavRow("program", "Программа", "", { icon: "program" }),
      drawerNavRow("workouts", "Дневник", "", { icon: "workouts" }),
      drawerNavRow("measurements", "Замеры", "", { icon: "measurements" }),
      drawerNavRow("health-stats", "Статистика", "", { icon: "health-stats" }),
      `<div class="drawer-divider" aria-hidden="true"></div>`,
      drawerNavRow(null, "Настройки", "", { action: "open-settings", icon: "settings" }),
    ].join("");
    hydrateNavIcons(nav);
    return;
  }
  const c = taskNavCounts();
  const inboxCount = activeTasksRaw().filter((t) => !t.project_id).length;
  nav.innerHTML = [
    drawerNavRow("today", "Сегодня", c.todayNav || ""),
    drawerNavRow("week", "Следующие 7 дней", c.weekNav || ""),
    drawerNavRow("search", "Поиск", ""),
    drawerNavRow("all-tasks", "Все задачи", c.all || ""),
    `<button class="drawer-row${state.inboxOnly && state.currentView === "all-tasks" ? " active" : ""}" type="button" data-view="all-tasks" data-inbox="1" data-drawer-close="1">${window.NavIcons ? NavIcons.badge("inbox") : ""}<span class="drawer-row-label">Входящие</span><span class="drawer-row-count">${inboxCount || ""}</span></button>`,
    drawerNavRow("done", "История", ""),
    `<div class="drawer-divider" aria-hidden="true"></div>`,
    drawerNavRow("projects", "Списки", state.projects.length || ""),
    drawerNavRow("lists", "Чеклисты", state.checklists.length || ""),
    `<div class="drawer-divider" aria-hidden="true"></div>`,
    drawerNavRow("measurements", "Здоровье", "", { icon: "health" }),
    drawerNavRow(null, "Настройки", "", { action: "open-settings", icon: "settings" }),
  ].join("");
  hydrateNavIcons(nav);
}

function closeMobileDrawer() {
  const drawer = document.getElementById("mobile-drawer");
  if (!drawer) return;
  drawer.classList.add("hidden");
  drawer.setAttribute("aria-hidden", "true");
}

function toggleMobileDrawer() {
  const drawer = document.getElementById("mobile-drawer");
  if (!drawer) return;
  closeOverflowMenu();
  if (drawer.classList.contains("hidden")) {
    renderMobileDrawer();
    drawer.classList.remove("hidden");
    drawer.setAttribute("aria-hidden", "false");
  } else {
    closeMobileDrawer();
  }
}

function closeOverflowMenu() {
  const menu = document.getElementById("view-overflow-menu");
  if (!menu) return;
  menu.classList.add("hidden");
  menu.setAttribute("aria-hidden", "true");
}

function toggleOverflowMenu() {
  const menu = document.getElementById("view-overflow-menu");
  if (!menu) return;
  closeMobileDrawer();
  syncOverflowHideDoneLabel();
  const willHide = !menu.classList.contains("hidden");
  menu.classList.toggle("hidden", willHide);
  menu.setAttribute("aria-hidden", willHide ? "true" : "false");
}

function syncOverflowHideDoneLabel() {
  const el = document.getElementById("overflow-hide-done-label");
  if (el) el.textContent = state.hideDoneInLists ? "Показать выполненные" : "Скрыть выполненные";
}

function quickAddHtml() {
  // FAB «+» уже есть — отдельная строка сверху только засоряет список
  return "";
}

function defaultDueForQuickAdd() {
  if (state.currentView === "cal-day" && state.calendarDay) return state.calendarDay;
  if (state.currentView === "today" || state.currentView === "week") return todayStr();
  if (state.currentView === "project-tasks" || state.currentView === "all-tasks") return todayStr();
  return todayStr();
}

async function quickCaptureCreate(titleRaw) {
  const title = String(titleRaw || "").trim();
  if (!title) return;
  const body = {
    title,
    due_date: defaultDueForQuickAdd(),
    priority: 0,
    project_id: state.currentView === "project-tasks" && state.projectFilter ? state.projectFilter : null,
    tags: [],
  };
  await api("/tasks", { method: "POST", body: JSON.stringify(body) });
  await loadAll();
  showToast("Добавлено");
}

function focusQuickCapture() {
  const input = document.querySelector("#main .quick-capture-input");
  if (input) {
    input.focus();
    input.select?.();
  }
}

function renderTaskList(items, { compact = true } = {}) {
  if (!items.length) return "";
  return `<div class="task-list">${items.map((t) => taskRowHtml(t, { compact })).join("")}</div>`;
}

function renderCollapsibleGroup(title, items, { open = true, cls = "", footer = "" } = {}) {
  if (!items.length && !footer) return "";
  const body = items.length
    ? renderTaskList(items)
    : `<div class="task-group-empty">Пусто</div>`;
  return `<details class="task-group task-card ${cls}"${open ? " open" : ""}>
    <summary class="disclosure-toggle">${DISCLOSURE_CHEVRON}<span class="task-group-title">${escapeHtml(title)}</span><span class="task-group-count">${items.length}</span></summary>
    ${body}
    ${footer ? `<div class="task-group-footer">${footer}</div>` : ""}
  </details>`;
}

function hydrateNavIcons(root = document) {
  if (!window.NavIcons) return;
  const day = new Date().getDate();
  root.querySelectorAll("[data-icon]").forEach((el) => {
    const name = el.dataset.icon;
    if (!name) return;
    el.innerHTML = NavIcons.svg(name, { day });
  });
}

const NAV_ICON_KEYS = {
  today: "today",
  week: "week",
  matrix: "matrix",
  "all-tasks": "inbox",
  search: "search",
  calendar: "calendar",
  lists: "lists",
  "finance-model": "finance",
  insights: "insights",
  "task-stats": "stats",
  done: "history",
  measurements: "measurements",
  workouts: "workouts",
  program: "program",
  "health-stats": "health-stats",
};

function navRowHtml(view, label, count) {
  const active =
    state.currentView === view || (state.currentView === "cal-day" && view === "calendar")
      ? " active"
      : "";
  const iconKey = NAV_ICON_KEYS[view] || view;
  const iconHtml = window.NavIcons ? NavIcons.badge(iconKey) : "";
  const countHtml = count != null && count !== "" ? `<span class="nav-row-count">${count}</span>` : "";
  return `<button class="nav-row${active}" data-view="${view}" type="button">
    ${iconHtml}
    <span class="nav-row-label">${escapeHtml(label)}</span>${countHtml}
  </button>`;
}

function renderSidebarNav() {
  const c = taskNavCounts();
  const inboxCount = activeTasksRaw().filter((t) => !t.project_id).length;
  const main = document.getElementById("sidebar-nav-main");
  if (main && isGymApp()) {
    main.innerHTML = [
      navRowHtml("program", "Программа", ""),
      navRowHtml("workouts", "Дневник", ""),
      navRowHtml("measurements", "Замеры", ""),
      navRowHtml("health-stats", "Статистика", ""),
    ].join("");
  } else if (main) {
    const inboxActive = state.inboxOnly && state.currentView === "all-tasks" ? " active" : "";
    main.innerHTML = [
      navRowHtml("today", "Сегодня", c.todayNav || ""),
      navRowHtml("week", "Следующие 7 дней", c.weekNav || ""),
      `<button class="nav-row${inboxActive}" data-view="all-tasks" data-inbox="1" type="button">
        ${window.NavIcons ? NavIcons.badge("inbox") : ""}
        <span class="nav-row-label">Входящие</span>
        <span class="nav-row-count">${inboxCount || ""}</span>
      </button>`,
      navRowHtml("matrix", "Матрица", ""),
      navRowHtml("all-tasks", "Все задачи", c.all || ""),
      navRowHtml("search", "Поиск", ""),
    ].join("");
  }
  const mobileMain = document.getElementById("more-menu-main");
  if (mobileMain) mobileMain.innerHTML = "";
  const listsCount = document.getElementById("nav-count-lists");
  if (listsCount) listsCount.textContent = String(state.checklists.length || 0);

  const projEl = document.getElementById("sidebar-projects-list");
  if (projEl) {
    if (!state.projects.length) {
      projEl.innerHTML = `<button class="nav-row nav-row-large" data-view="projects" type="button"><span class="nav-row-label">Все списки</span></button>`;
    } else {
      const folders = [];
      const byFolder = new Map();
      state.projects.forEach((p) => {
        const folder = (p.folder_name || "").trim() || "Другие";
        if (!byFolder.has(folder)) byFolder.set(folder, []);
        byFolder.get(folder).push(p);
      });
      const folderOrder = ["ЛИЧНЫЕ ЦЕЛИ", "Архивный список", "Empire", "Другие"];
      folderOrder.forEach((f) => {
        if (byFolder.has(f)) folders.push([f, byFolder.get(f)]);
      });
      byFolder.forEach((items, f) => {
        if (!folderOrder.includes(f)) folders.push([f, items]);
      });

      projEl.innerHTML = folders
        .map(([folder, items]) => {
          const rows = items
            .map((p) => {
              const isEmpire = (p.title || "").startsWith("Empire ·");
              const pct = isEmpire ? projectProgress(p.id).pct : null;
              const count = pct != null ? `${pct}%` : (p.open_tasks || 0);
              const active =
                state.currentView === "project-tasks" && state.projectFilter === p.id ? " active" : "";
              return `<button class="nav-row nav-row-large${active}" data-view="project-tasks" data-project-id="${p.id}" type="button">
                <span class="nav-row-label"><span class="project-dot" style="background:${projectColor(p.id)}"></span> ${escapeHtml(p.title)}</span>
                <span class="nav-row-count">${count}</span>
              </button>`;
            })
            .join("");
          const open = folder === "ЛИЧНЫЕ ЦЕЛИ" || folder === "Архивный список" ? " open" : "";
          return `<details class="nav-folder-wrap"${open}>
            <summary class="nav-folder-summary">${escapeHtml(folder)}</summary>
            <div class="nav-folder-lists">${rows}</div>
          </details>`;
        })
        .join("");
    }
  }

  const tagsEl = document.getElementById("sidebar-tags-list");
  if (tagsEl) {
    const tags = collectAllTags().slice(0, 40);
    if (!tags.length) {
      tagsEl.innerHTML = `<p class="nav-tags-empty hint">Меток пока нет — добавьте в карточке задачи</p>`;
    } else {
      tagsEl.innerHTML = tags
        .map((x) => {
          const active = state.tagFilter && state.tagFilter.toLowerCase() === x.tag.toLowerCase() ? " active" : "";
          const color = tagColor(x.tag);
          return `<button type="button" class="nav-row nav-row-large nav-row-tag${active}" data-action="filter-tag" data-tag="${escapeHtml(x.tag)}">
            <span class="tag-dot" style="background:${color}"></span>
            <span class="nav-row-label">${escapeHtml(x.tag)}</span>
            <span class="nav-row-count">${x.count}</span>
          </button>`;
        })
        .join("");
    }
  }

  document.querySelectorAll(".nav-row[data-view]").forEach((btn) => {
    const match =
      btn.dataset.view === state.currentView ||
      (state.currentView === "cal-day" && btn.dataset.view === "calendar");
    btn.classList.toggle("active", match);
  });
  document.querySelectorAll(".nav-item[data-view], .more-calendar-item[data-view]").forEach((btn) => {
    const match =
      btn.dataset.view === state.currentView ||
      (state.currentView === "cal-day" && btn.dataset.view === "calendar");
    btn.classList.toggle("active", match);
  });
  hydrateNavIcons(document.getElementById("sidebar"));
  hydrateNavIcons(document.getElementById("mobile-tabbar"));
  renderMobileDrawer();
}

function suppressAutofillBar(el) {
  if (!el || el.dataset.autofillSuppressed === "1") return;
  el.dataset.autofillSuppressed = "1";
  // Chrome часто игнорит autocomplete=off — короткий readonly на фокусе глушит панель подсказок
  el.setAttribute("autocomplete", "off");
  el.setAttribute("data-lpignore", "true");
  el.setAttribute("data-1p-ignore", "true");
  el.setAttribute("data-form-type", "other");
  el.addEventListener("focus", () => {
    el.setAttribute("readonly", "readonly");
    requestAnimationFrame(() => {
      el.removeAttribute("readonly");
    });
  });
}

function token() {
  return localStorage.getItem(TOKEN_KEY) || "";
}

function getFontScale() {
  const n = Number(localStorage.getItem(FONT_SCALE_KEY) || FONT_SCALE_DEFAULT);
  if (!Number.isFinite(n)) return FONT_SCALE_DEFAULT;
  return Math.min(FONT_SCALE_MAX, Math.max(FONT_SCALE_MIN, Math.round(n)));
}

function applyFontScale(pct = getFontScale()) {
  const scale = Math.min(FONT_SCALE_MAX, Math.max(FONT_SCALE_MIN, Math.round(Number(pct) || FONT_SCALE_DEFAULT)));
  localStorage.setItem(FONT_SCALE_KEY, String(scale));
  document.documentElement.style.setProperty("--font-scale", String(scale / 100));
  const label = document.getElementById("settings-font-scale-value");
  if (label) label.textContent = `${scale}%`;
  const preview = document.getElementById("settings-font-preview");
  if (preview) preview.textContent = scale === 100 ? "Так выглядит текст задач" : `Так выглядит текст · ${scale}%`;
  return scale;
}

function showToast(msg) {
  const el = document.getElementById("toast");
  if (!el) return;
  el.textContent = msg;
  el.classList.remove("hidden");
  setTimeout(() => el.classList.add("hidden"), 2400);
}

function setBootMsg(msg) {
  const p = document.querySelector("#boot-splash [data-boot-msg]");
  if (p) p.textContent = msg || "";
}

function urlBase64ToUint8Array(base64String) {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const raw = atob(base64);
  const out = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; ++i) out[i] = raw.charCodeAt(i);
  return out;
}

function saveOfflineSnapshot() {
  try {
    localStorage.setItem(
      OFFLINE_SNAPSHOT_KEY,
      JSON.stringify({
        saved_at: Date.now(),
        tasks: state.tasks,
        doneTasks: state.doneTasks,
        checklists: state.checklists,
        projects: state.projects,
        summary: state.summary,
        measurements: state.measurements,
        workouts: state.workouts,
        healthSummary: state.healthSummary,
      })
    );
  } catch (_) {}
}

function applyOfflineSnapshot(snap) {
  state.tasks = snap.tasks || [];
  state.doneTasks = snap.doneTasks || [];
  state.checklists = snap.checklists || [];
  state.projects = snap.projects || [];
  state.summary = snap.summary || {};
  state.measurements = snap.measurements || [];
  state.workouts = snap.workouts || [];
  state.healthSummary = snap.healthSummary || {};
}

async function api(path, opts = {}) {
  const headers = { "Content-Type": "application/json", "X-Planning-Token": token() };
  const ctrl = new AbortController();
  const ms = opts.timeoutMs ?? 12000;
  const timer = setTimeout(() => ctrl.abort(), ms);
  let res;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      ...opts,
      cache: "no-store",
      signal: opts.signal || ctrl.signal,
      headers: { ...headers, ...opts.headers },
    });
  } catch (e) {
    if (e && e.name === "AbortError") throw new Error("Сервер не ответил (таймаут)");
    throw e;
  } finally {
    clearTimeout(timer);
  }
  if (res.status === 401) {
    document.getElementById("auth-screen")?.classList.remove("hidden");
    throw new Error("auth");
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(formatApiError(err.detail, res.statusText || `HTTP ${res.status}`));
  }
  if (res.status === 204) return null;
  return res.json();
}

function formatApiError(detail, fallback = "Ошибка запроса") {
  if (!detail) return fallback;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === "string") return item;
        if (item && typeof item.msg === "string") return item.msg;
        return JSON.stringify(item);
      })
      .join("; ");
  }
  if (detail && typeof detail.msg === "string") return detail.msg;
  try {
    return JSON.stringify(detail);
  } catch {
    return fallback;
  }
}

async function apiUpload(path, file) {
  const fd = new FormData();
  fd.append("file", file);
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "X-Planning-Token": token() },
    body: fd,
  });
  if (res.status === 401) {
    document.getElementById("auth-screen").classList.remove("hidden");
    throw new Error("auth");
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(formatApiError(err.detail, res.statusText));
  }
  return res.json();
}

async function apiDownload(path, filename, { method = "GET" } = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers: { "X-Planning-Token": token() },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(formatApiError(err.detail, res.statusText));
  }
  const blob = await res.blob();
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.rel = "noopener";
  a.style.display = "none";
  document.body.appendChild(a);
  a.click();
  setTimeout(() => {
    URL.revokeObjectURL(a.href);
    a.remove();
  }, 2000);
}

function taskImageSrc(task, pendingFile) {
  if (pendingFile) return URL.createObjectURL(pendingFile);
  if (task?.image_url) return `${task.image_url}?v=${task.updated_at || ""}`;
  return null;
}

function renderTaskImagePreview(task = null) {
  const preview = document.getElementById("tf-image-preview");
  const removeBtn = document.getElementById("tf-image-remove");
  const fileInput = document.getElementById("tf-image-file");
  if (!preview) return;
  const src = state.pendingTaskImageRemove
    ? null
    : taskImageSrc(task, state.pendingTaskImage);
  if (src) {
    preview.classList.remove("hidden");
    preview.innerHTML = `<img src="${escapeHtml(src)}" alt="">`;
    removeBtn?.classList.remove("hidden");
  } else {
    preview.classList.add("hidden");
    preview.innerHTML = "";
    removeBtn?.classList.add("hidden");
  }
  if (fileInput) fileInput.value = "";
}

async function uploadTaskImage(taskId, file) {
  if (!file || !taskId) return null;
  return apiUpload(`/tasks/${taskId}/image`, file);
}

async function deleteTaskImage(taskId) {
  if (!taskId) return;
  await api(`/tasks/${taskId}/image`, { method: "DELETE" });
}

function dateToIsoLocal(d) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function todayStr() {
  return dateToIsoLocal(new Date());
}

function defaultProgramAnchor() {
  const today = todayStr();
  const d = new Date(`${today}T12:00:00`);
  let daysAhead = (0 - d.getDay() + 1) % 7;
  if (daysAhead === 0) daysAhead = 7;
  d.setDate(d.getDate() + daysAhead);
  return dateToIsoLocal(d);
}

function programScheduleStorageKey(programId) {
  return `empire_program_schedule_${programId || "gym_2026"}`;
}

function getProgramSchedule(programId) {
  const pid = programId || state.programId || "gym_2026";
  try {
    const raw = localStorage.getItem(programScheduleStorageKey(pid));
    if (raw) {
      const parsed = JSON.parse(raw);
      if (parsed.anchor && parsed.startDay) return parsed;
    }
  } catch (_) {}
  return { anchor: defaultProgramAnchor(), startDay: "A" };
}

function saveProgramSchedule(programId, schedule) {
  const pid = programId || state.programId || "gym_2026";
  localStorage.setItem(programScheduleStorageKey(pid), JSON.stringify(schedule));
}

function programScheduleHtml() {
  const sch = getProgramSchedule(state.programId);
  const opts = ["A", "B", "C"]
    .map((d) => `<option value="${d}"${sch.startDay === d ? " selected" : ""}>День ${d}</option>`)
    .join("");
  return `<div class="program-schedule card">
    <div class="program-schedule-row">
      <label class="program-schedule-field">Старт цикла
        <input type="date" id="program-anchor" value="${escapeHtml(sch.anchor)}">
      </label>
      <label class="program-schedule-field">Первый день
        <select id="program-start-day">${opts}</select>
      </label>
    </div>
    <div class="program-schedule-hint">Тренировки: понедельник · среда · пятница</div>
  </div>`;
}

function bindProgramScheduleHandlers(el) {
  const anchorInp = el.querySelector("#program-anchor");
  const startSel = el.querySelector("#program-start-day");
  const onChange = () => {
    saveProgramSchedule(state.programId, {
      anchor: anchorInp?.value || defaultProgramAnchor(),
      startDay: startSel?.value || "A",
    });
    renderWorkoutProgram().catch((err) => showToast(err.message));
  };
  anchorInp?.addEventListener("change", onChange);
  startSel?.addEventListener("change", onChange);
}

function addDays(n) {
  return addDaysToDateStr(todayStr(), n);
}

function addDaysToDateStr(iso, days) {
  const d = new Date(`${iso}T12:00:00`);
  d.setDate(d.getDate() + days);
  return dateToIsoLocal(d);
}

function formatDiaryDate(iso) {
  if (!iso) return "";
  const d = new Date(`${iso}T12:00:00`);
  return d.toLocaleDateString("ru-RU", { weekday: "short", day: "numeric", month: "short" });
}

function formatWeekGroupLabel(iso) {
  const today = todayStr();
  const tomorrow = addDays(1);
  const wd = new Date(`${iso}T12:00:00`).toLocaleDateString("ru-RU", { weekday: "short" });
  if (iso === today) return `${wd}, Сегодня`;
  if (iso === tomorrow) return `${wd}, Завтра`;
  return formatDiaryDate(iso);
}

function formatDayTitle(iso) {
  if (!iso) return "День";
  const d = new Date(`${iso}T12:00:00`);
  const today = todayStr();
  const tomorrow = addDays(1);
  const base = d.toLocaleDateString("ru-RU", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  });
  if (iso === today) return `Сегодня · ${base}`;
  if (iso === tomorrow) return `Завтра · ${base}`;
  return base.charAt(0).toUpperCase() + base.slice(1);
}

function openCalendarDay(day) {
  if (!day) return;
  state.calendarDay = day;
  state.calendarMonth = `${day.slice(0, 7)}-01`;
  showView("cal-day");
}

function useTaskSplitPane() {
  return window.matchMedia("(min-width: 900px)").matches;
}

function highlightSelectedTaskRow() {
  document.querySelectorAll(".task-row--selected").forEach((r) => r.classList.remove("task-row--selected"));
  if (!state.editingId) return;
  document.querySelectorAll(`[data-task-id="${state.editingId}"]`).forEach((r) => r.classList.add("task-row--selected"));
}

function usesDesktopTaskSplit() {
  return useTaskSplitPane() && SPLIT_TASK_VIEWS.has(state.currentView);
}

function syncSplitTaskLayout() {
  const app = document.getElementById("app");
  const sheet = document.getElementById("task-sheet");
  const split = usesDesktopTaskSplit();
  const showForm = !!state.editingId || state.creatingTask;
  app?.classList.toggle("split-task-mode", split);
  document.getElementById("resizer-detail")?.classList.toggle("hidden", !split);
  if (!sheet) return;
  if (split) {
    sheet.classList.remove("hidden");
    sheet.classList.toggle("detail-empty", !showForm);
    sheet.setAttribute("aria-hidden", showForm ? "false" : "true");
    document.getElementById("task-detail-empty")?.setAttribute("aria-hidden", showForm ? "true" : "false");
  } else if (!showForm) {
    sheet.classList.add("hidden");
    sheet.classList.remove("detail-empty");
    sheet.setAttribute("aria-hidden", "true");
  } else {
    sheet.classList.remove("hidden");
    sheet.classList.remove("detail-empty");
    sheet.setAttribute("aria-hidden", "false");
  }
  highlightSelectedTaskRow();
}

const COLUMN_WIDTH_KEYS = {
  sidebar: "empire_col_sidebar_w",
  detail: "empire_col_detail_w",
};
const COLUMN_WIDTH_LIMITS = {
  sidebar: { min: 200, max: 480, default: 260, cssVar: "--sidebar-w" },
  detail: { min: 300, max: 720, default: 420, cssVar: "--detail-panel-w" },
};

function clampColWidth(n, limits) {
  return Math.min(limits.max, Math.max(limits.min, Math.round(n)));
}

function readCssPx(app, cssVar, fallback) {
  const raw = getComputedStyle(app).getPropertyValue(cssVar).trim();
  const n = parseFloat(raw);
  return Number.isFinite(n) ? n : fallback;
}

function loadColumnWidths() {
  const app = document.getElementById("app");
  if (!app) return;
  Object.entries(COLUMN_WIDTH_LIMITS).forEach(([key, limits]) => {
    const stored = Number(localStorage.getItem(COLUMN_WIDTH_KEYS[key]));
    const w = clampColWidth(Number.isFinite(stored) && stored > 0 ? stored : limits.default, limits);
    app.style.setProperty(limits.cssVar, `${w}px`);
  });
}

function bindColumnResizer(el, key) {
  if (!el) return;
  const limits = COLUMN_WIDTH_LIMITS[key];
  const app = document.getElementById("app");
  let startX = 0;
  let startW = 0;
  const invert = key === "detail";

  const onMove = (e) => {
    const dx = e.clientX - startX;
    const next = clampColWidth(startW + (invert ? -dx : dx), limits);
    app.style.setProperty(limits.cssVar, `${next}px`);
  };
  const onUp = () => {
    document.removeEventListener("mousemove", onMove);
    document.removeEventListener("mouseup", onUp);
    document.body.classList.remove("col-resizing");
    el.classList.remove("active");
    const w = readCssPx(app, limits.cssVar, limits.default);
    localStorage.setItem(COLUMN_WIDTH_KEYS[key], String(w));
  };
  const onDown = (e) => {
    if (!useTaskSplitPane()) return;
    if (key === "detail" && !app.classList.contains("split-task-mode")) return;
    if (key === "sidebar" && app.classList.contains("settings-mode")) return;
    e.preventDefault();
    startX = e.clientX;
    startW = readCssPx(app, limits.cssVar, limits.default);
    document.body.classList.add("col-resizing");
    el.classList.add("active");
    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseup", onUp);
  };
  el.addEventListener("mousedown", onDown);
  el.addEventListener("keydown", (e) => {
    if (!useTaskSplitPane()) return;
    if (key === "detail" && !app.classList.contains("split-task-mode")) return;
    if (e.key !== "ArrowLeft" && e.key !== "ArrowRight") return;
    e.preventDefault();
    const cur = readCssPx(app, limits.cssVar, limits.default);
    const step = e.shiftKey ? 40 : 16;
    const delta = (e.key === "ArrowLeft" ? -1 : 1) * (invert ? -step : step);
    const next = clampColWidth(cur + delta, limits);
    app.style.setProperty(limits.cssVar, `${next}px`);
    localStorage.setItem(COLUMN_WIDTH_KEYS[key], String(next));
  });
  el.addEventListener("dblclick", () => {
    app.style.setProperty(limits.cssVar, `${limits.default}px`);
    localStorage.removeItem(COLUMN_WIDTH_KEYS[key]);
  });
}

function bindColumnResizers() {
  bindColumnResizer(document.getElementById("resizer-sidebar"), "sidebar");
  bindColumnResizer(document.getElementById("resizer-detail"), "detail");
}

function workoutDiaryNavHtml(dateValue, inputId) {
  return `<div class="diary-nav card">
    <button type="button" class="btn small diary-shift" data-shift="-7" title="−7 дней">«</button>
    <button type="button" class="btn small diary-shift" data-shift="-1" title="−1 день">‹</button>
    <div class="diary-nav-center">
      <input type="date" id="${inputId}" value="${dateValue}">
      <div class="diary-nav-label">${escapeHtml(formatDiaryDate(dateValue))}</div>
    </div>
    <button type="button" class="btn small diary-shift" data-shift="1" title="+1 день">›</button>
    <button type="button" class="btn small diary-shift" data-shift="7" title="+7 дней">»</button>
    <button type="button" class="btn small diary-today" type="button">Сегодня</button>
  </div>`;
}

function bindDiaryNav(root, { inputId, onChange }) {
  const input = root.querySelector(`#${inputId}`);
  if (!input) return;
  const apply = (val) => {
    input.value = val;
    const label = root.querySelector(".diary-nav-label");
    if (label) label.textContent = formatDiaryDate(val);
    onChange(val);
  };
  input.onchange = () => apply(input.value);
  root.querySelectorAll(".diary-shift").forEach((btn) => {
    btn.onclick = () => apply(addDaysToDateStr(input.value, Number(btn.dataset.shift)));
  });
  root.querySelector(".diary-today")?.addEventListener("click", () => apply(todayStr()));
}

function escapeHtml(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function formatPlainText(s) {
  if (!s) return "";
  let h = escapeHtml(s);
  h = h.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  h = h.replace(/\n/g, "<br>");
  return h;
}

function checklistByRef(ref) {
  return state.checklists.find((c) => c.agent_ref === ref) || null;
}

function checklistPct(cl) {
  if (!cl) return null;
  const total = cl.items_total || 0;
  const done = cl.items_done || 0;
  return total ? Math.round((done / total) * 100) : 0;
}

function renderFinanceModel() {
  const el = document.getElementById("view-finance-model");
  const FM = window.EMPIRE_FINANCE_MODEL;
  if (!FM) {
    el.innerHTML = '<div class="empty">Не загружен контент финмодели</div>';
    return;
  }

  const tab =
    state.fmPipelineTab === "snegiri"
      ? "snegiri"
      : state.fmPipelineTab === "career"
        ? "career"
        : "empire";
  const tabsHtml = `<div class="fm-tabs" role="tablist">
    <button type="button" class="fm-tab ${tab === "empire" ? "active" : ""}" data-fm-tab="empire" role="tab" aria-selected="${tab === "empire"}">Empire · книга и Где Пар</button>
    <button type="button" class="fm-tab ${tab === "snegiri" ? "active" : ""}" data-fm-tab="snegiri" role="tab" aria-selected="${tab === "snegiri"}">Снегири · гири</button>
    <button type="button" class="fm-tab ${tab === "career" ? "active" : ""}" data-fm-tab="career" role="tab" aria-selected="${tab === "career"}">Карьера · B2B</button>
  </div>`;

  if (tab === "snegiri") {
    el.innerHTML = tabsHtml + renderFinanceModelSnegiriBody(FM.snegiri);
    return;
  }
  if (tab === "career") {
    el.innerHTML = tabsHtml + renderFinanceModelCareerBody(FM.career);
    return;
  }

  el.innerHTML = tabsHtml + renderFinanceModelEmpireBody(FM);
}

function renderFinanceModelCareerBody(C) {
  if (!C) {
    return '<div class="empty">Нет блока career в finance_model_content.js</div>';
  }
  const pipeCl = checklistByRef(C.pipelineRef || "career-b2b-pipeline");
  const pipePct = checklistPct(pipeCl);

  const introHtml = (C.intro || [])
    .map((p) => `<p class="fm-intro-p">${formatPlainText(p)}</p>`)
    .join("");

  const phasesHtml = (C.phases || [])
    .map((ph) => {
      const cl = checklistByRef(ph.key);
      const pct = checklistPct(cl);
      const clId = cl?.id || "";
      return `<div class="fm-phase card">
        <div class="fm-phase-head">
          <strong>${escapeHtml(ph.label)}</strong>
          <span class="fm-phase-dates">${escapeHtml(ph.dates || "")}</span>
          ${pct != null ? `<span class="fm-phase-pct">${pct}%</span>` : ""}
        </div>
        <p class="fm-phase-focus">${escapeHtml(ph.focus || "")}</p>
        ${clId ? `<button type="button" class="btn small" data-goto-checklist="${clId}">Чеклист фазы →</button>` : '<p class="muted">Чеклист не найден — запусти seed_career_b2b_plan_2026.py</p>'}
      </div>`;
    })
    .join("");

  const weeksHtml = (C.weekChecklists || [])
    .map((w) => {
      const cl = checklistByRef(w.key);
      const pct = checklistPct(cl);
      const clId = cl?.id || "";
      return `<button type="button" class="fm-block" data-goto-checklist="${clId}" ${clId ? "" : "disabled"}>
        <span class="fm-block-title">${escapeHtml(w.label)}</span>
        ${pct != null ? `<span class="fm-block-pct">${pct}%</span>` : ""}
      </button>`;
    })
    .join("");

  const extraHtml = (C.extraChecklists || [])
    .map((w) => {
      const cl = checklistByRef(w.key);
      const pct = checklistPct(cl);
      const clId = cl?.id || "";
      return `<button type="button" class="btn small" data-goto-checklist="${clId}" ${clId ? "" : "disabled"} style="margin:4px">
        ${escapeHtml(w.label)}${pct != null ? ` · ${pct}%` : ""}
      </button>`;
    })
    .join("");

  const careerTasks = state.tasks
    .filter(
      (t) =>
        (t.obsidian_source || "").startsWith("career-b2b:") &&
        t.status !== "done" &&
        t.status !== "archived" &&
        t.status !== "cancelled"
    )
    .sort((a, b) => String(a.due_date || "").localeCompare(String(b.due_date || "")))
    .slice(0, 12);

  const milestonesHtml = careerTasks.length
    ? `<ul class="fm-milestones">${careerTasks
        .map(
          (t) => `<li>
          <button type="button" class="btn-link" data-open-task="${t.id}">${escapeHtml(t.title)}</button>
          <span class="muted">${escapeHtml(t.due_date || "—")}</span>
        </li>`
        )
        .join("")}</ul>`
    : '<p class="muted">Вехи появятся после seed (задачи career-b2b:*).</p>';

  const howToHtml = (C.howTo || [])
    .map((line) => `<li>${formatPlainText(line)}</li>`)
    .join("");

  const proj = (state.projects || []).find((p) => p.title === C.projectTitle);

  return `
    <div class="card fm-hero">
      <h2 class="fm-title">${escapeHtml(C.title)}</h2>
      <p class="fm-period">${escapeHtml(C.period || "")}</p>
      <div class="fm-progress-row">
        <span>Общий прогресс пайплайна: <strong>${pipePct != null ? pipePct + "%" : "—"}</strong></span>
        ${pipeCl?.id ? `<button type="button" class="btn small" data-goto-checklist="${pipeCl.id}">Итоговый чеклист →</button>` : ""}
      </div>
      <div class="fm-intro">${introHtml}</div>
      ${proj?.id ? `<button type="button" class="btn small" data-project-id="${proj.id}">Открыть список задач проекта →</button>` : ""}
    </div>
    <div class="section-title">Как пользоваться</div>
    <ul class="fm-howto">${howToHtml}</ul>
    <div class="section-title">Фазы</div>
    ${phasesHtml}
    <div class="section-title">${escapeHtml(C.modulesSectionTitle || "Модули курса")}</div>
    <div class="fm-blocks">${weeksHtml}</div>
    <div class="section-title">EN · review · готовность</div>
    <div>${extraHtml}</div>
    <div class="section-title">Ближайшие вехи</div>
    ${milestonesHtml}
  `;
}

function renderFinanceModelEmpireBody(FM) {
  const pipeCl = checklistByRef("empire-pipeline-2026");
  const pipePct = checklistPct(pipeCl);

  const blocksHtml = FM.pipeline
    .map((b) => {
      const cl = checklistByRef(b.checklistRef);
      const pct = checklistPct(cl);
      const clId = cl?.id || "";
      const codes = [b.code, b.tracker].filter(Boolean).join(" · ");
      const links = (b.links || [])
        .map((c) => `<span class="fm-code-chip">${escapeHtml(c)}</span>`)
        .join("");
      const fullDesc = b.fullDesc ? `<p class="fm-block-full">${formatPlainText(b.fullDesc)}</p>` : "";
      return `<button type="button" class="fm-block" data-goto-checklist="${clId}" ${clId ? "" : "disabled"}>
        <span class="fm-block-num">${escapeHtml(b.num)}</span>
        <span class="fm-block-codes">${escapeHtml(codes)}${b.weight ? ` · ${escapeHtml(b.weight)}` : ""}</span>
        <span class="fm-block-title">${escapeHtml(b.title)}</span>
        <span class="fm-block-period">${escapeHtml(b.period)}</span>
        <span class="fm-block-text">${escapeHtml(b.text)}</span>
        ${fullDesc}
        ${links ? `<span class="fm-block-links">${links}</span>` : ""}
        ${pct != null ? `<span class="fm-block-pct">${pct}%</span>` : ""}
      </button>`;
    })
    .join('<span class="fm-arrow" aria-hidden="true">→</span>');

  const phasesHtml = FM.phases
    .map((ph) => {
      const cl = checklistByRef(ph.key);
      const pct = checklistPct(cl);
      const clId = cl?.id || "";
      const codeLine = [ph.code, ph.quarter].filter(Boolean).join(" · ");
      const fullDesc = ph.fullDesc ? `<p class="fm-phase-desc">${escapeHtml(ph.fullDesc)}</p>` : "";
      return `<div class="fm-phase card">
        <div class="fm-phase-head">
          <span class="fm-phase-code">${escapeHtml(codeLine)}</span>
          <strong>${escapeHtml(ph.label)}</strong>
          <span class="fm-phase-dates">${escapeHtml(ph.dates)}</span>
          ${pct != null ? `<span class="fm-phase-pct">${pct}%</span>` : ""}
        </div>
        <p class="fm-phase-focus">${escapeHtml(ph.focus)}</p>
        ${fullDesc}
        ${clId ? `<button type="button" class="btn small" data-goto-checklist="${clId}">Чеклист фазы →</button>` : ""}
      </div>`;
    })
    .join("");

  const modulesLegendHtml = (FM.modulesLegend || [])
    .map(
      (group) => `<details class="fm-module-group card">
        <summary class="fm-module-summary">${escapeHtml(group.title)}</summary>
        ${group.intro ? `<p class="fm-module-intro">${escapeHtml(group.intro)}</p>` : ""}
        <dl class="fm-module-list">
          ${(group.items || [])
            .map(
              (item) => `<div class="fm-module-item">
                <dt><span class="fm-module-code">${escapeHtml(item.code)}</span> ${escapeHtml(item.name)}</dt>
                <dd>${escapeHtml(item.text)}</dd>
              </div>`
            )
            .join("")}
        </dl>
      </details>`
    )
    .join("");

  const milestoneTasks = state.tasks
    .filter(
      (t) =>
        t.due_date &&
        t.status !== "done" &&
        ((t.tags || []).includes("веха") ||
          (t.tags || []).includes("финмодель") ||
          (t.title || "").startsWith("ФМ:") ||
          (t.title || "").startsWith("Веха:"))
    )
    .sort((a, b) => (a.due_date || "").localeCompare(b.due_date || ""));

  const msStatic = FM.milestones
    .map((m) => {
      const task = milestoneTasks.find((t) => t.due_date === m.date && (t.title || "").includes(m.title.slice(0, 12)));
      const done = task ? false : state.doneTasks.some((t) => t.due_date === m.date);
      return `<tr class="${done ? "fm-ms-done" : ""}">
        <td>${escapeHtml(formatDateRu(m.date))}</td>
        <td><strong>${escapeHtml(m.title)}</strong><div class="hint">${escapeHtml(m.hint)}</div></td>
        <td>${task ? `<button type="button" class="btn-link" data-open-task="${task.id}">В задачах</button>` : done ? "✓" : "—"}</td>
      </tr>`;
    })
    .join("");

  const cashflowCl = checklistByRef("empire-finance-cashflow");
  const metricsCl = checklistByRef("empire-finance-metrics");

  const glossaryHtml = FM.glossary
    .map((g) => `<dt>${escapeHtml(g.term)}</dt><dd>${escapeHtml(g.text)}</dd>`)
    .join("");

  const monthlyHtml = FM.monthlyPlan
    .map(
      (r) => `<tr>
        <td>${escapeHtml(r.month)}</td>
        <td>${escapeHtml(r.income)}</td>
        <td>${escapeHtml(r.expense)}</td>
        <td class="hint">${escapeHtml(r.note)}</td>
      </tr>`
    )
    .join("");

  const bridge = FM.bridge35k;
  const introHtml = FM.intro.map((p) => `<p>${formatPlainText(p)}</p>`).join("");
  const bridgeHtml = bridge.paragraphs.map((p) => `<p>${formatPlainText(p)}</p>`).join("");

  return `
    <div class="fm-hero card">
      <h2 class="fm-title">${escapeHtml(FM.title)}</h2>
      <p class="hint">${escapeHtml(FM.period)}</p>
      ${pipePct != null ? `<div class="fm-overall">Общий прогресс пайплайна: <strong>${pipePct}%</strong>
        ${pipeCl?.id ? `<button type="button" class="btn small" data-goto-checklist="${pipeCl.id}">Итоговый чеклист →</button>` : ""}
      </div>` : ""}
      <div class="fm-intro">${introHtml}</div>
    </div>

    <div class="fm-bridge card fm-bridge-highlight">
      <h3>${escapeHtml(bridge.title)}</h3>
      <p class="fm-bridge-short"><strong>${escapeHtml(bridge.short)}</strong></p>
      ${bridgeHtml}
      <p class="hint">Срок: до ${escapeHtml(formatDateRu(bridge.deadline))} · задача в календаре и в проекте «Финмодель»</p>
    </div>

    <div class="section-title">Расшифровка модулей Empire</div>
    <p class="fm-hint">Коды из аудита Empire. Полная финмодель «Снегири · гири» — на соседней вкладке.</p>
    <div class="fm-modules">${modulesLegendHtml}</div>

    <div class="section-title">Пайплайн к цели (6 блоков)</div>
    <p class="hint fm-hint">Нажмите на блок — откроется связанный чеклист. Отмечайте пункты там, чтобы видеть процент.</p>
    <div class="fm-pipeline">${blocksHtml}</div>

    <div class="section-title">Фазы по месяцам</div>
    <div class="fm-phases">${phasesHtml}</div>

    <div class="section-title">Вехи с датами</div>
    <p class="hint fm-hint">Те же даты — в календаре приложения. «В задачах» — открыть карточку.</p>
    <div class="card fm-table-wrap">
      <table class="fm-table">
        <thead><tr><th>Дата</th><th>Что должно быть сделано</th><th></th></tr></thead>
        <tbody>${msStatic}</tbody>
      </table>
    </div>

    <div class="section-title">План денег по месяцам (ориентир)</div>
    <div class="card fm-table-wrap">
      <table class="fm-table">
        <thead><tr><th>Месяц</th><th>Доход Σ</th><th>Расход</th><th>Комментарий</th></tr></thead>
        <tbody>${monthlyHtml}</tbody>
      </table>
      ${cashflowCl?.id ? `<button type="button" class="btn small" style="margin:12px" data-goto-checklist="${cashflowCl.id}">Сверка план/факт (чеклист) →</button>` : ""}
    </div>

    <div class="section-title">Куда идут деньги</div>
    <div class="card">
      ${FM.moneySplit.rows
        .map(
          (r) => `<div class="fm-money-row">
            <strong>${escapeHtml(r.what)}</strong>
            <span>${escapeHtml(r.who)}</span>
            <span class="hint">${escapeHtml(r.share)}</span>
          </div>`
        )
        .join("")}
    </div>

    <div class="section-title">Словарь</div>
    <dl class="card fm-glossary">${glossaryHtml}</dl>

    <div class="fm-footer card">
      <p><strong>Как работать каждую неделю</strong></p>
      <ol class="fm-howto">
        <li>Раздел <em>Финмодель</em> — понять, на какой фазе вы сейчас.</li>
        <li><em>Чеклисты</em> — отмечать сделанное (фаза + итоговый %).</li>
        <li><em>Календарь</em> — не пропускать вехи с датой.</li>
        <li>Проект <em>Empire · Финмодель</em> — задачи с подробными пояснениями в заметке.</li>
        <li>Воскресенье — KPI и чеклист «метрики»${metricsCl?.id ? ` (<button type="button" class="btn-link" data-goto-checklist="${metricsCl.id}">открыть</button>)` : ""}.</li>
      </ol>
    </div>`;
}

function renderFinanceModelSnegiriBody(SN) {
  if (!SN) {
    return '<div class="empty card">Раздел «Снегири» не загружен</div>';
  }

  const introHtml = (SN.intro || []).map((p) => `<p>${formatPlainText(p)}</p>`).join("");
  const verdictHtml = (SN.verdict?.paragraphs || []).map((p) => `<p>${formatPlainText(p)}</p>`).join("");

  const stepsHtml = (SN.product?.steps || [])
    .map(
      (s) => `<div class="fm-sn-step">
        <span class="fm-sn-step-num">${escapeHtml(s.step)}</span>
        <strong>${escapeHtml(s.name)}</strong>
        <span class="hint">${escapeHtml(s.price)}</span>
        <p>${escapeHtml(s.text)}</p>
      </div>`
    )
    .join("");

  const tracksHtml = (SN.product?.tracks || [])
    .map(
      (t) => `<div class="fm-sn-track card">
        <strong>${escapeHtml(t.name)}</strong>
        <span class="hint">${escapeHtml(t.audience)}</span>
        <p>${formatPlainText(t.text)}</p>
      </div>`
    )
    .join("");

  const pricingHtml = (SN.pricing || [])
    .map(
      (p) => `<tr><td><strong>${escapeHtml(p.name)}</strong></td><td>${escapeHtml(p.price)}</td><td class="hint">${escapeHtml(p.note)}</td></tr>`
    )
    .join("");

  const capexRows = (SN.capex?.rows || [])
    .map((r) => `<tr><td>${escapeHtml(r.what)}</td><td>${escapeHtml(r.amount)}</td></tr>`)
    .join("");

  const unitRows = (SN.unitEconomics?.rows || [])
    .map((r) => `<tr><td>${escapeHtml(r.label)}</td><td>${formatPlainText(r.value)}</td></tr>`)
    .join("");

  const pipelineHtml = (SN.pipeline || [])
    .map((b) => {
      const fullDesc = b.fullDesc ? `<p class="fm-block-full">${formatPlainText(b.fullDesc)}</p>` : "";
      return `<div class="fm-block fm-block-static">
        <span class="fm-block-num">${escapeHtml(b.num)}</span>
        <span class="fm-block-title">${escapeHtml(b.title)}</span>
        <span class="fm-block-period">${escapeHtml(b.period)}</span>
        <span class="fm-block-text">${escapeHtml(b.text)}</span>
        ${fullDesc}
      </div>`;
    })
    .join('<span class="fm-arrow" aria-hidden="true">→</span>');

  const phasesHtml = (SN.phases || [])
    .map(
      (ph) => `<div class="fm-phase card">
        <div class="fm-phase-head">
          <strong>${escapeHtml(ph.label)}</strong>
          <span class="fm-phase-dates">${escapeHtml(ph.dates)}</span>
        </div>
        <p class="fm-phase-focus">${escapeHtml(ph.focus)}</p>
        <p class="fm-phase-desc">${escapeHtml(ph.fullDesc)}</p>
      </div>`
    )
    .join("");

  const killHtml = (SN.killMetrics || [])
    .map(
      (k) => `<div class="fm-sn-kill card">
        <div class="fm-sn-kill-head"><strong>${escapeHtml(k.title)}</strong><span class="hint">${escapeHtml(k.deadline)}</span></div>
        <p>${formatPlainText(k.text)}</p>
      </div>`
    )
    .join("");

  const msHtml = (SN.milestones || [])
    .map(
      (m) => `<tr><td>${escapeHtml(formatDateRu(m.date))}</td><td><strong>${escapeHtml(m.title)}</strong><div class="hint">${escapeHtml(m.hint)}</div></td></tr>`
    )
    .join("");

  const monthlyHtml = (SN.monthlyPlan || [])
    .map(
      (r) => `<tr>
        <td>${escapeHtml(r.month)}</td>
        <td>${escapeHtml(r.paying)}</td>
        <td>${escapeHtml(r.mrr)}</td>
        <td>${escapeHtml(r.cashflow)}</td>
        <td class="hint">${escapeHtml(r.note)}</td>
      </tr>`
    )
    .join("");

  const scenarioHtml = (SN.scenarios?.rows || [])
    .map(
      (r) => `<tr>
        <td><strong>${escapeHtml(r.name)}</strong></td>
        <td>${escapeHtml(r.conversion)}</td>
        <td>${escapeHtml(r.churn)}</td>
        <td>${escapeHtml(r.revshare)}</td>
        <td>${escapeHtml(r.be)}</td>
      </tr>`
    )
    .join("");

  const moneyHtml = (SN.moneySplit?.rows || [])
    .map(
      (r) => `<div class="fm-money-row">
        <strong>${escapeHtml(r.what)}</strong>
        <span>${escapeHtml(r.who)}</span>
        <span class="hint">${escapeHtml(r.share)}</span>
      </div>`
    )
    .join("");

  const glossaryHtml = (SN.glossary || [])
    .map((g) => `<dt>${escapeHtml(g.term)}</dt><dd>${escapeHtml(g.text)}</dd>`)
    .join("");

  const howtoHtml = (SN.howTo || []).map((li) => `<li>${formatPlainText(li)}</li>`).join("");

  return `
    <div class="fm-hero card">
      <h2 class="fm-title">${escapeHtml(SN.title)}</h2>
      <p class="hint">${escapeHtml(SN.site)} · ${escapeHtml(SN.period)}</p>
      <div class="fm-intro">${introHtml}</div>
    </div>

    <div class="fm-bridge card fm-bridge-highlight fm-sn-verdict">
      <h3>${escapeHtml(SN.verdict?.title || "Итог")}</h3>
      <p class="fm-bridge-short"><strong>${escapeHtml(SN.verdict?.short || "")}</strong></p>
      ${verdictHtml}
    </div>

    <div class="section-title">Что продаём</div>
    <div class="fm-sn-steps">${stepsHtml}</div>
    <div class="fm-sn-tracks">${tracksHtml}</div>

    <div class="section-title">Тарифы подписки</div>
    <div class="card fm-table-wrap">
      <table class="fm-table"><thead><tr><th>Тариф</th><th>Цена</th><th>Комментарий</th></tr></thead><tbody>${pricingHtml}</tbody></table>
    </div>

    <div class="section-title">${escapeHtml(SN.capex?.title || "Вложения до запуска")}</div>
    <p class="hint fm-hint">Итого: <strong>${escapeHtml(SN.capex?.total || "")}</strong>. ${escapeHtml(SN.capex?.cashReserve || "")}</p>
    <div class="card fm-table-wrap">
      <table class="fm-table"><thead><tr><th>Статья</th><th>Сумма</th></tr></thead><tbody>${capexRows}</tbody></table>
      <p class="hint" style="margin:12px">${escapeHtml(SN.capex?.codeBeforeContract || "")}</p>
    </div>

    <div class="section-title">${escapeHtml(SN.unitEconomics?.title || "Юнит-экономика")}</div>
    <p class="hint fm-hint">${escapeHtml(SN.unitEconomics?.note || "")}</p>
    <div class="card fm-table-wrap">
      <table class="fm-table"><tbody>${unitRows}</tbody></table>
    </div>

    <div class="section-title">Пайплайн разработки (7 шагов)</div>
    <p class="hint fm-hint">Слева направо: от договора с тренером до питания во второй версии. ~26 недель.</p>
    <div class="fm-pipeline">${pipelineHtml}</div>

    <div class="section-title">Стоп-метрики (когда останавливаем или меняем курс)</div>
    <div class="fm-sn-kills">${killHtml}</div>

    <div class="section-title">Фазы после запуска</div>
    <div class="fm-phases">${phasesHtml}</div>

    <div class="section-title">Вехи с датами</div>
    <div class="card fm-table-wrap">
      <table class="fm-table"><thead><tr><th>Дата</th><th>Событие</th></tr></thead><tbody>${msHtml}</tbody></table>
    </div>

    <div class="section-title">План по месяцам (ориентир)</div>
    <div class="card fm-table-wrap">
      <table class="fm-table">
        <thead><tr><th>Месяц</th><th>Платящие</th><th>Выручка подписок</th><th>Денежный поток</th><th>Комментарий</th></tr></thead>
        <tbody>${monthlyHtml}</tbody>
      </table>
    </div>

    <div class="section-title">${escapeHtml(SN.scenarios?.title || "Сценарии")}</div>
    <div class="card fm-table-wrap">
      <table class="fm-table">
        <thead><tr><th>Сценарий</th><th>Конверсия</th><th>Отток</th><th>Доля тренеру</th><th>Безубыточность</th></tr></thead>
        <tbody>${scenarioHtml}</tbody>
      </table>
    </div>

    <div class="section-title">${escapeHtml(SN.moneySplit?.title || "Куда идут деньги")}</div>
    <div class="card">${moneyHtml}</div>

    <div class="section-title">Налоги</div>
    <div class="card"><p>${formatPlainText(SN.taxNote || "")}</p></div>

    <div class="section-title">Словарь (все сокращения расшифрованы)</div>
    <dl class="card fm-glossary">${glossaryHtml}</dl>

    <div class="fm-footer card">
      <p><strong>Как работать с моделью</strong></p>
      <ol class="fm-howto">${howtoHtml}</ol>
    </div>`;
}

function formatDateRu(iso) {
  if (!iso) return "";
  const [y, m, d] = iso.split("-").map(Number);
  const months = ["янв", "фев", "мар", "апр", "май", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"];
  return `${d} ${months[m - 1]}. ${y}`;
}

function formatDue(t) {
  let s = "";
  if (t.due_date) s += t.due_date;
  if (t.due_time) s += (s ? " " : "") + t.due_time;
  return s;
}

function repeatKeyFromObj(obj) {
  if (!obj) return "";
  const f = obj.freq;
  const i = obj.interval || 1;
  if (f === "daily" && i === 1) return "daily";
  if (f === "weekdays") return "weekdays";
  if (f === "weekly" && i === 2) return "biweekly";
  if (f === "weekly") return "weekly";
  if (f === "monthly") return "monthly";
  if (f === "yearly") return "yearly";
  return "";
}

function computeRemindAt(dueDate, dueTime, offsetMin) {
  if (!dueDate || offsetMin === "" || offsetMin == null) return null;
  const tm = dueTime || "09:00";
  const base = new Date(`${dueDate}T${tm}:00`);
  if (isNaN(base)) return null;
  base.setMinutes(base.getMinutes() - Number(offsetMin));
  return base.toISOString().slice(0, 19);
}

function remindOffsetFromTask(t) {
  if (!t.remind_at || !t.due_date) return "";
  const due = new Date(`${t.due_date}T${t.due_time || "09:00"}:00`);
  const rem = new Date(t.remind_at.replace(" ", "T"));
  const diff = Math.round((due - rem) / 60000);
  const presets = [0, 5, 15, 60, 1440];
  return String(presets.find((p) => Math.abs(p - diff) < 3) ?? "");
}

function priorityBadge(p) {
  if (p >= 3) return '<span class="badge high">высокий</span>';
  if (p === 2) return '<span class="badge">средний</span>';
  if (p === 1) return '<span class="badge">низкий</span>';
  return "";
}

function numOrEmpty(v) {
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

function formatNum(v, digits = 1) {
  if (v == null || v === "") return "—";
  return Number(v).toFixed(digits).replace(/\.0$/, "");
}

function measurementRowHtml(m) {
  const parts = [];
  if (m.weight_kg != null) parts.push(`${formatNum(m.weight_kg)} кг`);
  if (m.waist_cm != null) parts.push(`талия ${formatNum(m.waist_cm)}`);
  if (m.biceps_r_cm != null || m.biceps_l_cm != null) {
    parts.push(`бицепс ${formatNum(m.biceps_r_cm)}/${formatNum(m.biceps_l_cm)}`);
  }
  if (m.legs_cm != null) parts.push(`ноги ${formatNum(m.legs_cm)}`);
  const note = m.note ? `<div class="task-note-preview">${escapeHtml(m.note)}</div>` : "";
  return `
    <div class="task-row health-row" data-measurement-id="${m.id}">
      <div class="health-icon">📏</div>
      <div class="task-body" data-action="open-measurement" data-id="${m.id}">
        <div class="task-title">${escapeHtml(m.measured_on)}</div>
        <div class="task-meta">${parts.map((p) => `<span class="badge">${escapeHtml(p)}</span>`).join("")}</div>
        ${note}
      </div>
    </div>`;
}

function workoutRowHtml(w) {
  const vol = w.sets > 1 ? `${w.sets}×` : "";
  const note = w.note ? `<div class="task-note-preview">${escapeHtml(w.note)}</div>` : "";
  return `
    <div class="task-row health-row" data-workout-id="${w.id}">
      <div class="health-icon">🏋</div>
      <div class="task-body" data-action="open-workout" data-id="${w.id}">
        <div class="task-title">${escapeHtml(w.exercise_label || w.exercise_key)}</div>
        <div class="task-meta">
          <span class="badge">${escapeHtml(w.logged_on)}</span>
          <span class="badge">${vol}${formatNum(w.weight_kg)} кг × ${w.reps}</span>
        </div>
        ${note}
      </div>
    </div>`;
}

function isoWeekKey(d = new Date()) {
  const x = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
  const day = x.getUTCDay() || 7;
  x.setUTCDate(x.getUTCDate() + 4 - day);
  const yearStart = new Date(Date.UTC(x.getUTCFullYear(), 0, 1));
  const week = Math.ceil((((x - yearStart) / 86400000) + 1) / 7);
  return `${x.getUTCFullYear()}-W${week}`;
}

function isSunday(d = new Date()) {
  return d.getDay() === 0;
}

function renderLineChart(points, title, valueFn, unit = "") {
  const pts = (points || [])
    .filter((p) => valueFn(p) != null)
    .map((p) => ({ x: p.measured_on || p.logged_on || "", y: Number(valueFn(p)) }))
    .filter((p) => p.x && Number.isFinite(p.y))
    .sort((a, b) => a.x.localeCompare(b.x));
  if (pts.length < 2) {
    return `<div class="spark-card"><div class="section-title">${escapeHtml(title)}</div><div class="empty" style="padding:12px">Нужно минимум два замера</div></div>`;
  }
  const w = 320;
  const h = 148;
  const padL = 36;
  const padR = 12;
  const padT = 12;
  const padB = 28;
  const ys = pts.map((p) => p.y);
  const min = Math.min(...ys);
  const max = Math.max(...ys);
  const span = max - min || 1;
  const innerW = w - padL - padR;
  const innerH = h - padT - padB;
  const xy = pts.map((p, i) => {
    const x = padL + (pts.length === 1 ? innerW / 2 : (i / (pts.length - 1)) * innerW);
    const y = padT + innerH - ((p.y - min) / span) * innerH;
    return { ...p, px: x, py: y };
  });
  const d = xy.map((p, i) => `${i ? "L" : "M"}${p.px.toFixed(1)},${p.py.toFixed(1)}`).join(" ");
  const last = xy[xy.length - 1];
  const firstLbl = escapeHtml(pts[0].x.slice(5));
  const lastLbl = escapeHtml(pts[pts.length - 1].x.slice(5));
  const dots = xy
    .map((p) => `<circle cx="${p.px.toFixed(1)}" cy="${p.py.toFixed(1)}" r="2.4" fill="currentColor"><title>${escapeHtml(p.x)}: ${formatNum(p.y)}${unit}</title></circle>`)
    .join("");
  return `<div class="spark-card line-chart-card">
    <div class="section-title">${escapeHtml(title)} <span class="line-chart-now">${formatNum(last.y)}${escapeHtml(unit)}</span></div>
    <svg class="line-chart" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none" role="img" aria-label="${escapeHtml(title)}">
      <text x="4" y="${padT + 10}" class="line-chart-axis">${formatNum(max)}</text>
      <text x="4" y="${h - padB}" class="line-chart-axis">${formatNum(min)}</text>
      <path d="${d}" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linejoin="round" stroke-linecap="round"/>
      ${dots}
      <text x="${padL}" y="${h - 8}" class="line-chart-axis">${firstLbl}</text>
      <text x="${w - padR}" y="${h - 8}" class="line-chart-axis" text-anchor="end">${lastLbl}</text>
    </svg>
  </div>`;
}

function renderSparkChart(points, title, valueFn, unit = "") {
  return renderLineChart(points, title, valueFn, unit);
}

function bicepsAvg(m) {
  const r = m.biceps_r_cm;
  const l = m.biceps_l_cm;
  if (r != null && l != null) return (Number(r) + Number(l)) / 2;
  return r ?? l ?? null;
}

function measurementSettingsHtml() {
  const s = state.healthSettings;
  const checked = s.remind_measure_sunday ? "checked" : "";
  return `
    <div class="health-settings card" style="padding:14px;margin-bottom:12px">
      <label class="toggle-row">
        <input type="checkbox" id="hs-remind-sunday" ${checked}>
        <span>Напоминать о замере по воскресеньям</span>
      </label>
      <div class="field-grid" style="margin-top:10px">
        <div>
          <label class="field-label">Час напоминания</label>
          <input id="hs-remind-hour" type="number" min="0" max="23" value="${s.remind_measure_hour ?? 10}">
        </div>
      </div>
      <button type="button" id="hs-save" class="btn small" style="margin-top:10px;width:auto">Сохранить настройки</button>
    </div>`;
}

function sundayBannerHtml() {
  if (!state.healthSettings.remind_measure_sunday) return "";
  if (!isSunday()) return "";
  if (state.healthSummary.measurement_this_week) return "";
  return `<div class="health-banner">
    <span>📏 Воскресенье — время замеров тела</span>
    <button type="button" class="btn small" data-action="add-measurement-now">+ Замер</button>
  </div>`;
}

function renderMeasurementCharts() {
  const ms = [...state.measurements];
  return [
    renderSparkChart(ms, "Вес, кг", (m) => m.weight_kg, " кг"),
    renderSparkChart(ms, "Талия, см", (m) => m.waist_cm, " см"),
    renderSparkChart(ms, "Бицепс (средн.), см", bicepsAvg, " см"),
    renderSparkChart(ms, "Ноги, см", (m) => m.legs_cm, " см"),
  ].join("");
}

function renderMeasurements() {
  const el = document.getElementById("view-measurements");
  const hs = state.healthSummary;
  const head = hs.latest_weight_kg
    ? `<div class="health-hero">
        <div class="health-hero-val">${formatNum(hs.latest_weight_kg)} <span>кг</span></div>
        <div class="health-hero-sub">${escapeHtml(hs.latest_measured_on || "")}${hs.latest_waist_cm ? ` · талия ${formatNum(hs.latest_waist_cm)}` : ""}</div>
      </div>`
    : '<div class="empty" style="padding:16px">Добавьте первый замер</div>';
  const list = state.measurements.length
    ? `<div class="section-title">История</div><div class="card">${state.measurements.map(measurementRowHtml).join("")}</div>`
    : "";
  const charts = renderMeasurementCharts();
  el.innerHTML = sundayBannerHtml() + measurementSettingsHtml() + head + charts + list;
  const saveBtn = document.getElementById("hs-save");
  if (saveBtn) {
    saveBtn.onclick = async () => {
      const body = {
        remind_measure_sunday: document.getElementById("hs-remind-sunday").checked,
        remind_measure_hour: Number(document.getElementById("hs-remind-hour").value),
      };
      const r = await api("/body/settings", { method: "PUT", body: JSON.stringify(body) });
      state.healthSettings = r;
      showToast("Настройки сохранены");
      renderMeasurements();
    };
  }
}

function getRestTimerDefaultSec() {
  const n = Number(localStorage.getItem("empire_rest_sec") || 120);
  return REST_TIMER_PRESETS.includes(n) ? n : 120;
}

function restTimerAutostartEnabled() {
  return localStorage.getItem("empire_rest_autostart") !== "0";
}

function formatRestTimer(ms) {
  const totalSec = Math.max(0, Math.ceil(ms / 1000));
  const m = Math.floor(totalSec / 60);
  const s = totalSec % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

function formatRestPreset(sec) {
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return s ? `${m}:${String(s).padStart(2, "0")}` : `${m}:00`;
}

function restTimerRemainingMs() {
  const rt = state.restTimer;
  if (rt.pausedRemainingMs != null) return rt.pausedRemainingMs;
  if (!rt.endAt) return 0;
  return Math.max(0, rt.endAt - Date.now());
}

function restTimerIsRunning() {
  return state.restTimer.endAt != null || state.restTimer.pausedRemainingMs != null;
}

function stopRestTimerInterval() {
  if (state.restTimer.intervalId) {
    clearInterval(state.restTimer.intervalId);
    state.restTimer.intervalId = null;
  }
}

function playRestTimerBeep() {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = "sine";
    osc.frequency.value = 880;
    gain.gain.value = 0.12;
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + 0.25);
    setTimeout(() => {
      const osc2 = ctx.createOscillator();
      const gain2 = ctx.createGain();
      osc2.type = "sine";
      osc2.frequency.value = 988;
      gain2.gain.value = 0.12;
      osc2.connect(gain2);
      gain2.connect(ctx.destination);
      osc2.start();
      osc2.stop(ctx.currentTime + 0.35);
    }, 280);
  } catch (_) {}
}

function onRestTimerComplete() {
  stopRestTimerInterval();
  state.restTimer.endAt = null;
  state.restTimer.pausedRemainingMs = null;
  syncRestTimerUI();
  showToast("Отдых окончен — следующий подход");
  if (navigator.vibrate) navigator.vibrate([180, 80, 180]);
  playRestTimerBeep();
}

function tickRestTimer() {
  if (state.restTimer.pausedRemainingMs != null) return;
  const left = restTimerRemainingMs();
  if (left <= 0) {
    onRestTimerComplete();
    return;
  }
  const display = document.getElementById("rest-timer-display");
  if (display) display.textContent = formatRestTimer(left);
}

function startRestTimer(seconds) {
  const sec = Number(seconds) || getRestTimerDefaultSec();
  localStorage.setItem("empire_rest_sec", String(sec));
  state.restTimer.presetSec = sec;
  state.restTimer.pausedRemainingMs = null;
  state.restTimer.endAt = Date.now() + sec * 1000;
  stopRestTimerInterval();
  syncRestTimerUI();
  tickRestTimer();
  state.restTimer.intervalId = setInterval(tickRestTimer, 200);
}

function pauseRestTimer() {
  if (state.restTimer.pausedRemainingMs != null) return;
  const left = restTimerRemainingMs();
  if (!left) return;
  stopRestTimerInterval();
  state.restTimer.pausedRemainingMs = left;
  state.restTimer.endAt = null;
  syncRestTimerUI();
}

function resumeRestTimer() {
  if (state.restTimer.pausedRemainingMs == null) return;
  state.restTimer.endAt = Date.now() + state.restTimer.pausedRemainingMs;
  state.restTimer.pausedRemainingMs = null;
  stopRestTimerInterval();
  syncRestTimerUI();
  tickRestTimer();
  state.restTimer.intervalId = setInterval(tickRestTimer, 200);
}

function stopRestTimer() {
  stopRestTimerInterval();
  state.restTimer.endAt = null;
  state.restTimer.pausedRemainingMs = null;
  syncRestTimerUI();
}

function addRestTimerSeconds(extra) {
  const addMs = (Number(extra) || 30) * 1000;
  if (state.restTimer.pausedRemainingMs != null) {
    state.restTimer.pausedRemainingMs += addMs;
  } else if (state.restTimer.endAt) {
    state.restTimer.endAt += addMs;
  } else {
    startRestTimer(Math.round(addMs / 1000));
    return;
  }
  syncRestTimerUI();
  tickRestTimer();
}

function syncRestTimerUI() {
  const bar = document.getElementById("rest-timer-bar");
  const idle = document.getElementById("rest-timer-idle");
  const active = document.getElementById("rest-timer-active");
  const display = document.getElementById("rest-timer-display");
  const sub = document.getElementById("rest-timer-sub");
  const pauseBtn = document.getElementById("rest-pause-btn");
  const autostart = document.getElementById("rest-autostart");
  if (!bar || !idle || !active) return;

  const running = restTimerIsRunning();
  const paused = state.restTimer.pausedRemainingMs != null;
  idle.classList.toggle("hidden", running);
  active.classList.toggle("hidden", !running);
  bar.classList.toggle("rest-timer-bar--active", running);

  const defaultSec = getRestTimerDefaultSec();
  bar.querySelectorAll(".rest-preset").forEach((btn) => {
    btn.classList.toggle("rest-preset--default", Number(btn.dataset.sec) === defaultSec);
  });

  if (running && display) {
    display.textContent = formatRestTimer(restTimerRemainingMs());
  }
  if (sub) sub.textContent = paused ? "пауза" : "осталось";
  if (pauseBtn) {
    pauseBtn.textContent = paused ? "Продолжить" : "Пауза";
    pauseBtn.dataset.action = paused ? "rest-resume" : "rest-pause";
  }
  if (autostart && autostart.checked !== restTimerAutostartEnabled()) {
    autostart.checked = restTimerAutostartEnabled();
  }
}

function initRestTimerControls() {
  const autostart = document.getElementById("rest-autostart");
  if (autostart) {
    autostart.checked = restTimerAutostartEnabled();
    autostart.addEventListener("change", () => {
      localStorage.setItem("empire_rest_autostart", autostart.checked ? "1" : "0");
    });
  }
  syncRestTimerUI();
}

function stopHoldTimerInterval() {
  if (state.holdTimer.intervalId) {
    clearInterval(state.holdTimer.intervalId);
    state.holdTimer.intervalId = null;
  }
}

function holdTimerRemainingMs() {
  const ht = state.holdTimer;
  if (ht.pausedRemainingMs != null) return ht.pausedRemainingMs;
  if (!ht.endAt) return 0;
  return Math.max(0, ht.endAt - Date.now());
}

function holdTimerIsRunning() {
  return state.holdTimer.endAt != null || state.holdTimer.pausedRemainingMs != null;
}

function formatHoldTimer(ms) {
  const totalSec = Math.max(0, Math.ceil(ms / 1000));
  return String(totalSec);
}

function syncHoldTimerUI() {
  const bar = document.getElementById("hold-timer-bar");
  const display = document.getElementById("hold-timer-display");
  const label = document.getElementById("hold-timer-label");
  const pauseBtn = document.getElementById("hold-pause-btn");
  if (!bar) return;
  const running = holdTimerIsRunning();
  const paused = state.holdTimer.pausedRemainingMs != null;
  bar.classList.toggle("hidden", !running);
  bar.classList.toggle("hold-timer-bar--active", running);
  bar.setAttribute("aria-hidden", running ? "false" : "true");
  if (display && running) display.textContent = formatHoldTimer(holdTimerRemainingMs());
  if (label) label.textContent = state.holdTimer.label || "Удержание";
  if (pauseBtn) {
    pauseBtn.textContent = paused ? "Продолжить" : "Пауза";
    pauseBtn.dataset.action = paused ? "hold-resume" : "hold-pause";
  }
  const root = document.getElementById("view-program");
  if (root && state.holdTimer.idx != null && state.holdTimer.setNum != null) {
    const status = root.querySelector(
      `.pg-hold-status[data-idx="${state.holdTimer.idx}"][data-set="${state.holdTimer.setNum}"]`,
    );
    if (status && running) status.textContent = paused ? "пауза" : `${formatHoldTimer(holdTimerRemainingMs())} сек`;
    else if (status && !running) status.textContent = "";
  }
}

function onHoldTimerComplete() {
  const idx = state.holdTimer.idx;
  const setNum = state.holdTimer.setNum;
  stopHoldTimerInterval();
  state.holdTimer.endAt = null;
  state.holdTimer.pausedRemainingMs = null;
  syncHoldTimerUI();
  playRestTimerBeep();
  if (navigator.vibrate) navigator.vibrate([180, 80, 180]);
  showToast("Удержание завершено");
  const root = document.getElementById("view-program");
  if (root && idx != null && setNum != null) {
    const ex = state.programSession?.exercises?.[Number(idx)];
    const secInp = root.querySelector(`.pg-hold-sec[data-idx="${idx}"][data-set="${setNum}"]`);
    // Авто-галочка только для чисто временных подходов (планка), не для Макгилла с повторами
    if (ex?.is_time_hold) {
      const cb = root.querySelector(`.pg-set-done[data-idx="${idx}"][data-set="${setNum}"]`);
      if (cb) {
        cb.checked = true;
        updateProgramDots(root, idx);
        if (restTimerAutostartEnabled()) startRestTimer(getRestTimerDefaultSec());
      }
      if (secInp) secInp.dataset.touched = "1";
      scheduleProgramAutoSave();
    }
  }
}

function tickHoldTimer() {
  if (state.holdTimer.pausedRemainingMs != null) return;
  const left = holdTimerRemainingMs();
  if (left <= 0) {
    onHoldTimerComplete();
    return;
  }
  syncHoldTimerUI();
}

function startHoldTimer(idx, setNum, seconds, label) {
  const sec = Math.max(1, Number(seconds) || 60);
  stopHoldTimer();
  state.holdTimer.idx = idx;
  state.holdTimer.setNum = setNum;
  state.holdTimer.label = label || "Удержание";
  state.holdTimer.pausedRemainingMs = null;
  state.holdTimer.endAt = Date.now() + sec * 1000;
  syncHoldTimerUI();
  tickHoldTimer();
  state.holdTimer.intervalId = setInterval(tickHoldTimer, 200);
}

function pauseHoldTimer() {
  if (state.holdTimer.pausedRemainingMs != null) return;
  const left = holdTimerRemainingMs();
  if (!left) return;
  stopHoldTimerInterval();
  state.holdTimer.pausedRemainingMs = left;
  state.holdTimer.endAt = null;
  syncHoldTimerUI();
}

function resumeHoldTimer() {
  if (state.holdTimer.pausedRemainingMs == null) return;
  state.holdTimer.endAt = Date.now() + state.holdTimer.pausedRemainingMs;
  state.holdTimer.pausedRemainingMs = null;
  stopHoldTimerInterval();
  syncHoldTimerUI();
  tickHoldTimer();
  state.holdTimer.intervalId = setInterval(tickHoldTimer, 200);
}

function stopHoldTimer() {
  stopHoldTimerInterval();
  state.holdTimer.endAt = null;
  state.holdTimer.pausedRemainingMs = null;
  state.holdTimer.idx = null;
  state.holdTimer.setNum = null;
  state.holdTimer.label = "";
  syncHoldTimerUI();
}

function syncRestTimerChrome(view) {
  const bar = document.getElementById("rest-timer-bar");
  if (!bar) return;
  const show = view === "workouts" || view === "program";
  bar.classList.toggle("hidden", !show);
  bar.setAttribute("aria-hidden", show ? "false" : "true");
  document.body.classList.toggle("health-timers-on", show);
  if (show) {
    document.getElementById("fab-add")?.classList.add("hidden");
    document.getElementById("fab-ai")?.classList.add("hidden");
    syncRestTimerUI();
  }
  if (view !== "program") stopHoldTimer();
}

function initRestTimerControls() {
  const autostart = document.getElementById("rest-autostart");
  if (autostart) {
    autostart.checked = restTimerAutostartEnabled();
    autostart.addEventListener("change", () => {
      localStorage.setItem("empire_rest_autostart", autostart.checked ? "1" : "0");
    });
  }
  syncRestTimerUI();
}

function renderWorkouts() {
  const el = document.getElementById("view-workouts");
  state.workoutDiaryDate = state.workoutDiaryDate || todayStr();
  const from = addDaysToDateStr(state.workoutDiaryDate, -7);
  const to = addDaysToDateStr(state.workoutDiaryDate, 7);
  const nav = workoutDiaryNavHtml(state.workoutDiaryDate, "workout-diary-date");
  const programLink = `<div class="card program-promo">
    <strong>Программы</strong> — зал (2026) и <em>Работа вне зала</em> (резина + стадион).
    <button type="button" class="btn linkish" data-goto="program">Открыть программу →</button>
  </div>`;
  api(`/workouts?from_date=${from}&to_date=${to}&limit=200`)
    .then((res) => {
      const logs = res.workouts || [];
      const byDate = {};
      logs.forEach((w) => {
        byDate[w.logged_on] = byDate[w.logged_on] || [];
        byDate[w.logged_on].push(w);
      });
      const days = [];
      for (let i = -7; i <= 7; i += 1) days.push(addDaysToDateStr(state.workoutDiaryDate, i));
      const sections = days.map((day) => {
        const items = byDate[day] || [];
        const title = day === todayStr() ? `Сегодня · ${formatDiaryDate(day)}` : formatDiaryDate(day);
        if (!items.length) {
          return `<div class="section-title">${escapeHtml(title)}</div><div class="card"><div class="empty" style="padding:12px">Нет записей</div></div>`;
        }
        return `<div class="section-title">${escapeHtml(title)} (${items.length})</div><div class="card">${items.map(workoutRowHtml).join("")}</div>`;
      }).join("");
      el.innerHTML = nav + programLink + sections;
      bindDiaryNav(el, {
        inputId: "workout-diary-date",
        onChange: (val) => {
          state.workoutDiaryDate = val;
          renderWorkouts();
        },
      });
      el.querySelector('[data-goto="program"]')?.addEventListener("click", () => {
        state.programDate = state.workoutDiaryDate;
        showView("program");
      });
    })
    .catch(() => {
      el.innerHTML = nav + programLink + '<div class="empty">Не удалось загрузить дневник</div>';
      bindDiaryNav(el, {
        inputId: "workout-diary-date",
        onChange: (val) => {
          state.workoutDiaryDate = val;
          renderWorkouts();
        },
      });
    });
}

async function loadProgramSession(on) {
  state.programDate = on || state.programDate || todayStr();
  state.workoutDiaryDate = state.programDate;
  try {
    const [session, logsRes] = await Promise.all([
      api(`/workouts/program/session?on=${encodeURIComponent(state.programDate)}&${programApiQuery()}`),
      api(`/workouts?logged_on=${encodeURIComponent(state.programDate)}`),
    ]);
    state.programSession = session;
    state.programLogsForDate = logsRes.workouts || [];
  } catch {
    state.programSession = null;
    state.programLogsForDate = [];
  }
}

function currentProgramNotePrefix() {
  const id = state.programId || "gym_2026";
  const meta = (state.workoutPrograms || []).find((p) => p.id === id);
  return meta?.note_prefix || (id === "outside_hall" ? "внезала подход" : "подход");
}

function programApiQuery() {
  const sch = getProgramSchedule(state.programId);
  const q = new URLSearchParams({
    program: state.programId || "gym_2026",
    anchor: sch.anchor,
    start_day: sch.startDay,
  });
  return q.toString();
}

function savedProgramSet(logs, exerciseKey, setNum) {
  const prefix = `${currentProgramNotePrefix()} ${setNum}/`;
  return logs.find((l) => l.exercise_key === exerciseKey && (l.note || "").startsWith(prefix));
}

function programSetCount(ex) {
  if (ex.is_max) return 1;
  return Math.max(1, ex.sets || 1);
}

function programHoldDefaultSec(ex) {
  return ex.hold_seconds || ex.reps || ex.reps_max || ex.reps_min || 60;
}

function programHoldSec(ex) {
  if (ex.hold_seconds) return Number(ex.hold_seconds);
  if (ex.is_time_hold) return programHoldDefaultSec(ex);
  return null;
}

function programExerciseRowHtml(ex, idx, logs) {
  if (ex.is_rest) {
    return `<div class="program-rest card">${escapeHtml(ex.detail || "Отдых")}</div>`;
  }
  const n = programSetCount(ex);
  const isHold = !!ex.is_time_hold;
  const holdSec = programHoldSec(ex);
  const w0 = ex.suggested_weight_kg ?? "";
  const reps0 = isHold ? programHoldDefaultSec(ex) : (ex.reps ?? ex.reps_max ?? ex.reps_min ?? 10);
  const hint = [ex.prescription, ex.detail].filter(Boolean).join(" · ");
  const setRows = [];
  for (let s = 1; s <= n; s += 1) {
    const saved = savedProgramSet(logs, ex.exercise_key, s);
    const wVal = saved ? saved.weight_kg : (s === 1 ? w0 : "");
    const rVal = saved ? saved.reps : reps0;
    const checked = saved ? "checked" : "";
    const touched = saved ? 'data-touched="1"' : "";
    if (isHold) {
      setRows.push(`<div class="program-set-row program-set-row--hold">
      <label class="set-check"><input type="checkbox" class="pg-set-done" data-idx="${idx}" data-set="${s}" ${checked}></label>
      <span class="set-num">${s}</span>
      <input type="number" class="pg-hold-sec pg-r" data-idx="${idx}" data-set="${s}" min="1" max="600" value="${rVal}" placeholder="сек" inputmode="numeric" ${touched}>
      <button type="button" class="btn small pg-hold-start" data-action="hold-start" data-idx="${idx}" data-set="${s}" title="Таймер">⏱</button>
      <span class="pg-hold-status" data-idx="${idx}" data-set="${s}"></span>
    </div>`);
    } else {
      const holdBtn = holdSec
        ? `<button type="button" class="btn small pg-hold-start" data-action="hold-start" data-idx="${idx}" data-set="${s}" data-hold-sec="${holdSec}" title="Удержание ${holdSec} сек">⏱ ${holdSec}</button>`
        : "";
      setRows.push(`<div class="program-set-row${holdSec ? " program-set-row--with-hold" : ""}">
      <label class="set-check"><input type="checkbox" class="pg-set-done" data-idx="${idx}" data-set="${s}" ${checked}></label>
      <span class="set-num">${s}</span>
      <input type="number" class="pg-w" data-idx="${idx}" data-set="${s}" min="0" step="2.5" value="${wVal !== "" && wVal != null ? wVal : ""}" placeholder="кг" inputmode="decimal" ${touched}>
      <input type="number" class="pg-r" data-idx="${idx}" data-set="${s}" min="1" max="50" value="${rVal}" placeholder="повт" inputmode="numeric" ${touched}>
      ${holdBtn}
    </div>`);
    }
  }
  const doneCount = setRows.length
    ? logs.filter((l) => {
        const note = l.note || "";
        return l.exercise_key === ex.exercise_key && note.startsWith(`${currentProgramNotePrefix()} `);
      }).length
    : 0;
  const dots = `${"●".repeat(Math.min(doneCount, n))}${"○".repeat(Math.max(0, n - doneCount))}`;
  const headCols = isHold
    ? `<div class="program-sets-head program-sets-head--hold"><span></span><span>#</span><span>сек</span><span>⏱</span><span></span></div>`
    : holdSec
      ? `<div class="program-sets-head program-sets-head--with-hold"><span></span><span>#</span><span>кг</span><span>повт</span><span>⏱</span></div>`
      : `<div class="program-sets-head"><span></span><span>#</span><span>кг</span><span>повт</span></div>`;
  const planLabel = isHold
    ? `${escapeHtml(ex.prescription)} · ${programHoldDefaultSec(ex)} сек`
    : holdSec
      ? `${escapeHtml(ex.prescription)} · ⏱ ${holdSec} сек`
      : escapeHtml(ex.prescription);
  const quickHold = holdSec
    ? `<button type="button" class="btn small program-hold-quick" data-action="hold-start" data-idx="${idx}" data-set="1" data-hold-sec="${holdSec}" title="Таймер ${holdSec} сек">⏱ ${holdSec} сек</button>`
    : "";
  return `<details class="program-ex card${isHold || holdSec ? " program-ex--hold" : ""}" ${isHold || holdSec ? "open" : ""}>
    <summary class="program-ex-summary">
      <span class="program-ex-title">${escapeHtml(ex.exercise_label)}</span>
      <span class="program-plan">${planLabel}</span>
      ${quickHold}
      <span class="program-dots" data-idx="${idx}">${dots}</span>
    </summary>
    <div class="program-ex-hint">${escapeHtml(hint)}</div>
    <div class="program-ex-body">
      ${headCols}
      ${setRows.join("")}
      ${!isHold && n > 1 ? `<button type="button" class="btn linkish pg-copy-w" data-idx="${idx}">Тот же вес во всех</button>` : ""}
    </div>
  </details>`;
}

function updateProgramDots(root, idx) {
  const boxes = root.querySelectorAll(`.pg-set-done[data-idx="${idx}"]`);
  let done = 0;
  boxes.forEach((b) => { if (b.checked) done += 1; });
  const el = root.querySelector(`.program-dots[data-idx="${idx}"]`);
  if (el) el.textContent = `${"●".repeat(done)}${"○".repeat(boxes.length - done)}`;
}

function bindProgramExerciseHandlers(root) {
  root.querySelectorAll(".pg-copy-w").forEach((btn) => {
    btn.onclick = () => {
      const idx = btn.dataset.idx;
      const first = root.querySelector(`.pg-w[data-idx="${idx}"][data-set="1"]`);
      if (!first) return;
      root.querySelectorAll(`.pg-w[data-idx="${idx}"]`).forEach((inp) => { inp.value = first.value; });
    };
  });
  root.querySelectorAll(".pg-set-done").forEach((cb) => {
    cb.onchange = () => {
      if (cb.checked && restTimerAutostartEnabled()) {
        startRestTimer(getRestTimerDefaultSec());
      }
      updateProgramDots(root, cb.dataset.idx);
      scheduleProgramAutoSave();
    };
  });
  root.querySelectorAll(".pg-w, .pg-r, .pg-hold-sec").forEach((inp) => {
    inp.addEventListener("input", () => {
      inp.dataset.touched = "1";
      scheduleProgramAutoSave();
    });
    inp.addEventListener("change", () => {
      inp.dataset.touched = "1";
      scheduleProgramAutoSave();
    });
  });
  root.querySelectorAll(".program-ex").forEach((det) => {
    det.addEventListener("toggle", () => {
      if (!det.open) return;
      requestAnimationFrame(() => {
        const last = det.querySelector(".program-set-row:last-child");
        const target = last || det.querySelector(".program-ex-body") || det;
        target.scrollIntoView({ block: "nearest", behavior: "smooth" });
      });
    });
  });
}

async function renderInsights() {
  const el = document.getElementById("view-insights");
  el.innerHTML = '<div class="empty">Анализ данных…</div>';
  try {
    const [daily, data] = await Promise.all([
      api("/insights/daily").catch(() => null),
      api("/insights?llm=0"),
    ]);
    state.insights = data;
    const pipe = data.pipeline || {};
    const tasks = data.tasks || {};
    const health = data.health || {};
    const focus = (daily?.focus_items || []).map((c) => `<li>${escapeHtml(c)}</li>`).join("");
    const dailyBlock = daily
      ? `<div class="insights-hero daily-brief">
        <h3>Фокус дня · ${escapeHtml(daily.day || "")}</h3>
        <div class="insights-meta">${daily.llm_used ? "LLM · " : ""}${daily.telegram_sent ? "TG ✓" : "PWA"}</div>
        <ul class="insights-list">${focus || "<li>—</li>"}</ul>
        ${daily.checklist_id ? `<button type="button" class="btn primary small" data-goto-checklist="${daily.checklist_id}">Чеклист фокуса →</button>` : ""}
        <button type="button" class="btn small" id="btn-run-daily" style="margin-top:8px">Запустить брифинг сейчас</button>
      </div>`
      : "";
    const conclusions = (data.conclusions || [])
      .map((c) => `<li>${escapeHtml(c)}</li>`)
      .join("");
    const narrative = data.narrative
      ? `<div class="card"><pre class="insights-narrative">${escapeHtml(data.narrative)}</pre></div>`
      : "";
    el.innerHTML = `
      ${dailyBlock}
      <div class="insights-hero">
        <h3>ИИ-брифинг Empire</h3>
        <div class="insights-meta">Обновлено: ${escapeHtml((data.generated_at || "").replace("T", " "))}</div>
        <button type="button" class="btn primary small" id="btn-refresh-insights" style="margin-top:10px">Обновить анализ</button>
      </div>
      <div class="insights-stat-grid">
        <div class="insights-stat"><strong>${tasks.tasks_todo ?? "—"}</strong><span>к выполнению</span></div>
        <div class="insights-stat"><strong>${tasks.overdue_count ?? 0}</strong><span>просрочено</span></div>
        <div class="insights-stat"><strong>${pipe.percent_weighted ?? "—"}%</strong><span>пайплайн (вес)</span></div>
        <div class="insights-stat"><strong>${health.workouts_last_31d ?? 0}</strong><span>силовых / 31д</span></div>
      </div>
      <div class="section-title">Выводы</div>
      <div class="card" style="padding:14px"><ul class="insights-list">${conclusions}</ul></div>
      ${narrative}`;
    document.getElementById("btn-refresh-insights").onclick = async () => {
      try {
        await api("/insights/refresh?llm=1", { method: "POST" });
        await renderInsights();
        showToast("Анализ обновлён");
      } catch (err) { showToast(err.message); }
    };
    document.getElementById("btn-run-daily")?.addEventListener("click", async () => {
      try {
        await api("/insights/daily/run?llm=1", { method: "POST" });
        await renderInsights();
        await loadAll();
        showToast("Брифинг готов");
      } catch (err) { showToast(err.message); }
    });
    el.querySelector("[data-goto-checklist]")?.addEventListener("click", async (e) => {
      const id = +e.currentTarget.dataset.gotoChecklist;
      showView("detail");
      await renderDetail(id);
    });
  } catch (err) {
    el.innerHTML = `<div class="empty">${escapeHtml(err.message)}</div>`;
  }
}

async function renderWorkoutProgram() {
  const el = document.getElementById("view-program");
  try {
    state.workoutProgramSummary = await api(`/workouts/program/summary?${programApiQuery()}`);
    state.workoutPrograms = state.workoutProgramSummary.programs || state.workoutPrograms || [];
    if (state.workoutProgramSummary.program_id) {
      state.programId = state.workoutProgramSummary.program_id;
    }
  } catch {
    el.innerHTML = '<div class="empty">Файл программы не найден на сервере</div>';
    return;
  }
  await loadProgramSession(state.programDate);
  const sum = state.workoutProgramSummary;
  const s = state.programSession;
  const nav = workoutDiaryNavHtml(state.programDate, "program-date");
  const switcher = programSwitcherHtml();
  const schedule = programScheduleHtml();
  const head = `<div class="card program-head">
    ${switcher}
    ${schedule}
    <div class="program-range">${escapeHtml(sum.title || "")} · ${sum.start || "—"} — ${sum.end || "—"} · ${sum.calendar_days || 0} тренировок</div>
    ${nav}
    <div id="program-autosave-hint" class="program-autosave-hint">Подходы сохраняются автоматически</div>
  </div>`;
  if (!s) {
    el.innerHTML = head + '<div class="empty">На эту дату нет тренировки по календарю этой программы</div>';
    bindProgramChrome(el);
    return;
  }
  const meta = s.meta && Object.keys(s.meta).length
    ? `<details class="card"><summary>Питание / фаза</summary><pre class="program-meta">${escapeHtml(JSON.stringify(s.meta, null, 2))}</pre></details>`
    : "";
  const logs = state.programLogsForDate || [];
  const exercises = (s.exercises || []).map((ex, idx) => programExerciseRowHtml(ex, idx, logs)).join("");
  el.innerHTML = `${head}
    <div class="card program-session">
      <h3>${escapeHtml(s.label)}</h3>
      <div class="program-sub">${escapeHtml(s.title || "")}${s.note ? " · " + escapeHtml(s.note) : ""}</div>
    </div>
    ${meta}
    <div class="section-title">Упражнения</div>
    ${exercises}
    <button type="button" class="btn block" id="btn-save-program">Сохранить сейчас</button>`;
  bindProgramChrome(el);
  document.getElementById("btn-save-program").onclick = () => saveProgramWorkout({ silent: false });
  bindProgramExerciseHandlers(el);
  el.querySelectorAll(".program-dots").forEach((d) => updateProgramDots(el, d.dataset.idx));
}

function programSwitcherHtml() {
  const programs = state.workoutPrograms?.length
    ? state.workoutPrograms
    : [
        { id: "gym_2026", title: "Программа 2026", short: "Зал" },
        { id: "outside_hall", title: "Работа вне зала", short: "Вне зала" },
      ];
  const chips = programs
    .map((p) => {
      const active = (state.programId || "gym_2026") === p.id ? " active" : "";
      const src = p.source === "user" ? " user" : "";
      return `<button type="button" class="chip program-switch-chip${active}${src}" data-action="switch-program" data-program-id="${escapeHtml(p.id)}">${escapeHtml(p.short || p.title)}</button>`;
    })
    .join("");
  const current = programs.find((p) => p.id === (state.programId || "gym_2026"));
  const del = current && current.source === "user"
    ? `<button type="button" class="btn small" data-action="delete-program">Удалить файл</button>`
    : "";
  return `<div class="program-switcher">
    <div class="chip-row">${chips}</div>
    <div class="program-file-row">
      <label class="btn small program-upload-btn">Загрузить файл
        <input id="program-file-input" type="file" accept=".json,.yaml,.yml,.md,application/json" hidden>
      </label>
      <button type="button" class="btn small" data-action="download-program-template">Скачать шаблон</button>
      <button type="button" class="btn small" data-action="export-program">Экспорт JSON</button>
      <button type="button" class="btn small" data-action="backup-health">Бэкап на VPS</button>
      ${del}
    </div>
    <p class="program-schedule-hint">Формат: empire-workout-program/v1 · JSON или YAML. Старый markdown тоже принимается.</p>
  </div>`;
}

function bindProgramChrome(el) {
  bindProgramScheduleHandlers(el);
  bindDiaryNav(el, {
    inputId: "program-date",
    onChange: async (val) => {
      state.programDate = val;
      await renderWorkoutProgram();
    },
  });
  const fileInp = el.querySelector("#program-file-input");
  if (fileInp) {
    fileInp.onchange = async () => {
      const file = fileInp.files && fileInp.files[0];
      if (!file) return;
      try {
        const r = await apiUpload("/workouts/program/upload", file);
        state.workoutPrograms = r.programs || [];
        if (r.program?.id) {
          state.programId = r.program.id;
          localStorage.setItem("empire_workout_program", r.program.id);
        }
        showToast("Программа загружена");
        await renderWorkoutProgram();
      } catch (err) {
        showToast(err.message || "Не удалось загрузить файл");
      } finally {
        fileInp.value = "";
      }
    };
  }
}

function collectProgramEntries() {
  const s = state.programSession;
  if (!s || !s.exercises) return [];
  const root = document.getElementById("view-program");
  if (!root) return [];
  const entries = [];
  s.exercises.forEach((ex, idx) => {
    if (ex.is_rest) return;
    const n = programSetCount(ex);
    for (let set = 1; set <= n; set += 1) {
      const wInp = root.querySelector(`.pg-w[data-idx="${idx}"][data-set="${set}"]`);
      const rInp = root.querySelector(`.pg-r[data-idx="${idx}"][data-set="${set}"]`);
      const done = root.querySelector(`.pg-set-done[data-idx="${idx}"][data-set="${set}"]`);
      const touched = wInp?.dataset.touched || rInp?.dataset.touched;
      if (done && !done.checked && !touched) continue;
      const wRaw = wInp?.value;
      const reps = Number(rInp?.value || 0);
      if (!reps || reps < 1) continue;
      const w = wRaw === "" || wRaw == null ? 0 : Number(wRaw);
      entries.push({
        logged_on: state.programDate,
        exercise_key: ex.exercise_key,
        weight_kg: w,
        reps,
        sets: 1,
        note: `${currentProgramNotePrefix()} ${set}/${n}`,
      });
    }
  });
  return entries;
}

function scheduleProgramAutoSave() {
  clearTimeout(state.programSaveTimer);
  state.programSaveTimer = setTimeout(() => {
    saveProgramWorkout({ silent: true, auto: true }).catch(() => {});
  }, 900);
}

async function saveProgramWorkout({ silent = false, auto = false } = {}) {
  if (state.programSaving) return;
  const entries = collectProgramEntries();
  if (!entries.length) {
    if (!silent) showToast("Отметьте хотя бы один подход");
    return;
  }
  state.programSaving = true;
  const hint = document.getElementById("program-autosave-hint");
  if (hint) hint.textContent = "Сохранение…";
  try {
    const r = await api("/workouts/program/log-batch", {
      method: "POST",
      body: JSON.stringify({
        logged_on: state.programDate,
        entries,
        replace_program: true,
        program_id: state.programId || "gym_2026",
      }),
    });
    const logsRes = await api(`/workouts?logged_on=${encodeURIComponent(state.programDate)}`);
    state.programLogsForDate = logsRes.workouts || [];
    const workRes = await api("/workouts?limit=100");
    state.workouts = workRes.workouts || [];
    if (hint) hint.textContent = auto ? `Автосохранено · ${r.saved} подх.` : `Сохранено: ${r.saved}`;
    if (!silent) showToast(`Сохранено: ${r.saved}`);
    const root = document.getElementById("view-program");
    if (root) {
      root.querySelectorAll(".program-dots").forEach((d) => updateProgramDots(root, d.dataset.idx));
    }
  } catch (err) {
    if (hint) hint.textContent = "Ошибка сохранения";
    if (!silent) showToast(err.message);
  } finally {
    state.programSaving = false;
  }
}

function periodChipsHtml(target) {
  const periods = [
    ["week", "7 дней"],
    ["month", "30 дней"],
    ["quarter", "90 дней"],
  ];
  return `<div class="chip-row period-chips" data-period-target="${target}">
    ${periods.map(([k, label]) => `<button type="button" class="chip${state.statsPeriod === k ? " active" : ""}" data-period="${k}">${label}</button>`).join("")}
  </div>`;
}

function progressBarHtml(label, pct, sub = "") {
  const p = Math.max(0, Math.min(100, pct));
  return `<div class="stat-row">
    <div class="stat-row-head"><span>${escapeHtml(label)}</span><strong>${p}%</strong></div>
    <div class="list-progress"><span style="width:${p}%"></span></div>
    ${sub ? `<div class="stat-sub">${escapeHtml(sub)}</div>` : ""}
  </div>`;
}

function deltaHtml(label, d, unit) {
  if (!d) return `<div class="stat-metric"><span class="stat-label">${escapeHtml(label)}</span><span class="stat-val">—</span></div>`;
  const sign = d.delta > 0 ? "+" : "";
  return `<div class="stat-metric">
    <span class="stat-label">${escapeHtml(label)}</span>
    <span class="stat-val">${formatNum(d.end)}${unit}</span>
    <span class="stat-delta${d.delta < 0 ? " good" : d.delta > 0 ? " warn" : ""}">${sign}${formatNum(d.delta)}${unit}</span>
  </div>`;
}

async function loadTaskStats() {
  state.taskStats = await api(`/stats/tasks?period=${state.statsPeriod}`);
}

async function loadHealthStats() {
  state.healthStats = await api(`/stats/health?period=${state.statsPeriod}`);
}

async function renderTaskStats() {
  await loadTaskStats();
  const s = state.taskStats;
  const el = document.getElementById("view-task-stats");
  const projects = (s.projects || [])
    .map((p) => progressBarHtml(p.title, p.pct, `${p.done}/${p.total} · открыто ${p.open}`))
    .join("");
  const lists = (s.checklists || [])
    .map((c) => progressBarHtml(c.title, c.pct, `${c.done}/${c.total}`))
    .join("");
  el.innerHTML = `
    ${periodChipsHtml("tasks")}
    <div class="stats-hero card">
      <div class="stat-metric"><span class="stat-label">Выполнено за период</span><span class="stat-val">${s.completed}</span></div>
      <div class="stat-metric"><span class="stat-label">Создано</span><span class="stat-val">${s.created}</span></div>
      <div class="stat-metric"><span class="stat-label">Открыто сейчас</span><span class="stat-val">${s.open}</span></div>
    </div>
    <div class="section-title">Прогресс по проектам</div>
    <div class="card stats-card">${projects || '<div class="empty">Нет задач в проектах</div>'}</div>
    <div class="section-title">Чеклисты</div>
    <div class="card stats-card">${lists || '<div class="empty">Чеклистов нет</div>'}</div>`;
  bindPeriodChips(el, "tasks");
}

async function renderHealthStats() {
  await loadHealthStats();
  const s = state.healthStats;
  const el = document.getElementById("view-health-stats");
  const charts = [
    renderSparkChart(state.measurements, "Вес, кг", (m) => m.weight_kg, " кг"),
    renderSparkChart(state.measurements, "Талия, см", (m) => m.waist_cm, " см"),
    renderSparkChart(state.measurements, "Бицепс (средн.), см", bicepsAvg, " см"),
    renderSparkChart(state.measurements, "Ноги, см", (m) => m.legs_cm, " см"),
  ].join("");
  const prs = (s.personal_records || [])
    .map((p) => `<span class="badge">${escapeHtml(p.exercise_label)}: ${formatNum(p.max_kg)} кг</span>`)
    .join("");
  const act = s.activities || {};
  el.innerHTML = `
    ${periodChipsHtml("health")}
    <div class="stats-hero card">
      ${deltaHtml("Вес", s.weight, " кг")}
      ${deltaHtml("Талия", s.waist, " см")}
      ${deltaHtml("Бицепс", s.biceps, " см")}
      ${deltaHtml("Ноги", s.legs, " см")}
    </div>
    <div class="stats-hero card" style="margin-top:8px">
      <div class="stat-metric"><span class="stat-label">ИМТ</span><span class="stat-val">${s.bmi ?? "—"}</span></div>
      <div class="stat-metric"><span class="stat-label">Талия/рост (WHtR)</span><span class="stat-val">${s.whtr ?? "—"}</span></div>
      <div class="stat-metric"><span class="stat-label">Силовых за период</span><span class="stat-val">${s.workouts_count}</span></div>
      <div class="stat-metric"><span class="stat-label">В неделю (силовые)</span><span class="stat-val">${s.workouts_per_week}</span></div>
      <div class="stat-metric"><span class="stat-label">Тоннаж / нед</span><span class="stat-val">${s.volume_per_week} кг</span></div>
      <div class="stat-metric"><span class="stat-label">Замеров</span><span class="stat-val">${s.measurements_count}</span></div>
    </div>
    ${charts}
    <div class="section-title">Рекорды за период</div>
    <div class="card stats-card"><div class="task-meta">${prs || "—"}</div></div>
    <div class="section-title">Кардио (авто-синхрон)</div>
    <div class="card stats-card" style="padding:14px;color:var(--muted);font-size:0.9rem">
      <p style="margin:0 0 8px">Garmin / Google Fit подгружаются на VPS автоматически — в приложении руками не импортируем.</p>
      <div class="task-meta">
        <span class="badge">${act.sessions || 0} тренировок</span>
        <span class="badge">${formatNum(act.distance_km, 1)} км</span>
        <span class="badge">${act.minutes || 0} мин</span>
        <span class="badge">${act.calories || 0} ккал</span>
      </div>
    </div>`;
  bindPeriodChips(el, "health");
}

function bindPeriodChips(container, target) {
  container.querySelectorAll("[data-period]").forEach((btn) => {
    btn.onclick = async () => {
      state.statsPeriod = btn.dataset.period;
      if (target === "tasks") await renderTaskStats();
      else await renderHealthStats();
    };
  });
}

function renderAllTasks() {
  let items = activeTasks();
  if (state.inboxOnly) items = items.filter((t) => !t.project_id);
  const sourceTasks = applyTagFilter(state.inboxOnly ? state.tasks.filter((t) => !t.project_id) : state.tasks);
  const groups = groupTasks(sourceTasks);
  const total = state.inboxOnly ? items.length : (state.summary?.tasks_todo ?? items.length);
  const hint = state.inboxOnly
    ? `<p class="sheet-hint">Входящие — задачи без проекта (${items.length}).</p>`
    : state.tagFilter
      ? `<p class="sheet-hint">Задачи с меткой #${escapeHtml(state.tagFilter)} (${items.length}).</p>`
      : total > items.length
        ? `<p class="sheet-hint">Показано ${items.length} из ${total}. Используйте поиск или фильтр по проекту.</p>`
        : "";
  document.getElementById("view-all-tasks").innerHTML =
    [
      quickAddHtml(),
      tagFilterBarHtml(),
      hint,
      groups.overdue.length ? '<div class="task-group-label overdue">Просрочено</div>' : "",
      groups.overdue.length ? renderTaskList(groups.overdue) : "",
      renderCollapsibleGroup("Сегодня", groups.today, { open: true, cls: "today" }),
      renderCollapsibleGroup("7 дней", groups.week, { open: true }),
      renderCollapsibleGroup("Позже / без срока", groups.later, { open: false }),
    ].filter(Boolean).join("") || `${quickAddHtml()}<div class="empty">Нет активных задач</div>`;
}

async function showLocalNotification(title, options = {}) {
  if (!("Notification" in window) || Notification.permission !== "granted") return false;
  const opts = {
    icon: ASSET_BASE + "/icon-192.png",
    badge: ASSET_BASE + "/icon-192.png",
    ...options,
  };
  if (opts.image && typeof opts.image === "string" && opts.image.startsWith("/")) {
    opts.image = `${location.origin}${opts.image}`;
  }
  try {
    if ("serviceWorker" in navigator) {
      const reg = await Promise.race([
        navigator.serviceWorker.ready,
        new Promise((_, rej) => setTimeout(() => rej(new Error("sw_ready_timeout")), 3000)),
      ]);
      await reg.showNotification(title, opts);
      return true;
    }
  } catch (_) {}
  try {
    // Desktop; on Android Chrome new Notification() throws Illegal constructor
    new Notification(title, opts);
    return true;
  } catch (_) {
    return false;
  }
}

function checkHealthReminders() {
  const s = state.healthSettings;
  if (!s.remind_measure_sunday) return;
  if (!isSunday()) return;
  const hour = Number(s.remind_measure_hour ?? 10);
  if (new Date().getHours() < hour) return;
  if (state.healthSummary.measurement_this_week) return;
  const weekKey = isoWeekKey();
  if (localStorage.getItem("empire_measure_reminded_week") === weekKey) return;
  if (!("Notification" in window) || Notification.permission !== "granted") return;
  localStorage.setItem("empire_measure_reminded_week", weekKey);
  void showLocalNotification("Задачник", {
    body: "Воскресенье — время замеров тела (вес, талия, бицепсы)",
    tag: "measure-sunday",
  });
}

function fillExerciseSelect(selected) {
  const sel = document.getElementById("wf-exercise");
  sel.innerHTML = Object.entries(state.exercises)
    .map(([k, label]) => `<option value="${k}"${k === selected ? " selected" : ""}>${escapeHtml(label)}</option>`)
    .join("");
}

function closeAllSheets() {
  closeDatePicker();
  closeMobileDrawer();
  closeOverflowMenu();
  closeSheet();
  closeMeasurementSheet();
  closeWorkoutSheet();
}

function openMeasurementSheet(row = null) {
  closeSheet();
  closeWorkoutSheet();
  const sheet = document.getElementById("measurement-sheet");
  sheet.classList.remove("hidden");
  sheet.setAttribute("aria-hidden", "false");
  document.getElementById("mf-id").value = row?.id || "";
  document.getElementById("mf-date").value = (row?.measured_on || todayStr()).slice(0, 10);
  document.getElementById("mf-weight").value = row?.weight_kg ?? "";
  document.getElementById("mf-waist").value = row?.waist_cm ?? "";
  document.getElementById("mf-biceps-r").value = row?.biceps_r_cm ?? "";
  document.getElementById("mf-biceps-l").value = row?.biceps_l_cm ?? "";
  document.getElementById("mf-legs").value = row?.legs_cm ?? "";
  document.getElementById("mf-note").value = row?.note || "";
  document.getElementById("mf-delete").classList.toggle("hidden", !row?.id);
}

function closeMeasurementSheet() {
  const sheet = document.getElementById("measurement-sheet");
  sheet.classList.add("hidden");
  sheet.setAttribute("aria-hidden", "true");
}

function openWorkoutSheet(row = null) {
  closeSheet();
  closeMeasurementSheet();
  fillExerciseSelect(row?.exercise_key || "bench_press");
  const sheet = document.getElementById("workout-sheet");
  sheet.classList.remove("hidden");
  sheet.setAttribute("aria-hidden", "false");
  document.getElementById("wf-id").value = row?.id || "";
  document.getElementById("wf-date").value = (row?.logged_on || todayStr()).slice(0, 10);
  document.getElementById("wf-exercise").value = row?.exercise_key || "bench_press";
  document.getElementById("wf-weight").value = row?.weight_kg ?? "";
  document.getElementById("wf-reps").value = row?.reps ?? "";
  document.getElementById("wf-sets").value = row?.sets ?? 1;
  document.getElementById("wf-note").value = row?.note || "";
  document.getElementById("wf-delete").classList.toggle("hidden", !row?.id);
}

function closeWorkoutSheet() {
  const sheet = document.getElementById("workout-sheet");
  sheet.classList.add("hidden");
  sheet.setAttribute("aria-hidden", "true");
}

function onPrimaryAdd() {
  const v = state.currentView;
  if (v === "health-stats" || v === "task-stats") return;
  if (v === "workouts") {
    openWorkoutSheet();
    return;
  }
  if (v === "program") {
    showView("workouts");
    return;
  }
  if (v === "measurements") {
    openMeasurementSheet();
    return;
  }
  openSheet(null);
  if (v === "cal-day" && state.calendarDay) {
    document.getElementById("tf-due-date").value = state.calendarDay;
  }
}

async function saveMeasurementForm(e) {
  e.preventDefault();
  const id = document.getElementById("mf-id").value;
  const body = {
    measured_on: document.getElementById("mf-date").value,
    weight_kg: numOrEmpty(document.getElementById("mf-weight").value),
    waist_cm: numOrEmpty(document.getElementById("mf-waist").value),
    biceps_r_cm: numOrEmpty(document.getElementById("mf-biceps-r").value),
    biceps_l_cm: numOrEmpty(document.getElementById("mf-biceps-l").value),
    legs_cm: numOrEmpty(document.getElementById("mf-legs").value),
    note: document.getElementById("mf-note").value.trim() || null,
  };
  if (id) await api(`/measurements/${id}`, { method: "PUT", body: JSON.stringify(body) });
  else await api("/measurements", { method: "POST", body: JSON.stringify(body) });
  closeMeasurementSheet();
  await loadAll();
  showToast("Замер сохранён");
}

async function saveWorkoutForm(e) {
  e.preventDefault();
  const id = document.getElementById("wf-id").value;
  const body = {
    logged_on: document.getElementById("wf-date").value,
    exercise_key: document.getElementById("wf-exercise").value,
    weight_kg: numOrEmpty(document.getElementById("wf-weight").value),
    reps: Number(document.getElementById("wf-reps").value),
    sets: Number(document.getElementById("wf-sets").value) || 1,
    note: document.getElementById("wf-note").value.trim() || null,
  };
  if (id) await api(`/workouts/${id}`, { method: "PUT", body: JSON.stringify(body) });
  else await api("/workouts", { method: "POST", body: JSON.stringify(body) });
  closeWorkoutSheet();
  await loadAll();
  showToast("Тренировка сохранена");
}

function taskRowHtml(t, { compact = false } = {}) {
  const done = t.status === "done";
  const doing = t.status === "doing";
  const checkCls = done ? "check done" : doing ? "check doing" : "check";
  const checkMark = done ? "✓" : doing ? "…" : "";
  const overdue = t.due_date && t.due_date < todayStr() && !done;

  if (compact) {
    const projectName = t.project_title || "Входящие";
    const projectHtml = t.project_id
      ? `<span class="task-project"><span class="project-dot" style="background:${projectColor(t.project_id)}"></span>${escapeHtml(projectName)}</span>`
      : `<span class="task-project">${escapeHtml(projectName)}</span>`;
    const metaDate = formatTaskMetaDate(t);
    const dateCls = metaDate.overdue ? "task-date overdue" : metaDate.today ? "task-date today" : "task-date";
    const selected = state.editingId === t.id ? " task-row--selected" : "";
    const priorityCls = (t.priority || 0) >= 3 ? " task-row--priority-high" : "";
    const icons = taskMetaIconsHtml(t);
    const tagsHtml = tagPillsHtml(t.tags, { limit: 2 });
    const metaHtml =
      metaDate.text || projectName || tagsHtml
        ? `<div class="task-meta-line">
            ${metaDate.text ? `<span class="${dateCls}">${icons}${escapeHtml(metaDate.text)}</span>` : "<span></span>"}
            ${projectHtml}
          </div>${tagsHtml}`
        : tagsHtml;
    return `
    <div class="task-row task-row--compact${done ? " task-row--done" : ""}${selected}${priorityCls}" data-task-id="${t.id}">
      <button type="button" class="${checkCls}" data-action="toggle-task" data-id="${t.id}" data-status="${t.status}">${checkMark}</button>
      <div class="task-body" data-action="open-task" data-id="${t.id}">
        <div class="task-title${done ? " done-text" : ""}">${escapeHtml(t.title)}</div>
        ${metaHtml}
      </div>
    </div>`;
  }

  let meta = "";
  const due = formatDue(t);
  if (due) meta += `<span class="badge${overdue ? " overdue" : ""}">${escapeHtml(due)}</span>`;
  if (t.repeat_label && t.repeat_label !== "Без повтора") {
    meta += `<span class="badge repeat">🔁 ${escapeHtml(t.repeat_label)}</span>`;
  }
  meta += priorityBadge(t.priority || 0);
  if (t.project_title) meta += `<span class="badge">${escapeHtml(t.project_title)}</span>`;
  (t.tags || []).forEach((tag) => {
    const color = tagColor(tag);
    meta += `<button type="button" class="badge badge-tag" data-action="filter-tag" data-tag="${escapeHtml(tag)}" style="--tag-color:${color}">#${escapeHtml(tag)}</button>`;
  });
  const noteLine = t.note
    ? `<div class="task-note-preview">${escapeHtml(t.note.split("\n")[0].slice(0, 140))}${t.note.length > 140 ? "…" : ""}</div>`
    : "";
  const thumb = t.image_url
    ? `<img class="task-thumb" src="${escapeHtml(t.image_url)}" alt="" loading="lazy">`
    : "";
  return `
    <div class="task-row${state.editingId === t.id ? " task-row--selected" : ""}" data-task-id="${t.id}">
      <button type="button" class="${checkCls}" data-action="toggle-task" data-id="${t.id}" data-status="${t.status}">${checkMark}</button>
      <div class="task-body" data-action="open-task" data-id="${t.id}">
        <div class="task-title-row">${thumb}<div class="task-title${done ? " done-text" : ""}">${escapeHtml(t.title)}</div></div>
        ${noteLine}
        <div class="task-meta">${meta}</div>
      </div>
    </div>`;
}

function sortByDueTime(a, b) {
  const ad = a.due_date || "9999";
  const bd = b.due_date || "9999";
  if (ad !== bd) return ad.localeCompare(bd);
  return (a.due_time || "99:99").localeCompare(b.due_time || "99:99");
}

function groupTasks(tasks) {
  const today = todayStr();
  const weekEnd = addDays(7);
  const groups = { overdue: [], today: [], week: [], later: [] };
  const sorted = [...tasks].sort(sortByDueTime);
  for (const t of sorted) {
    if (t.status === "done" || t.status === "cancelled") continue;
    if (!t.due_date) { groups.later.push(t); continue; }
    if (t.due_date < today) groups.overdue.push(t);
    else if (t.due_date === today) groups.today.push(t);
    else if (t.due_date <= weekEnd) groups.week.push(t);
    else groups.later.push(t);
  }
  return groups;
}

function renderSection(title, items, cls = "") {
  if (!items.length) return "";
  return `<div class="section-title ${cls}">${title} (${items.length})</div>
    ${renderTaskList(items)}`;
}

function renderToday() {
  const groups = groupTasks(applyTagFilter(state.tasks));
  const counts = taskNavCounts();
  const completedToday = [...counts.completedToday]
    .sort((a, b) => (b.completed_at || "").localeCompare(a.completed_at || ""))
    .slice(0, 50);
  const doneOpen = localStorage.getItem("empire_group_done_open") !== "0";
  const parts = [
    quickAddHtml(),
    tagFilterBarHtml(),
    groups.overdue.length
      ? renderCollapsibleGroup("Просрочено", groups.overdue, { open: true, cls: "overdue" })
      : "",
    renderCollapsibleGroup("Сегодня", groups.today, { open: true, cls: "today" }),
    state.hideDoneInLists
      ? ""
      : renderCollapsibleGroup("Выполнено", completedToday, {
          open: doneOpen,
          cls: "done",
          footer: completedToday.length
            ? `<button type="button" class="btn linkish" data-action="show-done-history">Вся история →</button>`
            : "",
        }),
  ].filter(Boolean);
  const el = document.getElementById("view-today");
  el.innerHTML = parts.join("") || `${quickAddHtml()}<div class="empty">Нет активных задач</div>`;
  el.querySelector(".task-group.done")?.addEventListener("toggle", (e) => {
    localStorage.setItem("empire_group_done_open", e.target.open ? "1" : "0");
  });
}

function renderWeek() {
  const today = todayStr();
  const weekEnd = addDays(7);
  const active = activeTasks().sort(sortByDueTime);
  const overdue = active.filter((t) => t.due_date && t.due_date < today);
  const byDay = {};
  for (let i = 0; i <= 7; i += 1) byDay[addDaysToDateStr(today, i)] = [];
  active.forEach((t) => {
    if (!t.due_date || t.due_date < today || t.due_date > weekEnd) return;
    byDay[t.due_date].push(t);
  });
  const parts = [quickAddHtml(), tagFilterBarHtml()];
  if (overdue.length) {
    parts.push(renderCollapsibleGroup("Просрочено", overdue, { open: true, cls: "overdue" }));
  }
  Object.entries(byDay).forEach(([day, items]) => {
    if (!items.length) return;
    const label = formatWeekGroupLabel(day);
    parts.push(renderCollapsibleGroup(label, items, { open: day === today || items.length <= 5 }));
  });
  const el = document.getElementById("view-week");
  el.innerHTML = parts.length > 1
    ? parts.join("")
    : `${quickAddHtml()}<div class="empty">На ближайшие 7 дней задач нет</div>`;
}

function eisenhowerQuadrant(task) {
  const today = todayStr();
  const urgentUntil = addDays(2);
  const important = (task.priority || 0) >= 2;
  const urgent = Boolean(task.due_date) && (task.due_date < today || task.due_date <= urgentUntil);
  if (urgent && important) return "q1";
  if (!urgent && important) return "q2";
  if (urgent && !important) return "q3";
  return "q4";
}

function renderMatrix() {
  const el = document.getElementById("view-matrix");
  const groups = { q1: [], q2: [], q3: [], q4: [] };
  activeTasks()
    .sort(sortByDueTime)
    .forEach((t) => groups[eisenhowerQuadrant(t)].push(t));
  const quadrant = (key) => {
    const meta = MATRIX_META[key];
    const body = groups[key].length
      ? `<div class="matrix-body">${renderTaskList(groups[key])}</div>`
      : '<div class="matrix-body"><div class="task-group-empty">Пусто</div></div>';
    return `<div class="matrix-quadrant ${key}">
      <div class="matrix-head"><strong>${escapeHtml(meta.title)}</strong><span>${escapeHtml(meta.hint)} · ${groups[key].length}</span></div>
      ${body}
    </div>`;
  };
  el.innerHTML = `
    <p class="matrix-note">Как в TickTick: <b>важно</b> — приоритет «средний» или «высокий»; <b>срочно</b> — просрочено или срок в ближайшие 2 дня.</p>
    <div class="matrix-grid">${["q1", "q2", "q3", "q4"].map(quadrant).join("")}</div>`;
}

function monthStartFromToday() {
  const t = todayStr();
  return `${t.slice(0, 7)}-01`;
}

function addMonthsToMonthStart(iso, delta) {
  const d = new Date(`${iso}T12:00:00`);
  d.setMonth(d.getMonth() + delta);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-01`;
}

function calendarGridRange(monthStart) {
  const d = new Date(`${monthStart}T12:00:00`);
  const y = d.getFullYear();
  const m = d.getMonth();
  const first = new Date(y, m, 1);
  const last = new Date(y, m + 1, 0);
  const startPad = (first.getDay() + 6) % 7;
  const gridStart = new Date(first);
  gridStart.setDate(first.getDate() - startPad);
  const endPad = 6 - ((last.getDay() + 6) % 7);
  const gridEnd = new Date(last);
  gridEnd.setDate(last.getDate() + endPad);
  return {
    monthStart,
    monthLabel: first.toLocaleDateString("ru-RU", { month: "long", year: "numeric" }),
    gridStart: dateToIsoLocal(gridStart),
    gridEnd: dateToIsoLocal(gridEnd),
    monthKey: monthStart.slice(0, 7),
  };
}

function expandGoogleEventDays(ev) {
  let start = ev.start;
  let end = ev.end || start;
  if (ev.all_day && end > start) {
    end = addDaysToDateStr(end, -1);
  }
  const days = [];
  let cur = start;
  while (cur <= end) {
    days.push(cur);
    cur = addDaysToDateStr(cur, 1);
  }
  return days;
}

function bindCalendarView(el) {
  el.querySelector('[data-action="cal-prev"]')?.addEventListener("click", () => {
    state.calendarMonth = addMonthsToMonthStart(state.calendarMonth, -1);
    renderCalendar();
  });
  el.querySelector('[data-action="cal-next"]')?.addEventListener("click", () => {
    state.calendarMonth = addMonthsToMonthStart(state.calendarMonth, 1);
    renderCalendar();
  });
  el.querySelector('[data-action="cal-today"]')?.addEventListener("click", () => {
    openCalendarDay(todayStr());
  });
  el.querySelector('[data-action="cal-pick-month"]')?.addEventListener("change", (e) => {
    const v = e.target.value;
    if (!v) return;
    state.calendarMonth = `${v}-01`;
    renderCalendar();
  });
  el.querySelectorAll(".cal-day[data-date]").forEach((cell) => {
    cell.addEventListener("click", async (e) => {
      if (e.target.closest("[data-action='toggle-task']")) return;
      const taskEv = e.target.closest(".cal-event.task[data-task-id]");
      if (taskEv) {
        const id = +taskEv.dataset.taskId;
        const t = [...state.tasks, ...state.doneTasks].find((x) => x.id === id);
        if (t) await openSheet(t);
        return;
      }
      openCalendarDay(cell.dataset.date);
    });
  });
}

function bindCalendarDayView(el) {
  el.querySelector('[data-action="cal-back-month"]')?.addEventListener("click", () => {
    showView("calendar");
  });
  el.querySelector('[data-action="cal-day-prev"]')?.addEventListener("click", () => {
    state.calendarDay = addDaysToDateStr(state.calendarDay, -1);
    state.calendarMonth = `${state.calendarDay.slice(0, 7)}-01`;
    renderCalendarDay();
  });
  el.querySelector('[data-action="cal-day-next"]')?.addEventListener("click", () => {
    state.calendarDay = addDaysToDateStr(state.calendarDay, 1);
    state.calendarMonth = `${state.calendarDay.slice(0, 7)}-01`;
    renderCalendarDay();
  });
  el.querySelector('[data-action="cal-day-today"]')?.addEventListener("click", () => {
    openCalendarDay(todayStr());
  });
}

function localCalendarTasks(gridStart, gridEnd) {
  return activeTasks().filter(
    (t) => t.due_date && t.due_date >= gridStart && t.due_date <= gridEnd
  );
}

async function fetchCalendarPayload(range) {
  try {
    return await api(
      `/calendar?from_date=${encodeURIComponent(range.gridStart)}&to_date=${encodeURIComponent(range.gridEnd)}`
    );
  } catch (err) {
    const msg = String(err.message || "").toLowerCase();
    if (msg.includes("not found") || msg.includes("404") || msg.includes("failed")) {
      return {
        tasks: localCalendarTasks(range.gridStart, range.gridEnd),
        google_events: [],
        google_configured: false,
        google_error: null,
        _local: true,
      };
    }
    throw err;
  }
}

async function renderCalendar() {
  state.calendarMonth = state.calendarMonth || monthStartFromToday();
  const range = calendarGridRange(state.calendarMonth);
  const el = document.getElementById("view-calendar");
  el.innerHTML = '<div class="empty">Загрузка календаря…</div>';
  try {
    const [data, gcal] = await Promise.all([
      fetchCalendarPayload(range),
      api("/calendar/google").catch(() => ({ configured: false, ical_url: "" })),
    ]);
    state.googleCalendarUrl = gcal.ical_url || "";
    if (data._local) data.google_configured = !!gcal.configured;
    const byDay = {};
    (data.tasks || []).forEach((t) => {
      byDay[t.due_date] = byDay[t.due_date] || [];
      byDay[t.due_date].push({ kind: "task", title: t.title, id: t.id });
    });
    (data.google_events || []).forEach((ev) => {
      expandGoogleEventDays(ev).forEach((day) => {
        byDay[day] = byDay[day] || [];
        byDay[day].push({ kind: "google", title: ev.title, id: `${ev.id}-${day}` });
      });
    });
    const days = [];
    let cur = range.gridStart;
    while (cur <= range.gridEnd) {
      days.push(cur);
      cur = addDaysToDateStr(cur, 1);
    }
    const cells = days.map((day) => {
      const outside = !day.startsWith(range.monthKey);
      const isToday = day === todayStr();
      const events = (byDay[day] || [])
        .slice(0, 4)
        .map(
          (ev) =>
            ev.kind === "task"
              ? `<div class="cal-event task" data-task-id="${ev.id}" title="${escapeHtml(ev.title)}">${escapeHtml(ev.title)}</div>`
              : `<div class="cal-event ${ev.kind}" title="${escapeHtml(ev.title)}">${escapeHtml(ev.title)}</div>`
        )
        .join("");
      const more = (byDay[day] || []).length > 4 ? `<div class="cal-event">+${byDay[day].length - 4}</div>` : "";
      return `<div class="cal-day${outside ? " outside" : ""}${isToday ? " today" : ""}" data-date="${day}">
        <div class="cal-day-num">${Number(day.slice(8, 10))}</div>${events}${more}
      </div>`;
    }).join("");
    const gcalErr = data.google_error
      ? `<div class="sheet-hint" style="color:#f87171;margin-bottom:12px">Google: ${escapeHtml(data.google_error)}</div>`
      : "";
    const localHint = data._local
      ? `<div class="sheet-hint" style="margin-bottom:12px;color:var(--muted)">Задачи из локальных данных. Google — после подключения в настройках.</div>`
      : "";
    const gcalBanner = data.google_configured
      ? `<div class="cal-connect-banner"><span>Google Calendar · ${(data.google_events || []).length} событий в периоде</span><button type="button" class="btn small" data-action="open-settings-calendar">Настройки</button></div>`
      : `<div class="cal-connect-banner"><span>Подключите Google Calendar, чтобы видеть события рядом с задачами</span><button type="button" class="btn small primary" data-action="open-settings-calendar">Подключить</button></div>`;
    el.innerHTML = `
      ${gcalBanner}
      ${localHint}
      ${gcalErr}
      <div class="cal-legend">
        <span class="task"><i></i> Задачи Empire</span>
        <span class="google"><i></i> Google Calendar</span>
      </div>
      <div class="cal-engine">
        <button type="button" class="cal-engine-arrow" data-action="cal-prev" title="Предыдущий месяц" aria-label="Предыдущий месяц">‹</button>
        <div class="cal-engine-center">
          <h2 class="cal-engine-title">${escapeHtml(range.monthLabel)}</h2>
          <label class="cal-engine-jump">
            <span class="cal-engine-jump-label">Перейти к месяцу</span>
            <input type="month" class="cal-month-picker" data-action="cal-pick-month" value="${escapeHtml(range.monthKey)}" aria-label="Выбор месяца">
          </label>
        </div>
        <button type="button" class="cal-engine-today" data-action="cal-today">Сегодня</button>
        <button type="button" class="cal-engine-arrow" data-action="cal-next" title="Следующий месяц" aria-label="Следующий месяц">›</button>
      </div>
      ${quickAddHtml()}
      <div class="cal-grid">
        ${WEEKDAYS.map((d) => `<div class="cal-dow">${d}</div>`).join("")}
        ${cells}
      </div>`;
    bindCalendarView(el);
  } catch (err) {
    el.innerHTML = `<div class="empty">${escapeHtml(err.message)}</div>`;
  }
}

async function renderCalendarDay() {
  const day = state.calendarDay || todayStr();
  state.calendarDay = day;
  state.calendarMonth = `${day.slice(0, 7)}-01`;
  const el = document.getElementById("view-cal-day");
  el.innerHTML = '<div class="empty">Загрузка дня…</div>';
  document.getElementById("page-title").textContent = formatDayTitle(day);
  try {
    const range = { gridStart: day, gridEnd: day };
    const data = await fetchCalendarPayload(range);
    const active = activeTasks()
      .filter((t) => t.due_date === day)
      .sort(sortByDueTime);
    const completed = state.doneTasks
      .filter((t) => (t.completed_at || "").slice(0, 10) === day || (t.due_date === day && t.status === "done"))
      .sort((a, b) => (b.completed_at || "").localeCompare(a.completed_at || ""));
    const googleEvents = (data.google_events || []).filter((ev) => expandGoogleEventDays(ev).includes(day));
    const isToday = day === todayStr();
    const gcalHtml = googleEvents.length
      ? `<div class="cal-day-events card">
          <div class="section-title">Google Calendar</div>
          ${googleEvents
            .map(
              (ev) => `<div class="cal-day-gevent">
                <span class="cal-day-gevent-dot"></span>
                <div>
                  <div class="cal-day-gevent-title">${escapeHtml(ev.title)}</div>
                  ${ev.start !== ev.end ? `<div class="hint">${escapeHtml(ev.start)}${ev.end ? ` — ${escapeHtml(ev.end)}` : ""}</div>` : ""}
                </div>
              </div>`
            )
            .join("")}
        </div>`
      : "";
    const tasksHtml = active.length
      ? renderTaskList(active, { compact: false })
      : '<div class="empty cal-day-empty">Нет открытых задач на этот день</div>';
    const doneHtml = completed.length
      ? renderCollapsibleGroup("Выполнено", completed, { open: isToday, cls: "done" })
      : "";
    el.innerHTML = `
      <button type="button" class="back-btn" data-action="cal-back-month">← Обзор месяца</button>
      <div class="cal-day-header">
        <button type="button" class="cal-engine-arrow" data-action="cal-day-prev" title="Предыдущий день" aria-label="Предыдущий день">‹</button>
        <div class="cal-day-header-center">
          <h2 class="cal-day-title">${escapeHtml(formatDayTitle(day))}</h2>
          ${isToday ? "" : `<button type="button" class="btn small cal-day-today-btn" data-action="cal-day-today">Сегодня</button>`}
        </div>
        <button type="button" class="cal-engine-arrow" data-action="cal-day-next" title="Следующий день" aria-label="Следующий день">›</button>
      </div>
      ${quickAddHtml()}
      ${gcalHtml}
      <div class="section-title">Задачи (${active.length})</div>
      ${tasksHtml}
      ${doneHtml}`;
    bindCalendarDayView(el);
    el.querySelector(".task-group.done")?.addEventListener("toggle", (e) => {
      localStorage.setItem("empire_group_done_open", e.target.open ? "1" : "0");
    });
  } catch (err) {
    el.innerHTML = `<div class="empty">${escapeHtml(err.message)}</div>`;
  }
}

function renderSearch(q) {
  const el = document.getElementById("view-search");
  const query = (q || "").trim().toLowerCase();
  let items = applyTagFilter(state.tasks);
  if (query) {
    items = items.filter(
      (t) =>
        t.title.toLowerCase().includes(query) ||
        (t.note || "").toLowerCase().includes(query) ||
        (t.tags || []).some((x) => x.toLowerCase().includes(query))
    );
  }
  items = items.filter((t) => t.status !== "done" && t.status !== "archived").sort(sortByDueTime);
  el.innerHTML = [
    tagFilterBarHtml(),
    items.length ? renderTaskList(items) : '<div class="empty">Ничего не найдено</div>',
  ].join("");
}

async function renderSomeday() {
  const el = document.getElementById("view-someday");
  if (!el) return;
  el.innerHTML = '<div class="empty">Загрузка…</div>';
  try {
    const res = await api("/tasks/someday");
    const items = res.tasks || [];
    el.innerHTML = [
      '<p class="hint">Задачи без срока — как «Когда-нибудь» в Singularity. Назначьте дату или закройте.</p>',
      items.length
        ? renderTaskList(items)
        : '<div class="empty">Пусто — сюда попадают задачи без due date</div>',
    ].join("");
  } catch (err) {
    el.innerHTML = `<div class="empty">${escapeHtml(err.message)}</div>`;
  }
}

async function renderArchive() {
  const el = document.getElementById("view-archive");
  if (!el) return;
  el.innerHTML = '<div class="empty">Загрузка…</div>';
  try {
    const res = await api("/tasks/archive");
    const items = res.tasks || [];
    el.innerHTML = [
      `<div class="card program-promo" style="margin-bottom:12px">
        <div>Архив — выполненные, убранные из истории.</div>
        <button type="button" class="btn linkish" data-action="archive-done-bulk">Перенести всю историю в архив →</button>
      </div>`,
      items.length ? renderTaskList(items) : '<div class="empty">Архив пуст</div>',
    ].join("");
    el.querySelector('[data-action="archive-done-bulk"]')?.addEventListener("click", async () => {
      if (!confirm("Перенести все выполненные задачи в архив?")) return;
      const r = await api("/tasks/archive-done", { method: "POST", body: "{}" });
      showToast(`В архив: ${r.archived || 0}`);
      await loadAll();
      renderArchive();
    });
  } catch (err) {
    el.innerHTML = `<div class="empty">${escapeHtml(err.message)}</div>`;
  }
}

function assistantBubble(role, text, extraHtml = "") {
  return `<div class="asst-msg asst-msg--${role}">
    <div class="asst-bubble">${formatPlainText(text)}${extraHtml}</div>
  </div>`;
}

function assistantTaskChips(tasks) {
  if (!tasks?.length) return "";
  return `<div class="asst-chips">${tasks
    .slice(0, 12)
    .map(
      (t) =>
        `<button type="button" class="asst-chip" data-action="open-task" data-id="${t.id}">#${t.id} ${escapeHtml(t.title)}${t.due_date ? ` · ${escapeHtml(t.due_date)}` : ""}</button>`
    )
    .join("")}</div>`;
}

async function renderAssistant() {
  const el = document.getElementById("view-assistant");
  if (!el) return;
  if (!state.assistantHistory) state.assistantHistory = [];
  const hist = state.assistantHistory
    .map((m) => assistantBubble(m.role, m.content, m.extra || ""))
    .join("");
  el.innerHTML = `
    <div class="asst-wrap">
      <p class="hint">Быстрый поиск и создание: «найди гирю», «создай завтра позвонить врачу», «когда-нибудь идея книги».</p>
      <div class="asst-feed" id="asst-feed">${hist || assistantBubble("assistant", "Чем помочь? Могу найти задачи или создать новые.")}</div>
      <form class="asst-compose" id="asst-form" autocomplete="off" data-lpignore="true">
        <input id="asst-input" type="text" name="zdk-asst" placeholder="Найти или создать задачу…" autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false" maxlength="2000" data-lpignore="true" data-1p-ignore="true" data-form-type="other" inputmode="text">
        <button class="btn primary" type="submit">Отправить</button>
      </form>
      <div class="asst-quick">
        <button type="button" class="chip" data-asst-q="найди просроченные">Просроченные</button>
        <button type="button" class="chip" data-asst-q="создай сегодня тренировка день A">Тренировка сегодня</button>
        <button type="button" class="chip" data-asst-q="перенеси выполненные в архив">В архив</button>
      </div>
    </div>`;
  const feed = el.querySelector("#asst-feed");
  const form = el.querySelector("#asst-form");
  const input = el.querySelector("#asst-input");
  const send = async (text) => {
    const msg = (text || "").trim();
    if (!msg) return;
    state.assistantHistory.push({ role: "user", content: msg });
    feed.insertAdjacentHTML("beforeend", assistantBubble("user", msg));
    input.value = "";
    feed.insertAdjacentHTML("beforeend", assistantBubble("assistant", "Думаю…"));
    feed.scrollTop = feed.scrollHeight;
    try {
      const res = await api("/assistant", {
        method: "POST",
        body: JSON.stringify({
          message: msg,
          history: state.assistantHistory.slice(0, -1).map((m) => ({ role: m.role, content: m.content })),
        }),
      });
      feed.lastElementChild?.remove();
      let extra = "";
      if (res.matches?.length) extra += assistantTaskChips(res.matches);
      if (res.created?.length) extra += `<div class="hint">Создано: ${res.created.length}</div>` + assistantTaskChips(res.created);
      if (res.completed?.length) extra += `<div class="hint">Закрыто: ${res.completed.length}</div>`;
      if (res.archived) extra += `<div class="hint">В архив: ${res.archived}</div>`;
      const reply = res.reply || "Готово.";
      state.assistantHistory.push({ role: "assistant", content: reply, extra });
      feed.insertAdjacentHTML("beforeend", assistantBubble("assistant", reply, extra));
      if (res.created?.length || res.completed?.length || res.archived) await loadAll();
    } catch (err) {
      feed.lastElementChild?.remove();
      const errText = err.message || "Ошибка";
      state.assistantHistory.push({ role: "assistant", content: errText });
      feed.insertAdjacentHTML("beforeend", assistantBubble("assistant", errText));
    }
    feed.scrollTop = feed.scrollHeight;
    hydrateNavIcons(el);
  };
  form?.addEventListener("submit", (e) => {
    e.preventDefault();
    send(input.value);
  });
  el.querySelectorAll("[data-asst-q]").forEach((btn) => {
    btn.addEventListener("click", () => send(btn.dataset.asstQ));
  });
  suppressAutofillBar(input);
  input?.focus();
}

function projectProgress(projectId) {
  const open = state.tasks.filter((t) => t.project_id === projectId);
  const done = state.doneTasks.filter((t) => t.project_id === projectId);
  const total = open.length + done.length;
  const pct = total ? Math.round((done.length / total) * 100) : 0;
  return { open: open.length, done: done.length, total, pct };
}

function linkedChecklistsForProject(projectTitle) {
  const slug = (projectTitle || "").toLowerCase();
  const key = slug.includes("gdepar")
    ? "gdepar"
    : slug.includes("pension")
      ? "pension"
      : slug.includes("финмодель") || slug.includes("финансовая")
        ? "finance"
        : slug.includes("метрик")
          ? "metrics"
          : "";
  if (!key) return [];
  return state.checklists.filter((c) => {
    const tags = (c.tags || []).join(" ").toLowerCase();
    const title = (c.title || "").toLowerCase();
    return tags.includes(key) || title.includes(key) || (c.agent_ref || "").includes(key);
  });
}

function projectHeaderHtml(p) {
  if (!p) return "";
  const prog = projectProgress(p.id);
  const linked = linkedChecklistsForProject(p.title);
  let clHtml = "";
  if (linked.length) {
    const parts = linked.map((c) => {
      const total = c.items_total || 0;
      const done = c.items_done || 0;
      const pct = total ? Math.round((done / total) * 100) : 0;
      return `${escapeHtml(c.title)} ${pct}%`;
    });
    clHtml = `<div class="project-linked-cl hint">Чеклисты: ${parts.join(" · ")}</div>`;
  }
  const desc = (p.description || "").trim();
  return `<div class="project-head card">
    <div class="project-head-row">
      <span class="project-head-pct">${prog.pct}%</span>
      <span class="project-head-stats">${prog.done}/${prog.total} закрыто · ${prog.open} открыто</span>
    </div>
    <div class="list-progress" style="margin:8px 0"><span style="width:${prog.pct}%"></span></div>
    ${desc ? `<div class="project-desc hint">${formatPlainText(desc)}</div>` : ""}
    ${clHtml}
  </div>`;
}

function renderProjects() {
  const el = document.getElementById("view-projects");
  if (!state.projects.length) {
    el.innerHTML = '<div class="empty">Проектов нет</div>';
    return;
  }
  el.innerHTML = state.projects
    .map((p) => {
      const prog = projectProgress(p.id);
      return `
    <div class="card project-row" data-project-id="${p.id}">
      <div class="task-body">
        <div class="task-title">${escapeHtml(p.title)}<span class="project-count">${prog.pct}%</span></div>
        <div class="hint">${prog.done}/${prog.total} закрыто</div>
      </div>
    </div>`;
    })
    .join("");
}

function renderProjectTasks(pid) {
  const p = state.projects.find((x) => x.id === pid);
  const tasks = applyTagFilter(state.tasks.filter((t) => t.project_id === pid && t.status !== "done")).sort(sortByDueTime);
  document.getElementById("view-project-tasks").innerHTML = `
    <button class="back-btn" data-action="back-projects">← Списки</button>
    ${projectHeaderHtml(p)}
    ${tagFilterBarHtml()}
    <div class="section-title">Задачи</div>
    ${tasks.length ? renderTaskList(tasks) : '<div class="empty">Нет открытых задач</div>'}`;
}

function renderDone() {
  const el = document.getElementById("view-done");
  const items = state.doneTasks.slice(0, 100);
  el.innerHTML = items.length
    ? renderTaskList(items)
    : '<div class="empty">Выполненных задач нет</div>';
}

async function importTicktickFile(file, { fresh = false } = {}) {
  const fd = new FormData();
  fd.append("file", file);
  const q = fresh ? "?fresh=1" : "";
  const res = await fetch(`${API_BASE}/import/ticktick${q}`, {
    method: "POST",
    headers: { "X-Planning-Token": token() },
    body: fd,
  });
  if (!res.ok) {
    if (res.status === 413) {
      const mb = (file.size / (1024 * 1024)).toFixed(1);
      throw new Error(`Файл слишком большой (${mb} МБ). Сообщите админу — нужен лимит nginx.`);
    }
    const body = await res.json().catch(() => ({}));
    const detail = body.detail;
    const msg = Array.isArray(detail)
      ? detail.map((d) => d.msg || d).join("; ")
      : detail || `import failed (${res.status})`;
    throw new Error(msg);
  }
  return res.json();
}

function requestNotify() {
  if (!("Notification" in window)) {
    showToast("Уведомления не поддерживаются");
    return Promise.resolve();
  }
  return Notification.requestPermission().then(async (p) => {
    if (p !== "granted") {
      showToast("Разрешение не дано");
      return;
    }
    try {
      const pushed = await subscribeWebPush();
      showToast(pushed ? "Push-напоминания включены" : "Уведомления включены");
    } catch (err) {
      showToast(err.message === "push_not_configured" ? "Уведомления в приложении" : "Push: " + err.message);
    }
  });
}

async function subscribeWebPush() {
  if (!("serviceWorker" in navigator) || !("PushManager" in window)) return false;
  // Отдельный push-SW без fetch — не глушит загрузку PWA.
  // Push SW только на /tasks/; на /x/ не трогаем SW.
  if (TASKS_MOUNT !== "/tasks") return false;
  const reg = await navigator.serviceWorker.register(ASSET_BASE + "/sw-push.js?v=1", {
    scope: "/tasks/",
    updateViaCache: "none",
  });
  await Promise.race([
    reg.update().catch(() => {}),
    new Promise((r) => setTimeout(r, 2000)),
  ]);
  const ready = await Promise.race([
    navigator.serviceWorker.ready,
    new Promise((_, rej) => setTimeout(() => rej(new Error("sw_ready_timeout")), 5000)),
  ]);
  const res = await fetch(`${API_BASE}/push/vapid-public-key`);
  if (!res.ok) throw new Error("push_not_configured");
  const { public_key: publicKey } = await res.json();
  if (!publicKey) throw new Error("push_not_configured");
  let sub = await ready.pushManager.getSubscription();
  if (!sub) {
    sub = await ready.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(publicKey),
    });
  }
  await api("/push/subscribe", { method: "POST", body: JSON.stringify(sub.toJSON()) });
  return true;
}

async function ensurePushSubscription() {
  if (!("Notification" in window) || Notification.permission !== "granted") return;
  try {
    await subscribeWebPush();
  } catch (_) {}
}

function openSettings(section = "notifications") {
  if (state.currentView !== "settings") {
    state.settingsReturnView = state.currentView || "today";
  }
  state.settingsSection = section;
  showView("settings");
}

function isPushOn() {
  return typeof Notification !== "undefined" && Notification.permission === "granted";
}

function btn3dToggleHtml(action, on, { onLabel = "Вкл", offLabel = "Выкл", wide = false } = {}) {
  const cls = `btn-3d-toggle${wide ? " btn-3d-toggle--wide" : ""}${on ? " on" : ""}`;
  return `<button type="button" class="${cls}" data-action="${action}" aria-pressed="${on}">${on ? onLabel : offLabel}</button>`;
}

function notifyPermissionLabel() {
  if (!("Notification" in window)) return "Не поддерживается";
  const map = { granted: "Разрешены", denied: "Запрещены", default: "Не запрошены" };
  return map[Notification.permission] || Notification.permission;
}

function settingsPanelHtml(section) {
  if (section === "notifications") {
    const hour = Number(localStorage.getItem("empire_briefing_hour") || "8");
    const pushOn = isPushOn();
    const hourOpts = Array.from({ length: 17 }, (_, i) => i + 6)
      .map((h) => `<option value="${h}"${h === hour ? " selected" : ""}>${String(h).padStart(2, "0")}:00</option>`)
      .join("");
    return `
      <h2>Уведомления</h2>
      <p class="settings-desc">Напоминания по задачам, push с сервера и утренний брифинг с фокусом дня.</p>
      <div class="settings-card">
        <div class="settings-row">
          <div><label>Push-напоминания</label><div class="hint">${escapeHtml(notifyPermissionLabel())}</div></div>
          ${btn3dToggleHtml("settings-enable-push", pushOn, {
            onLabel: "Push включён",
            offLabel: "Включить push",
            wide: true,
          })}
        </div>
        <div class="settings-row">
          <div><label>Брифинг «фокус дня»</label><div class="hint">Локальное уведомление в выбранный час</div></div>
          <select id="settings-briefing-hour" class="settings-input">${hourOpts}</select>
        </div>
      </div>
      <p class="settings-desc">Напоминания о замерах настраиваются в разделе <b>Здоровье → Замеры</b>.</p>`;
  }
  if (section === "calendar") {
    return `
      <h2>Подписка на календарь</h2>
      <p class="settings-desc">Подключите Google Calendar через секретную ссылку iCal — события появятся в обзоре месяца рядом с задачами Empire.</p>
      <div class="settings-card">
        <div class="sheet-hint" style="margin-bottom:12px">1. Откройте <b>Google Calendar</b> на компьютере<br>
        2. Настройки нужного календаря → <b>Интеграция календаря</b><br>
        3. Скопируйте <b>Секретный адрес в формате iCal</b></div>
        <input id="settings-gcal-url" class="settings-input" type="url" placeholder="https://calendar.google.com/calendar/ical/..." value="${escapeHtml(state.googleCalendarUrl)}" autocomplete="off">
        <div style="display:flex;gap:8px;margin-top:12px;flex-wrap:wrap">
          <button type="button" class="btn primary small" data-action="settings-save-gcal">Сохранить</button>
          <button type="button" class="btn small" data-action="settings-refresh-gcal">Обновить в календаре</button>
          <button type="button" class="btn small danger" data-action="settings-disconnect-gcal">Отключить</button>
        </div>
        <div id="settings-gcal-status" class="hint" style="margin-top:10px"></div>
      </div>`;
  }
  if (section === "appearance") {
    const doneOpen = localStorage.getItem("empire_group_done_open") !== "0";
    const projectsOpen = localStorage.getItem("empire_projects_open") !== "0";
    const fontPct = getFontScale();
    return `
      <h2>Внешний вид</h2>
      <p class="settings-desc">Размер текста и поведение списков.</p>
      <div class="settings-card">
        <div class="settings-row" style="flex-direction:column;align-items:stretch;gap:14px">
          <div>
            <label>Размер текста</label>
            <div class="hint">Как в Telegram — двигай ползунок</div>
          </div>
          <div class="font-scale-block">
            <div class="font-scale-row">
              <span class="font-scale-a-sm" aria-hidden="true">A</span>
              <input id="settings-font-scale" class="font-scale-slider" type="range"
                min="${FONT_SCALE_MIN}" max="${FONT_SCALE_MAX}" step="5" value="${fontPct}"
                aria-label="Размер текста" />
              <span class="font-scale-a-lg" aria-hidden="true">A</span>
            </div>
            <div id="settings-font-scale-value" class="font-scale-value">${fontPct}%</div>
            <div id="settings-font-preview" class="font-scale-preview">Так выглядит текст задач</div>
            <button type="button" class="btn small" data-action="settings-font-reset">По умолчанию (100%)</button>
          </div>
        </div>
        <div class="settings-row">
          <div><label>Секция «Выполнено» открыта</label><div class="hint">На экране «Сегодня»</div></div>
          ${btn3dToggleHtml("settings-toggle-done-open", doneOpen)}
        </div>
        <div class="settings-row">
          <div><label>Проекты развёрнуты</label><div class="hint">Блок «Проекты» в боковом меню</div></div>
          ${btn3dToggleHtml("settings-toggle-projects-open", projectsOpen)}
        </div>
        <div class="settings-row">
          <div><label>Сброс ширины колонок</label><div class="hint">Меню слева и панель задачи справа</div></div>
          <button type="button" class="btn small" data-action="settings-reset-columns">По умолчанию</button>
        </div>
      </div>`;
  }
  if (section === "data") {
    return `
      <h2>Данные</h2>
      <p class="settings-desc">Импорт TickTick. Тренировки, замеры и программа — в отдельном разделе «Здоровье», не удаляются.</p>
      <div class="settings-card">
        <div class="settings-row">
          <div><label>Сброс и импорт TickTick CSV</label><div class="hint" id="ticktick-purge-status">Загрузка…</div></div>
          <button type="button" class="btn small primary" data-action="settings-fresh-import-ticktick" id="btn-fresh-import-ticktick">Выбрать CSV…</button>
          <input type="file" id="settings-ticktick-fresh-csv" accept=".csv,text/csv" hidden>
        </div>
        <div class="settings-row">
          <div><label>Удалить только задачи и проекты</label><div class="hint">Чеклисты, цели, тренировки и замеры остаются</div></div>
          <button type="button" class="btn small danger" data-action="settings-purge-tasks">Очистить задачи</button>
        </div>
        <div class="settings-row">
          <div><label>Дубликаты задач</label><div class="hint" id="dedupe-status">Одинаковое название и дата — лишние удаляются, остаётся задача с повтором и заметкой</div></div>
          <div style="display:flex;gap:8px;flex-wrap:wrap;flex-shrink:0">
            <button type="button" class="btn small" data-action="settings-scan-dupes">Проверить</button>
            <button type="button" class="btn small danger" data-action="settings-dedupe-tasks">Удалить дубликаты</button>
          </div>
        </div>
        <div class="settings-row">
          <div><label>Очистить офлайн-кэш</label><div class="hint">Снимок задач и кэш service worker</div></div>
          <button type="button" class="btn small danger" data-action="settings-clear-cache">Очистить</button>
        </div>
      </div>`;
  }
  return `
    <h2>О приложении</h2>
    <p class="settings-desc">Задачник — задачи, календарь, здоровье и ИИ-ассистент на neverretire.ru.</p>
    <div class="settings-card">
      <div class="settings-row"><label>Версия</label><span>${escapeHtml(APP_VER)}</span></div>
      <div class="settings-row"><label>Адрес</label><a href="${TASKS_MOUNT}/" style="color:var(--accent)">neverretire.ru${TASKS_MOUNT}</a></div>
      <div class="settings-row"><label>Android APK</label><span class="hint">android/zadachnik/zadachnik-debug.apk на VPS</span></div>
      <div class="settings-row"><label>Аккаунт</label><span class="hint">Один токен доступа — без отдельного профиля</span></div>
      <p class="hint">Виджет: рабочий стол → Виджеты → «Задачник · 7 дней». Тап по заголовку меняет фильтр. Лонгтап иконки — новая задача / ИИ / когда-нибудь.</p>
    </div>`;
}

async function loadGoogleSettingsStatus() {
  try {
    const gcal = await api("/calendar/google");
    state.googleCalendarUrl = gcal.ical_url || "";
    return gcal;
  } catch {
    return { configured: false, ical_url: "" };
  }
}

async function renderSettings() {
  const el = document.getElementById("view-settings");
  const section = state.settingsSection || "notifications";
  const nav = SETTINGS_SECTIONS.map(
    (s) =>
      `<button type="button" class="settings-nav-item${s.id === section ? " active" : ""}" data-settings-section="${s.id}">
        <span class="settings-nav-icon">${window.NavIcons ? NavIcons.badge(s.icon) : ""}</span>${escapeHtml(s.title)}
      </button>`
  ).join("");
  el.innerHTML = `<div class="settings-layout">
    <nav class="settings-nav" aria-label="Разделы настроек">${nav}</nav>
    <div class="settings-body" id="settings-panel">${settingsPanelHtml(section)}</div>
  </div>`;
  if (section === "calendar") {
    const gcal = await loadGoogleSettingsStatus();
    const input = el.querySelector("#settings-gcal-url");
    if (input && gcal.ical_url) input.value = gcal.ical_url;
    const status = el.querySelector("#settings-gcal-status");
    if (status) {
      status.textContent = gcal.configured ? "Google Calendar подключён" : "Не подключён";
    }
  }
  if (section === "data") {
    loadTicktickStats(el);
  }
  bindSettings(el);
}

async function loadTicktickStats(root) {
  const status = root.querySelector("#ticktick-purge-status");
  if (!status) return;
  try {
    const stats = await api("/import/ticktick/stats?scope=tasks");
    const parts = [];
    if (stats.tasks) parts.push(`${stats.tasks} задач`);
    if (stats.projects) parts.push(`${stats.projects} проектов`);
    status.textContent = stats.count
      ? `Сейчас: ${parts.join(", ")}. Импорт удалит их и загрузит CSV заново (1–3 мин)`
      : "Задач нет — можно импортировать CSV из TickTick";
  } catch {
    status.textContent = "Не удалось загрузить статистику";
  }
}

function bindSettings(root) {
  root.querySelectorAll("[data-settings-section]").forEach((btn) => {
    btn.addEventListener("click", () => {
      state.settingsSection = btn.dataset.settingsSection;
      renderSettings();
    });
  });
  root.querySelector('[data-action="settings-enable-push"]')?.addEventListener("click", (e) => {
    const btn = e.currentTarget;
    if (isPushOn()) {
      btn.classList.add("on");
      btn.setAttribute("aria-pressed", "true");
      btn.textContent = "Push включён";
      return;
    }
    requestNotify().then(() => renderSettings());
  });
  root.querySelector("#settings-briefing-hour")?.addEventListener("change", (e) => {
    localStorage.setItem("empire_briefing_hour", String(e.target.value));
    showToast("Час брифинга сохранён");
  });
  root.querySelector('[data-action="settings-toggle-done-open"]')?.addEventListener("click", (e) => {
    const btn = e.currentTarget;
    const on = !btn.classList.contains("on");
    btn.classList.toggle("on", on);
    btn.setAttribute("aria-pressed", on);
    btn.textContent = on ? "Вкл" : "Выкл";
    localStorage.setItem("empire_group_done_open", on ? "1" : "0");
    renderToday();
  });
  const fontSlider = root.querySelector("#settings-font-scale");
  fontSlider?.addEventListener("input", (e) => {
    applyFontScale(e.target.value);
  });
  root.querySelector('[data-action="settings-font-reset"]')?.addEventListener("click", () => {
    applyFontScale(FONT_SCALE_DEFAULT);
    if (fontSlider) fontSlider.value = String(FONT_SCALE_DEFAULT);
    showToast("Размер текста сброшен");
  });
  root.querySelector('[data-action="settings-toggle-projects-open"]')?.addEventListener("click", (e) => {
    const btn = e.currentTarget;
    const on = !btn.classList.contains("on");
    btn.classList.toggle("on", on);
    btn.setAttribute("aria-pressed", on);
    btn.textContent = on ? "Вкл" : "Выкл";
    localStorage.setItem("empire_projects_open", on ? "1" : "0");
    const wrap = document.querySelector(".nav-projects-wrap");
    if (wrap) wrap.open = on;
  });
  root.querySelector('[data-action="settings-reset-columns"]')?.addEventListener("click", () => {
    Object.keys(COLUMN_WIDTH_KEYS).forEach((k) => localStorage.removeItem(COLUMN_WIDTH_KEYS[k]));
    loadColumnWidths();
    showToast("Ширина колонок сброшена");
  });
  root.querySelector('[data-action="settings-purge-tasks"]')?.addEventListener("click", async () => {
    try {
      const stats = await api("/import/ticktick/stats?scope=tasks");
      if (!stats.tasks && !stats.projects) {
        showToast("Задач и проектов нет");
        return;
      }
      const parts = [];
      if (stats.tasks) parts.push(`${stats.tasks} задач`);
      if (stats.projects) parts.push(`${stats.projects} проектов`);
      if (!confirm(`Удалить ${parts.join(" и ")}? Тренировки, замеры и чеклисты не трогаем.`)) return;
      const res = await api("/import/ticktick/purge?scope=tasks", { method: "POST" });
      showToast(`Удалено: ${res.tasks} задач, ${res.projects} проектов`);
      await loadAll();
      renderSettings();
    } catch (err) {
      showToast(err.message);
    }
  });
  const freshCsv = root.querySelector("#settings-ticktick-fresh-csv");
  root.querySelector('[data-action="settings-fresh-import-ticktick"]')?.addEventListener("click", () => {
    freshCsv?.click();
  });
  freshCsv?.addEventListener("change", async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const btn = root.querySelector("#btn-fresh-import-ticktick");
    try {
      const stats = await api("/import/ticktick/stats?scope=tasks");
      const parts = [];
      if (stats.tasks) parts.push(`${stats.tasks} задач`);
      if (stats.projects) parts.push(`${stats.projects} проектов`);
      const msg = stats.tasks || stats.projects
        ? `Удалить ${parts.join(" и ")} и импортировать «${file.name}»? (1–3 мин, не закрывайте вкладку)`
        : `Импортировать «${file.name}»? (1–3 мин)`;
      if (!confirm(msg)) return;
      if (btn) { btn.disabled = true; btn.textContent = "Импорт…"; }
      showToast("Импорт CSV… подождите 1–3 минуты");
      const r = await importTicktickFile(file, { fresh: true });
      showToast(`Готово: +${r.imported || 0} задач, проектов ${r.projects || 0}`);
      loadAll().catch((err) => showToast(err.message));
      renderSettings();
    } catch (err) {
      showToast(String(err.message));
    } finally {
      if (btn) { btn.disabled = false; btn.textContent = "Выбрать CSV…"; }
    }
    e.target.value = "";
  });
  root.querySelector('[data-action="settings-scan-dupes"]')?.addEventListener("click", async () => {
    try {
      const preview = await api("/tasks/duplicates");
      const status = root.querySelector("#dedupe-status");
      if (status) {
        status.textContent = preview.to_remove
          ? `Найдено ${preview.group_count} групп, лишних задач: ${preview.to_remove}`
          : "Дубликатов не найдено";
      }
      if (!preview.to_remove) showToast("Дубликатов нет");
      else showToast(`Лишних задач: ${preview.to_remove}`);
    } catch (err) {
      showToast(err.message);
    }
  });
  root.querySelector('[data-action="settings-dedupe-tasks"]')?.addEventListener("click", async () => {
    try {
      const preview = await api("/tasks/duplicates");
      if (!preview.to_remove) {
        showToast("Дубликатов не найдено");
        return;
      }
      if (!confirm(`Удалить ${preview.to_remove} дубликатов в ${preview.group_count} группах?`)) return;
      const res = await api("/tasks/deduplicate", { method: "POST" });
      showToast(`Удалено: ${res.removed}`);
      await loadAll();
      renderSettings();
    } catch (err) {
      showToast(err.message);
    }
  });
  root.querySelector('[data-action="settings-clear-cache"]')?.addEventListener("click", async () => {
    if (!confirm("Очистить офлайн-кэш и снимок данных?")) return;
    localStorage.removeItem(OFFLINE_SNAPSHOT_KEY);
    if ("caches" in window) {
      const keys = await caches.keys();
      await Promise.all(keys.map((k) => caches.delete(k)));
    }
    showToast("Кэш очищен");
  });
  root.querySelector('[data-action="settings-save-gcal"]')?.addEventListener("click", async () => {
    const url = (root.querySelector("#settings-gcal-url")?.value || "").trim();
    try {
      await api("/calendar/google", { method: "PUT", body: JSON.stringify({ ical_url: url || null }) });
      state.googleCalendarUrl = url;
      showToast(url ? "Google Calendar подключён" : "Ссылка удалена");
      await renderSettings();
      if (state.currentView === "calendar") renderCalendar();
    } catch (err) {
      showToast(err.message);
    }
  });
  root.querySelector('[data-action="settings-disconnect-gcal"]')?.addEventListener("click", async () => {
    try {
      await api("/calendar/google", { method: "PUT", body: JSON.stringify({ ical_url: null }) });
      state.googleCalendarUrl = "";
      showToast("Google Calendar отключён");
      await renderSettings();
      if (state.currentView === "calendar") renderCalendar();
    } catch (err) {
      showToast(err.message);
    }
  });
  root.querySelector('[data-action="settings-refresh-gcal"]')?.addEventListener("click", () => {
    if (state.currentView === "calendar") renderCalendar();
    else showToast("Откройте календарь для обновления");
  });
}

function updateChromeForView(name) {
  const isSettings = name === "settings";
  document.getElementById("btn-mobile-menu")?.classList.toggle("hidden", isSettings);
  document.getElementById("btn-overflow")?.classList.toggle("hidden", isSettings);
  syncRestTimerChrome(name);
  document.querySelectorAll(".icon-rail-btn[data-view]").forEach((btn) => {
    const match = btn.dataset.view === name || (name === "cal-day" && btn.dataset.view === "calendar");
    btn.classList.toggle("active", !isSettings && match);
  });
  document.querySelectorAll("#btn-settings-rail, #btn-settings").forEach((btn) => {
    btn.classList.toggle("active", isSettings);
  });
  const backBtn = document.getElementById("btn-back-view");
  if (backBtn) backBtn.classList.toggle("hidden", !isSettings);
}

function renderLists() {
  const el = document.getElementById("view-lists");
  if (!state.checklists.length) {
    el.innerHTML = '<div class="empty">Чеклисты от агента появятся здесь</div>';
    return;
  }
  el.innerHTML = state.checklists
    .map((cl) => {
      const total = cl.items_total || 0;
      const done = cl.items_done || 0;
      const pct = total ? Math.round((done / total) * 100) : 0;
      return `
      <div class="card list-row" data-checklist-id="${cl.id}">
        <div style="padding:14px;width:100%">
          <div class="task-title">${escapeHtml(cl.title)}</div>
          <div class="list-progress"><span style="width:${pct}%"></span></div>
          <div class="task-meta">${done}/${total}</div>
        </div>
      </div>`;
    })
    .join("");
}

async function renderDetail(id) {
  const cl = await api(`/checklists/${id}`);
  const items = (cl.items || [])
    .map(
      (item) => `
      <div class="check-item">
        <button type="button" class="check${item.status === "done" ? " done" : ""}" data-action="toggle-item" data-id="${item.id}" data-cl="${cl.id}">${item.status === "done" ? "✓" : ""}</button>
        <div class="task-body"><div class="task-title${item.status === "done" ? " done-text" : ""}">${escapeHtml(item.title)}</div></div>
      </div>`
    )
    .join("");
  document.getElementById("view-detail").innerHTML = `
    <button class="back-btn" data-action="back-lists">← Чеклисты</button>
    <div class="card"><div class="detail-header"><h2>${escapeHtml(cl.title)}</h2></div>${items}</div>`;
}

function renderMetrics() {
  const s = state.summary;
  const h = state.healthSummary;
  let html = `
    <div class="metric"><strong>${s.tasks_todo || 0}</strong>к выполнению</div>
    <div class="metric"><strong>${s.tasks_doing || 0}</strong>в работе</div>`;
  if (h.latest_weight_kg) {
    html += `<div class="metric"><strong>${formatNum(h.latest_weight_kg)}</strong>кг</div>`;
  }
  if (state.currentView === "measurements") {
    html += `<div class="metric"><strong>${h.measurements_count || 0}</strong>замеров</div>`;
  } else if (state.currentView === "workouts") {
    html += `<div class="metric"><strong>${h.workouts_count || 0}</strong>тренировок</div>`;
  } else if (state.currentView === "health-stats") {
    html += `<div class="metric"><strong>${formatNum(h.latest_weight_kg)}</strong>кг</div>`;
  } else if (state.currentView === "task-stats") {
    html += `<div class="metric"><strong>${state.taskStats?.completed ?? "—"}</strong>сделано</div>`;
  }
  document.getElementById("metrics").innerHTML = html;
}

function fillProjectSelect() {
  const sel = document.getElementById("tf-project");
  sel.innerHTML = '<option value="">—</option>';
  state.projects.forEach((p) => {
    sel.innerHTML += `<option value="${p.id}">${escapeHtml(p.title)}</option>`;
  });
}

async function openSheet(task = null) {
  closeMeasurementSheet();
  closeWorkoutSheet();
  if (task?.id) {
    try {
      task = await api(`/tasks/${task.id}`);
    } catch (_) {
      /* keep list row */
    }
  }
  state.editingId = task?.id || null;
  state.creatingTask = !task?.id;
  const sheet = document.getElementById("task-sheet");
  sheet.classList.remove("hidden");
  sheet.classList.remove("detail-empty");
  sheet.setAttribute("aria-hidden", "false");
  document.getElementById("task-detail-empty")?.setAttribute("aria-hidden", "true");
  document.getElementById("tf-id").value = task?.id || "";
  document.getElementById("tf-title").value = task?.title || "";
  document.getElementById("tf-note").value = task?.note || "";
  document.getElementById("tf-due-date").value = task?.due_date || "";
  document.getElementById("tf-due-time").value = task?.due_time || "";
  document.getElementById("tf-priority").value = String(task?.priority ?? 0);
  document.getElementById("tf-project").value = task?.project_id || "";
  setSheetTags(task?.tags || []);
  document.getElementById("tf-repeat").value = repeatKeyFromObj(task?.repeat_rule_obj);
  document.getElementById("tf-remind").value = task ? remindOffsetFromTask(task) : "";
  document.getElementById("tf-delete").classList.toggle("hidden", !task?.id);
  document.getElementById("subtasks-block").classList.toggle("hidden", !task?.id);
  const chk = document.getElementById("tf-complete");
  chk.className = "check large" + (task?.status === "done" ? " done" : "");
  chk.textContent = task?.status === "done" ? "✓" : "";
  if (task?.id) loadSubtasks(task.id);
  else document.getElementById("subtasks-list").innerHTML = "";
  state.pendingTaskImage = null;
  state.pendingTaskImageRemove = false;
  renderTaskImagePreview(task);
  syncSheetMetaDisplay();
  renderTagSuggestions("");
  const details = document.getElementById("sheet-fields-details");
  if (details && !usesDesktopTaskSplit()) {
    details.open = state.creatingTask;
  }
  const titleEl = document.getElementById("tf-title");
  suppressAutofillBar(titleEl);
  titleEl?.focus();
  syncSplitTaskLayout();
}

function closeSheet() {
  const sheet = document.getElementById("task-sheet");
  state.editingId = null;
  state.creatingTask = false;
  state.pendingTaskImage = null;
  state.pendingTaskImageRemove = false;
  if (usesDesktopTaskSplit()) {
    sheet.classList.remove("hidden");
    sheet.classList.add("detail-empty");
    sheet.setAttribute("aria-hidden", "true");
    document.getElementById("task-detail-empty")?.setAttribute("aria-hidden", "false");
  } else {
    sheet.classList.add("hidden");
    sheet.classList.remove("detail-empty");
    sheet.setAttribute("aria-hidden", "true");
  }
  syncSplitTaskLayout();
}

async function loadSubtasks(parentId) {
  const data = await api(`/tasks/${parentId}`);
  const list = document.getElementById("subtasks-list");
  list.innerHTML = (data.subtasks || []).map((t) => taskRowHtml(t, { compact: true })).join("")
    || '<div class="empty" style="padding:8px">Нет подзадач</div>';
}

function showView(name) {
  closeAllSheets();
  if (name === "settings") {
    state.currentView = "settings";
    document.getElementById("app")?.classList.add("settings-mode");
    document.querySelectorAll(".view").forEach((v) => v.classList.remove("active"));
    document.getElementById("view-settings").classList.add("active");
    document.querySelectorAll(".nav-row[data-view], .nav-item[data-view], .drawer-row[data-view]").forEach((n) => {
      n.classList.remove("active");
    });
    document.getElementById("page-title").textContent = TITLES.settings;
    document.getElementById("search-bar").classList.add("hidden");
    document.getElementById("btn-add-header").classList.add("hidden");
    document.getElementById("fab-add").classList.add("hidden");
    document.getElementById("fab-ai")?.classList.add("hidden");
    document.getElementById("metrics")?.classList.add("hidden");
    updateChromeForView("settings");
    renderSettings();
    return;
  }
  document.getElementById("app")?.classList.remove("settings-mode");
  state.currentView = name;
  if (HEALTH_VIEWS.has(name)) {
    state.section = "health";
    state.healthView = name;
    state.inboxOnly = false;
  } else if (TASK_VIEWS.has(name)) {
    state.section = "tasks";
    state.taskView = name;
    if (name !== "all-tasks") state.inboxOnly = false;
  }
  document.querySelectorAll(".view").forEach((v) => v.classList.remove("active"));
  document.querySelectorAll(".nav-row[data-view], .nav-item[data-view], .drawer-row[data-view]").forEach((n) => {
    const match = n.dataset.view === name || (name === "cal-day" && n.dataset.view === "calendar");
    n.classList.toggle("active", match);
  });
  syncTabbar();
  const map = {
    today: "view-today",
    week: "view-week",
    calendar: "view-calendar",
    "cal-day": "view-cal-day",
    matrix: "view-matrix",
    "all-tasks": "view-all-tasks",
    search: "view-search",
    projects: "view-projects",
    lists: "view-lists",
    done: "view-done",
    someday: "view-someday",
    archive: "view-archive",
    assistant: "view-assistant",
    "task-stats": "view-task-stats",
    insights: "view-insights",
    "finance-model": "view-finance-model",
    measurements: "view-measurements",
    workouts: "view-workouts",
    program: "view-program",
    "health-stats": "view-health-stats",
    detail: "view-detail",
    "project-tasks": "view-project-tasks",
    settings: "view-settings",
  };
  document.getElementById(map[name] || "view-today").classList.add("active");
  document.getElementById("page-title").textContent =
    name === "cal-day"
      ? formatDayTitle(state.calendarDay || todayStr())
      : name === "all-tasks" && state.inboxOnly
        ? "Входящие"
        : name === "all-tasks" && state.tagFilter
          ? `#${state.tagFilter}`
          : (TITLES[name] || "Empire");
  const mainEl = document.getElementById("main");
  if (mainEl) mainEl.scrollTop = 0;
  document.getElementById("search-bar").classList.toggle("hidden", name !== "search");
  document.getElementById("metrics")?.classList.toggle("hidden", name === "settings");
  const addBtn = document.getElementById("btn-add-header");
  const isHealth = HEALTH_VIEWS.has(name);
  const isStats = name === "task-stats" || name === "health-stats" || name === "insights";
  const isPipelineHub = name === "finance-model";
  addBtn.classList.toggle("hidden", isStats || isPipelineHub);
  updateChromeForView(name);
  if (!isStats && !isPipelineHub) {
    if (name === "measurements") addBtn.textContent = "+ Замер";
    else if (name === "workouts") addBtn.textContent = "+ Тренировка";
    else if (name === "program") addBtn.textContent = "Дневник";
    else addBtn.textContent = "+ Задача";
  }
  const showFab =
    !isStats &&
    !isPipelineHub &&
    name !== "assistant" &&
    (isHealth ? ["measurements"].includes(name) : !["settings", "task-stats", "insights", "program", "health-stats", "workouts"].includes(name));
  // На тренировках/программе FAB мешает таймерам отдыха и удержания
  const showAiFab =
    !isGymApp() &&
    !isHealth &&
    !isStats &&
    !isPipelineHub &&
    !["settings", "assistant", "program", "workouts"].includes(name);
  document.getElementById("fab-add").classList.toggle("hidden", !showFab);
  document.getElementById("fab-ai")?.classList.toggle("hidden", !showAiFab);
  document.getElementById("fab-add").setAttribute(
    "aria-label",
    name === "measurements" ? "Новый замер" : "Новая задача"
  );
  if (name === "all-tasks") renderAllTasks();
  if (name === "week") renderWeek();
  if (name === "calendar") renderCalendar();
  if (name === "cal-day") renderCalendarDay();
  if (name === "matrix") renderMatrix();
  if (name === "someday") renderSomeday();
  if (name === "archive") renderArchive();
  if (name === "assistant") renderAssistant();
  if (name === "measurements") renderMeasurements();
  if (name === "workouts") renderWorkouts();
  if (name === "program") renderWorkoutProgram();
  if (name === "insights") renderInsights();
  if (name === "finance-model") renderFinanceModel();
  if (name === "task-stats") renderTaskStats();
  if (name === "health-stats") renderHealthStats();
  renderMetrics();
  renderSidebarNav();
  renderMobileDrawer();
  syncSplitTaskLayout();
  syncTabbar();
}

function showSection(section) {
  if (section === "tasks") showView(state.taskView || "today");
  else if (section === "health") showView(state.healthView || "measurements");
}

async function loadAll() {
  try {
    if (isGymApp()) {
      const [measRes, workRes, bodySum, summary] = await Promise.all([
        api("/measurements"),
        api("/workouts"),
        api("/body/summary"),
        api("/summary").catch(() => ({})),
      ]);
      state.tasks = [];
      state.doneTasks = [];
      state.checklists = [];
      state.projects = [];
      state.summary = summary || {};
      state.measurements = measRes.measurements || [];
      state.workouts = workRes.workouts || [];
      state.healthSummary = bodySum || {};
      state.healthSettings = bodySum.settings || state.healthSettings;
      state.exercises = bodySum.exercises || {};
      saveOfflineSnapshot();
      fillExerciseSelect();
      renderSidebarNav();
      renderMetrics();
      return;
    }
    const [tasksRes, doneRes, listsRes, projRes, summary, measRes, workRes, bodySum] = await Promise.all([
      api("/tasks"),
      api("/tasks?include_done=true&status=done"),
      api("/checklists"),
      api("/projects"),
      api("/summary"),
      api("/measurements"),
      api("/workouts"),
      api("/body/summary"),
    ]);
    state.tasks = tasksRes.tasks || [];
    state.doneTasks = doneRes.tasks || [];
    state.checklists = listsRes.checklists || [];
    state.projects = projRes.projects || [];
    state.summary = summary;
    state.measurements = measRes.measurements || [];
    state.workouts = workRes.workouts || [];
    state.healthSummary = bodySum || {};
    state.healthSettings = bodySum.settings || state.healthSettings;
    state.exercises = bodySum.exercises || {};
    saveOfflineSnapshot();
  } catch (e) {
    if (e.message === "auth") throw e;
    const snap = (() => {
      try {
        return JSON.parse(localStorage.getItem(OFFLINE_SNAPSHOT_KEY) || "null");
      } catch {
        return null;
      }
    })();
    if (snap?.tasks || snap?.measurements || snap?.workouts) {
      applyOfflineSnapshot(snap);
      renderSidebarNav();
      if (!isGymApp()) {
        renderToday();
        renderMetrics();
      } else {
        renderMetrics();
      }
      showToast("Офлайн — сохранённые данные");
      return;
    }
    throw e;
  }
  fillProjectSelect();
  fillExerciseSelect();
  const safe = (label, fn) => {
    try {
      fn();
    } catch (err) {
      console.error("loadAll render failed:", label, err);
      showToast?.(`Ошибка экрана: ${label}`);
    }
  };
  safe("sidebar", () => renderSidebarNav());
  safe("metrics", () => renderMetrics());
  safe("today", () => renderToday());
  safe("week", () => renderWeek());
  safe("search", () => renderSearch(document.getElementById("search-input")?.value || ""));
  safe("projects", () => renderProjects());
  safe("lists", () => renderLists());
  safe("done", () => renderDone());
  if (state.currentView === "all-tasks") safe("all-tasks", () => renderAllTasks());
  if (state.currentView === "week") safe("week2", () => renderWeek());
  if (state.currentView === "calendar") safe("calendar", () => renderCalendar());
  if (state.currentView === "cal-day") safe("cal-day", () => renderCalendarDay());
  if (state.currentView === "matrix") safe("matrix", () => renderMatrix());
  if (state.currentView === "measurements") safe("measurements", () => renderMeasurements());
  if (state.currentView === "workouts") safe("workouts", () => renderWorkouts());
  if (state.currentView === "task-stats") {
    try {
      await renderTaskStats();
    } catch (err) {
      console.error("loadAll render failed: task-stats", err);
    }
  }
  if (state.currentView === "health-stats") {
    try {
      await renderHealthStats();
    } catch (err) {
      console.error("loadAll render failed: health-stats", err);
    }
  }
  if (state.projectFilter) safe("project-tasks", () => renderProjectTasks(state.projectFilter));
  try {
    checkReminders();
    checkHealthReminders();
  } catch (_) {}
}

async function toggleTask(id, status) {
  if (status !== "done") {
    const res = await api(`/tasks/${id}/complete`, { method: "POST" });
    if (res.spawned) showToast("Следующее повторение создано");
  } else {
    await api(`/tasks/${id}`, { method: "PATCH", body: JSON.stringify({ status: "todo" }) });
  }
  await loadAll();
}

async function saveTaskForm(e) {
  e.preventDefault();
  const id = document.getElementById("tf-id").value;
  const dueDate = document.getElementById("tf-due-date").value || null;
  const dueTime = document.getElementById("tf-due-time").value || null;
  const repeatKey = document.getElementById("tf-repeat").value;
  const remindOff = document.getElementById("tf-remind").value;
  const tags = getSheetTags();
  const body = {
    title: document.getElementById("tf-title").value.trim(),
    note: document.getElementById("tf-note").value.trim() || null,
    due_date: dueDate,
    due_time: dueTime,
    clear_due: !dueDate,
    clear_time: !dueTime,
    priority: +document.getElementById("tf-priority").value,
    project_id: document.getElementById("tf-project").value
      ? +document.getElementById("tf-project").value
      : null,
    tags,
    repeat_rule: repeatKey ? REPEAT_MAP[repeatKey] : null,
    clear_repeat: !repeatKey,
    remind_at: computeRemindAt(dueDate, dueTime, remindOff),
    clear_remind: !remindOff,
  };
  if (id) {
    await api(`/tasks/${id}`, { method: "PUT", body: JSON.stringify(body) });
    if (state.pendingTaskImageRemove && !state.pendingTaskImage) {
      await deleteTaskImage(+id);
    } else if (state.pendingTaskImage) {
      await uploadTaskImage(+id, state.pendingTaskImage);
    }
    showToast("Сохранено");
  } else {
    const created = await api("/tasks", { method: "POST", body: JSON.stringify(body) });
    if (state.pendingTaskImage && created?.id) {
      await uploadTaskImage(created.id, state.pendingTaskImage);
    }
    showToast("Задача создана");
  }
  state.pendingTaskImage = null;
  state.pendingTaskImageRemove = false;
  closeSheet();
  await loadAll();
}

async function checkDailyBriefing() {
  const hour = Number(localStorage.getItem("empire_briefing_hour") || "8");
  const now = new Date();
  if (now.getHours() < hour || now.getHours() > hour + 2) return;
  const key = `empire_daily_notified_${todayStr()}`;
  if (localStorage.getItem(key)) return;
  try {
    const daily = await api("/insights/daily");
    const items = daily.focus_items || [];
    if (!items.length) return;
    localStorage.setItem(key, "1");
    await showLocalNotification("Задачник · фокус дня", {
      body: items.slice(0, 3).join("\n"),
      tag: `daily-${daily.day}`,
    });
  } catch (_) {}
}

async function checkReminders() {
  await checkDailyBriefing();
  if (!("Notification" in window)) return;
  try {
    const data = await api("/reminders/due");
    for (const t of data.reminders || []) {
      if (state.reminded.has(t.id)) continue;
      if (Notification.permission !== "granted") continue;
      const opts = { body: t.title, tag: `task-${t.id}`, data: { url: TASKS_MOUNT + "/", task_id: t.id } };
      if (t.image_url) opts.image = t.image_url;
      const shown = await showLocalNotification("Задачник", opts);
      if (!shown) continue;
      await api(`/tasks/${t.id}/reminder/ack`, { method: "POST" });
      state.reminded.add(t.id);
      localStorage.setItem("empire_reminded", JSON.stringify([...state.reminded]));
    }
  } catch (_) {}
}

function bindEvents() {
  document.addEventListener("click", async (e) => {
    const settingsBtn = e.target.closest("[data-action^='open-settings']");
    if (settingsBtn) {
      e.preventDefault();
      closeMobileDrawer();
      closeOverflowMenu();
      const action = settingsBtn.dataset.action;
      if (action === "open-settings-notify") openSettings("notifications");
      else if (action === "open-settings-calendar") openSettings("calendar");
      else openSettings();
      return;
    }
    const navBtn = e.target.closest(".nav-row[data-view], .nav-item[data-view], .drawer-row[data-view]");
    if (navBtn && !navBtn.dataset.projectId && navBtn.dataset.view) {
      e.preventDefault();
      e.stopPropagation();
      if (navBtn.dataset.inbox === "1") {
        state.inboxOnly = true;
        showView("all-tasks");
      } else if (navBtn.dataset.view === "search") {
        document.getElementById("search-bar")?.classList.remove("hidden");
        showView("search");
        setTimeout(() => document.getElementById("search-input")?.focus(), 50);
      } else {
        showView(navBtn.dataset.view);
      }
      if (navBtn.dataset.drawerClose) closeMobileDrawer();
      return;
    }
    const projBtn = e.target.closest("[data-view='project-tasks'][data-project-id]");
    if (projBtn) {
      e.preventDefault();
      e.stopPropagation();
      state.projectFilter = +projBtn.dataset.projectId;
      showView("project-tasks");
      renderProjectTasks(state.projectFilter);
      return;
    }

    const fmTab = e.target.closest("[data-fm-tab]");
    if (fmTab?.closest("#view-finance-model")) {
      e.preventDefault();
      const raw = fmTab.dataset.fmTab;
      const next = raw === "snegiri" || raw === "career" ? raw : "empire";
      if (next !== state.fmPipelineTab) {
        state.fmPipelineTab = next;
        localStorage.setItem("empire_fm_tab", next);
        renderFinanceModel();
      }
      return;
    }

    const fmGoto = e.target.closest("[data-goto-checklist]");
    if (fmGoto?.closest("#view-finance-model")) {
      e.preventDefault();
      const id = +fmGoto.dataset.gotoChecklist;
      if (!id) return;
      showView("detail");
      await renderDetail(id);
      return;
    }

    const fmOpenTask = e.target.closest("[data-open-task]");
    if (fmOpenTask?.closest("#view-finance-model")) {
      e.preventDefault();
      const id = +fmOpenTask.dataset.openTask;
      const t = state.tasks.find((x) => x.id === id);
      if (t) await openSheet(t);
      return;
    }
  });

  document.getElementById("mobile-tabbar")?.addEventListener("click", (e) => {
    const btn = e.target.closest(".tab[data-view]");
    if (!btn) return;
    e.preventDefault();
    e.stopPropagation();
    const view = btn.dataset.view;
    if (view === "search") {
      document.getElementById("search-bar")?.classList.remove("hidden");
      showView("search");
      document.getElementById("search-input")?.focus();
      return;
    }
    showView(view);
  });

  document.getElementById("main")?.addEventListener("submit", async (e) => {
    const form = e.target.closest("form[data-quick-capture]");
    if (!form) return;
    e.preventDefault();
    const input = form.querySelector(".quick-capture-input");
    const title = input?.value || "";
    try {
      await quickCaptureCreate(title);
      if (input) {
        input.value = "";
        input.focus();
      }
    } catch (err) {
      showToast(err.message || "Не удалось создать");
    }
  });

  ["tf-due-date", "tf-due-time", "tf-repeat", "tf-project", "tf-priority", "tf-remind"].forEach((id) => {
    document.getElementById(id)?.addEventListener("change", () => syncSheetMetaDisplay());
  });
  document.getElementById("tf-tags")?.addEventListener("input", () => syncSheetMetaDisplay());
  document.getElementById("tf-tag-add")?.addEventListener("input", (e) => renderTagSuggestions(e.target.value));
  document.getElementById("tf-tag-add")?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      addSheetTag(e.target.value);
    } else if (e.key === "Escape") {
      e.target.value = "";
      renderTagSuggestions("");
    }
  });

  document.querySelectorAll(".icon-rail-btn[data-view]").forEach((btn) => {
    btn.addEventListener("click", () => {
      if (btn.dataset.view === "search") {
        const bar = document.getElementById("search-bar");
        bar.classList.remove("hidden");
        showView("search");
        document.getElementById("search-input").focus();
      } else {
        showView(btn.dataset.view);
      }
    });
  });
  document.getElementById("btn-back-view")?.addEventListener("click", () => {
    showView(state.settingsReturnView || "today");
  });

  document.getElementById("btn-refresh")?.addEventListener("click", () => loadAll().catch((e) => showToast(e.message)));
  document.getElementById("fab-add")?.addEventListener("click", () => onPrimaryAdd());
  document.getElementById("fab-ai")?.addEventListener("click", () => showView("assistant"));
  document.getElementById("btn-add-header")?.addEventListener("click", () => onPrimaryAdd());
  document.getElementById("task-form")?.addEventListener("submit", (e) => saveTaskForm(e).catch((err) => showToast(err.message)));
  document.getElementById("tf-image-file")?.addEventListener("change", (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    state.pendingTaskImage = file;
    state.pendingTaskImageRemove = false;
    renderTaskImagePreview();
  });
  document.getElementById("tf-image-remove")?.addEventListener("click", () => {
    state.pendingTaskImage = null;
    state.pendingTaskImageRemove = true;
    renderTaskImagePreview();
  });
  document.getElementById("tf-delete")?.addEventListener("click", async () => {
    const id = document.getElementById("tf-id").value;
    if (!id || !confirm("Удалить задачу?")) return;
    await api(`/tasks/${id}`, { method: "DELETE" });
    closeSheet();
    await loadAll();
    showToast("Удалено");
  });
  document.getElementById("tf-complete")?.addEventListener("click", async () => {
    const id = document.getElementById("tf-id").value;
    if (!id) return;
    await toggleTask(+id, "doing");
    closeSheet();
  });

  document.querySelectorAll("[data-action='close-sheet'], .sheet-backdrop").forEach((el) => {
    if (el.closest("#task-sheet")) el.addEventListener("click", closeSheet);
  });
  document.querySelectorAll("[data-action='close-measurement']").forEach((el) => {
    el.addEventListener("click", closeMeasurementSheet);
  });
  document.querySelectorAll("[data-action='close-workout']").forEach((el) => {
    el.addEventListener("click", closeWorkoutSheet);
  });
  document.getElementById("measurement-form")?.addEventListener("submit", (e) => saveMeasurementForm(e).catch((err) => showToast(err.message)));
  document.getElementById("workout-form")?.addEventListener("submit", (e) => saveWorkoutForm(e).catch((err) => showToast(err.message)));
  document.getElementById("mf-delete")?.addEventListener("click", async () => {
    const id = document.getElementById("mf-id").value;
    if (!id || !confirm("Удалить замер?")) return;
    await api(`/measurements/${id}`, { method: "DELETE" });
    closeMeasurementSheet();
    await loadAll();
    showToast("Удалено");
  });
  document.getElementById("wf-delete")?.addEventListener("click", async () => {
    const id = document.getElementById("wf-id").value;
    if (!id || !confirm("Удалить запись?")) return;
    await api(`/workouts/${id}`, { method: "DELETE" });
    closeWorkoutSheet();
    await loadAll();
    showToast("Удалено");
  });

  document.getElementById("date-chips")?.addEventListener("click", (e) => {
    const chip = e.target.closest("[data-date]");
    if (!chip) return;
    const kind = chip.dataset.date;
    const dateEl = document.getElementById("tf-due-date");
    if (kind === "today") dateEl.value = todayStr();
    else if (kind === "tomorrow") dateEl.value = addDays(1);
    else if (kind === "week") dateEl.value = addDays(7);
    else dateEl.value = "";
    syncSheetMetaDisplay();
  });

  document.getElementById("search-input")?.addEventListener("input", (e) => renderSearch(e.target.value));

  document.getElementById("subtask-add-btn")?.addEventListener("click", async () => {
    const parentId = document.getElementById("tf-id").value;
    const title = document.getElementById("subtask-new").value.trim();
    if (!parentId || !title) return;
    await api("/tasks", { method: "POST", body: JSON.stringify({ title, parent_id: +parentId }) });
    document.getElementById("subtask-new").value = "";
    await loadSubtasks(+parentId);
    await loadAll();
  });

  async function onCsvPick(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const r = await importTicktickFile(file);
      showToast(`Импорт: +${r.imported || 0}, архив +${r.imported_done || 0}, обновлено ${r.updated || 0}, описаний ${r.backfilled || 0}`);
      await loadAll();
    } catch (err) { showToast(String(err.message)); }
    e.target.value = "";
  }
  document.getElementById("import-csv").addEventListener("change", onCsvPick);
  document.getElementById("import-csv-mobile").addEventListener("change", onCsvPick);

  document.addEventListener("click", async (e) => {
    const actionEl = e.target.closest("[data-action]");
    if (actionEl) {
      const action = actionEl.dataset.action;
      if (action === "toggle-task") {
        if (!actionEl.closest("#main")) return;
        e.stopPropagation();
        try { await toggleTask(+actionEl.dataset.id, actionEl.dataset.status); } catch (err) { showToast(err.message); }
        return;
      }
      if (action === "open-task") {
        if (!actionEl.closest("#main")) return;
        const id = +actionEl.dataset.id;
        let t =
          state.tasks.find((x) => x.id === id) ||
          state.doneTasks.find((x) => x.id === id);
        if (!t) {
          try {
            t = await api(`/tasks/${id}`);
          } catch (_) {}
        }
        if (t) await openSheet(t);
        else showToast("Задача не найдена");
        return;
      }
      if (action === "toggle-item") {
        if (!actionEl.closest("#main")) return;
        try {
          const item = actionEl;
          const next = item.classList.contains("done") ? "todo" : "done";
          await api(`/checklists/${item.dataset.cl}/items/${item.dataset.id}`, {
            method: "PATCH",
            body: JSON.stringify({ status: next }),
          });
          await loadAll();
          if (state.currentView === "detail") await renderDetail(+item.dataset.cl);
        } catch (err) { showToast(err.message); }
        return;
      }
      if (action === "add-measurement-now") {
        if (!actionEl.closest("#main")) return;
        openMeasurementSheet();
        return;
      }
      if (action === "open-measurement") {
        if (!actionEl.closest("#main")) return;
        const m = state.measurements.find((x) => x.id === +actionEl.dataset.id);
        if (m) openMeasurementSheet(m);
        return;
      }
      if (action === "open-workout") {
        if (!actionEl.closest("#main")) return;
        const w = state.workouts.find((x) => x.id === +actionEl.dataset.id);
        if (w) openWorkoutSheet(w);
        return;
      }
      if (action === "back-lists") { if (!actionEl.closest("#main")) return; showView("lists"); }
      if (action === "back-projects") { if (!actionEl.closest("#main")) return; state.projectFilter = null; showView("projects"); }
      if (action === "show-all-tasks") { if (!actionEl.closest("#main")) return; showView("all-tasks"); }
      if (action === "show-done-history") { if (!actionEl.closest("#main")) return; showView("done"); }
      if (action === "quick-add") {
        if (!actionEl.closest("#main")) return;
        openSheet(null);
        if (state.currentView === "cal-day" && state.calendarDay) {
          document.getElementById("tf-due-date").value = state.calendarDay;
          syncSheetMetaDisplay();
        } else if (state.currentView === "today" || state.currentView === "week") {
          document.getElementById("tf-due-date").value = todayStr();
          syncSheetMetaDisplay();
        }
        return;
      }
      if (action === "cal-back-month") {
        if (!actionEl.closest("#main")) return;
        showView("calendar");
        return;
      }
      if (action === "cal-day-prev") {
        if (!actionEl.closest("#main")) return;
        state.calendarDay = addDaysToDateStr(state.calendarDay || todayStr(), -1);
        renderCalendarDay();
        return;
      }
      if (action === "cal-day-next") {
        if (!actionEl.closest("#main")) return;
        state.calendarDay = addDaysToDateStr(state.calendarDay || todayStr(), 1);
        renderCalendarDay();
        return;
      }
      if (action === "cal-day-today") {
        if (!actionEl.closest("#main")) return;
        openCalendarDay(todayStr());
        return;
      }
      if (action === "toggle-mobile-drawer") {
        toggleMobileDrawer();
        return;
      }
      if (action === "close-mobile-drawer") {
        closeMobileDrawer();
        return;
      }
      if (action === "toggle-overflow-menu") {
        toggleOverflowMenu();
        return;
      }
      if (action === "toggle-hide-done") {
        state.hideDoneInLists = !state.hideDoneInLists;
        localStorage.setItem("empire_hide_done", state.hideDoneInLists ? "1" : "0");
        syncOverflowHideDoneLabel();
        closeOverflowMenu();
        if (state.currentView === "today") renderToday();
        if (state.currentView === "week") renderWeek();
        return;
      }
      if (action === "overflow-view-sort") {
        closeOverflowMenu();
        showToast("Сортировка — в разработке");
        return;
      }
      if (action === "overflow-goto") {
        closeOverflowMenu();
        showView(actionEl.dataset.view);
        return;
      }
      if (action === "overflow-refresh") {
        closeOverflowMenu();
        loadAll().catch((err) => showToast(err.message));
        return;
      }
      if (action === "open-date-picker") {
        e.preventDefault();
        e.stopPropagation();
        openDatePicker();
        return;
      }
      if (action === "close-date-picker") {
        closeDatePicker();
        return;
      }
      if (action === "confirm-date-picker") {
        confirmDatePicker().catch((err) => showToast(err.message));
        return;
      }
      if (action === "dp-prev-month") {
        state.datePickerMonth = addMonthsToMonthStart(state.datePickerMonth || monthStartFromToday(), -1);
        renderDatePickerCalendar();
        return;
      }
      if (action === "dp-next-month") {
        state.datePickerMonth = addMonthsToMonthStart(state.datePickerMonth || monthStartFromToday(), 1);
        renderDatePickerCalendar();
        return;
      }
      if (action === "dp-pick-day") {
        state.datePickerSelected = actionEl.dataset.date;
        renderDatePickerCalendar();
        return;
      }
      if (action === "dp-quick") {
        const offset = Number(actionEl.dataset.offset || 0);
        state.datePickerSelected = addDaysToDateStr(todayStr(), offset);
        state.datePickerMonth = `${state.datePickerSelected.slice(0, 7)}-01`;
        renderDatePickerCalendar();
        return;
      }
      if (action === "dp-clear-date") {
        clearDatePickerSelection().catch((err) => showToast(err.message));
        return;
      }
      if (action === "filter-tag") {
        e.preventDefault();
        e.stopPropagation();
        openTagFilter(actionEl.dataset.tag);
        return;
      }
      if (action === "clear-tag-filter") {
        e.preventDefault();
        clearTagFilter();
        return;
      }
      if (action === "remove-sheet-tag") {
        e.preventDefault();
        e.stopPropagation();
        removeSheetTag(actionEl.dataset.tag);
        return;
      }
      if (action === "pick-sheet-tag") {
        e.preventDefault();
        e.stopPropagation();
        addSheetTag(actionEl.dataset.tag);
        return;
      }
      if (action === "focus-tag-add") {
        e.preventDefault();
        document.getElementById("tf-tag-add")?.focus();
        return;
      }
      if (action === "switch-program") {
        e.preventDefault();
        const next = actionEl.dataset.programId || "gym_2026";
        if (next === state.programId) return;
        state.programId = next;
        localStorage.setItem("empire_workout_program", next);
        state.workoutProgramSummary = null;
        renderWorkoutProgram().catch((err) => showToast(err.message));
        return;
      }
      if (action === "download-program-template") {
        e.preventDefault();
        apiDownload("/workouts/program/template", "full_body_3day.json").catch((err) => showToast(err.message));
        return;
      }
      if (action === "export-program") {
        e.preventDefault();
        const id = state.programId || "gym_2026";
        api(`/workouts/program/${encodeURIComponent(id)}/export`)
          .then((spec) => {
            const blob = new Blob([JSON.stringify(spec, null, 2)], { type: "application/json" });
            const a = document.createElement("a");
            a.href = URL.createObjectURL(blob);
            a.download = `${id}.json`;
            a.rel = "noopener";
            a.style.display = "none";
            document.body.appendChild(a);
            a.click();
            setTimeout(() => {
              URL.revokeObjectURL(a.href);
              a.remove();
            }, 2000);
          })
          .catch((err) => showToast(err.message));
        return;
      }
      if (action === "backup-health") {
        e.preventDefault();
        apiDownload("/body/backup", `health_backup.zip`, { method: "POST" })
          .then(() => showToast("Бэкап сохранён на VPS и скачан"))
          .catch((err) => showToast(err.message));
        return;
      }
      if (action === "delete-program") {
        e.preventDefault();
        const id = state.programId;
        if (!id || !confirm(`Удалить загруженный файл «${id}»? Логи подходов останутся.`)) return;
        api(`/workouts/program/${encodeURIComponent(id)}`, { method: "DELETE" })
          .then(async (r) => {
            state.workoutPrograms = r.programs || [];
            state.programId = "gym_2026";
            localStorage.setItem("empire_workout_program", "gym_2026");
            showToast("Файл удалён");
            await renderWorkoutProgram();
          })
          .catch((err) => showToast(err.message));
        return;
      }
      if (action === "rest-start") {
        e.preventDefault();
        startRestTimer(Number(actionEl.dataset.sec) || getRestTimerDefaultSec());
        return;
      }
      if (action === "rest-pause") {
        e.preventDefault();
        pauseRestTimer();
        return;
      }
      if (action === "rest-resume") {
        e.preventDefault();
        resumeRestTimer();
        return;
      }
      if (action === "rest-stop") {
        e.preventDefault();
        stopRestTimer();
        return;
      }
      if (action === "hold-start") {
        e.preventDefault();
        e.stopPropagation();
        const idx = actionEl.dataset.idx;
        const setNum = actionEl.dataset.set;
        const root = document.getElementById("view-program");
        const secInp = root?.querySelector(`.pg-hold-sec[data-idx="${idx}"][data-set="${setNum}"]`);
        const ex = state.programSession?.exercises?.[Number(idx)];
        const sec = Number(actionEl.dataset.holdSec)
          || Number(secInp?.value)
          || programHoldSec(ex)
          || programHoldDefaultSec(ex || {});
        startHoldTimer(idx, setNum, sec, ex?.exercise_label || "Удержание");
        return;
      }
      if (action === "hold-pause") {
        e.preventDefault();
        pauseHoldTimer();
        return;
      }
      if (action === "hold-resume") {
        e.preventDefault();
        resumeHoldTimer();
        return;
      }
      if (action === "hold-stop") {
        e.preventDefault();
        stopHoldTimer();
        return;
      }
      if (action === "rest-add-30") {
        e.preventDefault();
        addRestTimerSeconds(30);
        return;
      }
      if (action === "focus-field") {
        const targetId = actionEl.dataset.target;
        const details = document.getElementById("sheet-fields-details");
        if (details) details.open = true;
        const field = document.getElementById(targetId);
        field?.focus();
        field?.scrollIntoView({ behavior: "smooth", block: "center" });
        return;
      }
      if (action === "toggle-sheet-fields") {
        const details = document.getElementById("sheet-fields-details");
        if (details) details.open = !details.open;
        return;
      }
      if (action === "cycle-priority") {
        const sel = document.getElementById("tf-priority");
        if (!sel) return;
        const order = [0, 2, 3, 0];
        const cur = Number(sel.value || 0);
        const idx = order.indexOf(cur >= 2 ? cur : 0);
        sel.value = String(order[(idx + 1) % order.length]);
        syncSheetMetaDisplay();
        return;
      }
    }

    const mRow = e.target.closest("[data-measurement-id]");
    if (mRow && mRow.closest("#main") && !e.target.closest("[data-action]")) {
      const m = state.measurements.find((x) => x.id === +mRow.dataset.measurementId);
      if (m) openMeasurementSheet(m);
      return;
    }

    const wRow = e.target.closest("[data-workout-id]");
    if (wRow && wRow.closest("#main") && !e.target.closest("[data-action]")) {
      const w = state.workouts.find((x) => x.id === +wRow.dataset.workoutId);
      if (w) openWorkoutSheet(w);
      return;
    }

    const row = e.target.closest("[data-task-id]");
    if (row && row.closest("#main") && !e.target.closest("[data-action='toggle-task']")) {
      const t = [...state.tasks, ...state.doneTasks].find((x) => x.id === +row.dataset.taskId);
      if (t) await openSheet(t);
      return;
    }

    const clRow = e.target.closest("[data-checklist-id]");
    if (clRow && clRow.closest("#main")) {
      showView("detail");
      await renderDetail(+clRow.dataset.checklistId);
      return;
    }

    const pRow = e.target.closest("[data-project-id]");
    if (pRow && pRow.closest("#main")) {
      state.projectFilter = +pRow.dataset.projectId;
      showView("project-tasks");
      renderProjectTasks(state.projectFilter);
    }
  });

  document.getElementById("token-save")?.addEventListener("click", async () => {
    const v = document.getElementById("token-input").value.trim();
    if (!v) return;
    localStorage.setItem(TOKEN_KEY, v);
    document.getElementById("auth-screen").classList.add("hidden");
    const splash = document.getElementById("boot-splash");
    if (splash) {
      splash.classList.remove("hidden");
      const p = splash.querySelector("[data-boot-msg]");
      if (p) p.textContent = "Вход…";
    }
    try {
      await loadAll();
      if (isGymApp()) showView("program");
      else showView("today");
      hideBootSplash();
    } catch (e) {
      showBootFailure(e.message === "auth" ? "Неверный токен" : (e.message || "Ошибка входа"));
      document.getElementById("auth-screen")?.classList.remove("hidden");
    }
  });
}

let bootWatchdogId = null;

function clearBootWatchdog() {
  if (bootWatchdogId != null) {
    clearTimeout(bootWatchdogId);
    bootWatchdogId = null;
  }
}

function uiLooksAlive() {
  const auth = document.getElementById("auth-screen");
  const authOpen = !!(auth && !auth.classList.contains("hidden"));
  const tasksN = Array.isArray(state.tasks) ? state.tasks.length : 0;
  const todayLen = (document.getElementById("view-today")?.innerHTML || "").length;
  return authOpen || tasksN > 0 || todayLen > 40;
}

function hidePcLifeline() {
  document.getElementById("pc-lifeline")?.classList.add("ok");
}

function hideBootSplash() {
  clearBootWatchdog();
  window.__empireDiag = {
    appVer: APP_VER,
    tasks: Array.isArray(state.tasks) ? state.tasks.length : 0,
    checklists: Array.isArray(state.checklists) ? state.checklists.length : 0,
    projects: Array.isArray(state.projects) ? state.projects.length : 0,
    hasToken: !!token(),
  };
  // Не прячем splash в чёрную пустоту: всегда показываем auth или UI.
  if (!uiLooksAlive()) {
    if (!token()) {
      document.getElementById("auth-screen")?.classList.remove("hidden");
    } else if ((window.__empireDiag.tasks || 0) === 0) {
      setBootMsg("Нет задач с сервера — введите токен заново или обновите.");
      document.getElementById("auth-screen")?.classList.remove("hidden");
    } else {
      setBootMsg("Рисую экран…");
    }
  }
  window.__empireReady = true;
  document.getElementById("boot-splash")?.classList.add("hidden");
  const err = document.getElementById("boot-error");
  if (err) err.style.display = "none";
  if (token() && uiLooksAlive() && (window.__empireDiag.tasks || 0) > 0) {
    document.getElementById("auth-screen")?.classList.add("hidden");
    hidePcLifeline();
  } else if (!token() || !uiLooksAlive()) {
    document.getElementById("auth-screen")?.classList.remove("hidden");
  }
}

function showBootFailure(msg) {
  clearBootWatchdog();
  window.__empireReady = true;
  document.getElementById("boot-splash")?.classList.add("hidden");
  const box = document.getElementById("boot-error");
  if (box) {
    box.style.display = "block";
    box.textContent = msg || "Ошибка загрузки";
  }
  document.getElementById("auth-screen")?.classList.remove("hidden");
  // lifeline остаётся видимой на ПК
}

async function purgeOldAppCache() {
  try {
    const prev = localStorage.getItem("empire_app_ver");
    if (prev === APP_VER) return;
    localStorage.setItem("empire_app_ver", APP_VER);
    if (!("caches" in window)) return;
    const keysPromise = caches.keys();
    const keys = await Promise.race([
      keysPromise,
      new Promise((_, rej) => setTimeout(() => rej(new Error("cache-timeout")), 800)),
    ]);
    await Promise.race([
      Promise.all(keys.map((k) => caches.delete(k).catch(() => {}))),
      new Promise((r) => setTimeout(r, 800)),
    ]);
  } catch (_) {}
}

async function init() {
  const splash = document.getElementById("boot-splash");
  if (splash) splash.classList.remove("hidden");
  setBootMsg("Старт…");
  try {
    try {
      applyFontScale();
      applyGymChrome();
    } catch (e) {
      console.error("chrome", e);
    }
    setBootMsg("Кэш…");
    await Promise.race([purgeOldAppCache(), new Promise((r) => setTimeout(r, 1000))]);
    try {
      closeAllSheets();
      loadColumnWidths();
    } catch (e) {
      console.error("sheets/cols", e);
    }
    const projectsWrap = document.querySelector(".nav-projects-wrap");
    if (projectsWrap && localStorage.getItem("empire_projects_open") === "0") {
      projectsWrap.open = false;
    }
    setBootMsg("Интерфейс…");
    try {
      bindEvents();
    } catch (e) {
      console.error("bindEvents", e);
      showBootFailure("Ошибка UI: " + (e && e.message ? e.message : e));
    }
    try {
      initRestTimerControls();
      bindColumnResizers();
      renderMobileTabbar();
      syncOverflowHideDoneLabel();
      hydrateNavIcons();
      suppressAutofillBar(document.getElementById("tf-title"));
      suppressAutofillBar(document.getElementById("search-input"));
      suppressAutofillBar(document.getElementById("tf-tag-add"));
      suppressAutofillBar(document.getElementById("tf-note"));
    } catch (e) {
      console.error("ui extras", e);
    }
    if (window.matchMedia("(min-width: 900px)").matches) {
      document.getElementById("sheet-fields-details")?.setAttribute("open", "");
    }
    window.addEventListener("resize", () => {
      try {
        syncSplitTaskLayout();
      } catch (_) {}
    });
    document.addEventListener("keydown", (e) => {
      if (state.currentView !== "calendar") return;
      if (e.target.closest("input, textarea, select, [contenteditable]")) return;
      if (e.key === "ArrowLeft") {
        state.calendarMonth = addMonthsToMonthStart(state.calendarMonth, -1);
        renderCalendar();
      } else if (e.key === "ArrowRight") {
        state.calendarMonth = addMonthsToMonthStart(state.calendarMonth, 1);
        renderCalendar();
      }
    });
    if (!token()) {
      hideBootSplash();
      document.getElementById("auth-screen")?.classList.remove("hidden");
      try {
        renderSidebarNav();
      } catch (_) {}
      return;
    }
    try {
      setBootMsg("Данные с сервера…");
      await loadAll();
      closeAllSheets();
      const params = new URLSearchParams(location.search);
      const view = params.get("view");
      const settingsSection = params.get("section");
      if (view === "settings") {
        if (settingsSection && SETTINGS_SECTIONS.some((s) => s.id === settingsSection)) {
          state.settingsSection = settingsSection;
        }
        openSettings(state.settingsSection);
      } else if (view && TITLES[view]) {
        showView(view);
        if (view === "program") await renderWorkoutProgram();
      } else if (isGymApp()) {
        showView("program");
        await renderWorkoutProgram();
      } else {
        closeAllSheets();
        showView(state.currentView || "today");
      }
      if (params.get("action") === "new") onPrimaryAdd();
      const taskId = params.get("task");
      if (taskId) {
        const t = state.tasks.find((x) => String(x.id) === taskId) || state.doneTasks.find((x) => String(x.id) === taskId);
        if (t) await openSheet(t);
        else {
          try {
            const remote = await api(`/tasks/${taskId}`);
            if (remote) await openSheet(remote);
          } catch (_) {}
        }
      }
      syncSplitTaskLayout();
      hideBootSplash();
      if (!isGymApp()) ensurePushSubscription().catch(() => {});
    } catch (e) {
      if (e.message === "auth") {
        hideBootSplash();
        document.getElementById("auth-screen")?.classList.remove("hidden");
        return;
      }
      showToast(e.message);
      // офлайн-снимок уже мог примениться в loadAll; всё равно покажем UI
      try {
        if (isGymApp()) {
          const el = document.getElementById("view-program");
          if (el) {
            document.querySelectorAll(".view").forEach((v) => v.classList.remove("active"));
            el.classList.add("active");
            el.innerHTML = `<div class="card"><h3>Не удалось загрузить</h3><p>${escapeHtml(e.message || "ошибка")}</p><p class="muted">Обновите страницу или введите токен заново.</p><p><button type="button" class="btn" id="btn-retry-auth">Сменить токен</button></p></div>`;
            document.getElementById("btn-retry-auth")?.addEventListener("click", () => {
              localStorage.removeItem(TOKEN_KEY);
              document.getElementById("auth-screen")?.classList.remove("hidden");
            });
          }
          document.getElementById("page-title").textContent = "Программа";
        } else {
          showView("today");
          showBootFailure(e.message || "Ошибка загрузки данных");
        }
      } catch (_) {
        showBootFailure(e.message || "Ошибка загрузки");
      }
      hideBootSplash();
    }
    setInterval(() => checkReminders(), 60000);
    setInterval(() => checkHealthReminders(), 60000);
  } catch (e) {
    showBootFailure(e && e.message ? e.message : String(e));
  }
}

// 25s: loadAll тянет 8 эндпоинтов + рендер; 8s давал ложный «зависла» и оставлял auth поверх UI.
bootWatchdogId = setTimeout(() => {
  if (!window.__empireReady) {
    showBootFailure(
      "Загрузка зависла. Закройте ВСЕ вкладки neverretire.ru, откройте https://neverretire.ru/go-tasks/ и нажмите кнопку."
    );
  }
}, 12000);

init().catch((e) => showBootFailure(e && e.message ? e.message : String(e)));
