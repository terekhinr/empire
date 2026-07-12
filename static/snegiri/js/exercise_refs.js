/** Ссылки YouTube + метаданные мультиков. Источник: snegiri_kb/exercise_refs_data.json */
(function (global) {
  const REFS_URL = "data/exercise_refs.json";
  let cache = null;

  function bySlug(slug) {
    if (!cache) return null;
    return cache[slug.replace(/-/g, "_")] || null;
  }

  function byExerciseId(id) {
    if (!cache) return null;
    for (const key in cache) {
      if (cache[key].ids && cache[key].ids.indexOf(id) >= 0) return cache[key];
    }
    return null;
  }

  function performerKey() {
    try {
      const p = global.SnegiriStore && global.SnegiriStore.get().profile.performer;
      return p === "f" ? "f" : "m";
    } catch (e) {
      return "m";
    }
  }

  function comicSrc(ref) {
    if (!ref || !ref.comic || !ref.comic.assets) return null;
    const k = performerKey();
    return ref.comic.assets[k] || ref.comic.assets.m;
  }

  function load() {
    if (cache) return Promise.resolve(cache);
    return fetch(REFS_URL)
      .then(function (r) {
        if (!r.ok) throw new Error("refs");
        return r.json();
      })
      .then(function (data) {
        cache = {};
        for (const k in data) {
          if (k.charAt(0) !== "_") cache[k] = data[k];
        }
        return cache;
      })
      .catch(function () {
        cache = {};
        return cache;
      });
  }

  global.SnegiriExerciseRefs = {
    load: load,
    bySlug: bySlug,
    byExerciseId: byExerciseId,
    comicSrc: comicSrc,
    performerKey: performerKey,
  };
})(typeof window !== "undefined" ? window : globalThis);
