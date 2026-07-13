/** Метаданные фаз мультика (термины тренеров, тайминги, подсказки). */
(function (global) {
  const URL = "data/comic_phases.json";
  let cache = null;

  function load() {
    if (cache) return Promise.resolve(cache);
    return fetch(URL)
      .then(function (r) {
        if (!r.ok) throw new Error("phases");
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

  function bySlug(slug) {
    return cache ? cache[slug] : null;
  }

  function frameSrc(spec, performer, index) {
    if (!spec) return null;
    const pk = performer === "f" ? "f" : "m";
    const n = String(index).padStart(2, "0");
    return spec.frame_dir + "/" + pk + "/" + n + ".webp";
  }

  function stripSrc(spec, performer) {
    if (!spec || !spec.strip) return null;
    const pk = performer === "f" ? "f" : "m";
    return spec.strip[pk];
  }

  global.SnegiriComicPhases = {
    load: load,
    bySlug: bySlug,
    frameSrc: frameSrc,
    stripSrc: stripSrc,
  };
})(typeof window !== "undefined" ? window : globalThis);
