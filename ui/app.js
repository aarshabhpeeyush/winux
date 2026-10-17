// WinUx control panel. Talks to server.py, which changes the real Windows settings.

const TOKEN = window.WINUX_TOKEN;
let state = {};
let wallFilter = "all";
let art = null; // { file, colors, accent, dark }

const $ = (id) => document.getElementById(id);

const ACCENTS = [
  ["#ffe600", "Dark World"],
  ["#d4141e", "Soul"],
  ["#3b6fd8", "Kris"],
  ["#9b4dca", "Susie"],
  ["#2fbf71", "Ralsei"],
  ["#3a3aff", "Lancer"],
  ["#ff3ea5", "Big Shot"],
  ["#5b8cff", "Skyline"],
  ["#00d0ff", "Cyber"],
  ["#ff8a1f", "Orange"],
  ["#8a8f98", "Gaster"],
  ["#f2f2f2", "White"],
];

// ---------------------------------------------------------------- server

async function api(path, { method = "GET", body, headers = {} } = {}) {
  const res = await fetch(path, {
    method,
    headers: {
      "X-WinUx-Token": TOKEN,
      ...(body && !(body instanceof Blob) ? { "Content-Type": "application/json" } : {}),
      ...headers,
    },
    body: body instanceof Blob ? body : body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || "Something went wrong.");
  return data;
}

async function apply(settings, message) {
  try {
    state = { ...state, ...(await api("/api/apply", { method: "POST", body: settings })) };
    render();
    if (message) {
      const onTaskbarTab = !$("tab-taskbar").classList.contains("hidden");
      say(state.needsRestart && !onTaskbarTab
        ? [...(Array.isArray(message) ? message : [message]), " Restart the taskbar (TASKBAR tab) to see all of it."]
        : message);
    }
  } catch (e) {
    say(e.message, true);
  }
}

// ---------------------------------------------------------------- dialog box

let typing = 0;
let audio;

function blip() {
  try {
    audio = audio || new AudioContext();
    const o = audio.createOscillator();
    const g = audio.createGain();
    o.type = "square";
    o.frequency.value = 520 + Math.random() * 40;
    g.gain.value = 0.025;
    o.connect(g).connect(audio.destination);
    o.start();
    o.stop(audio.currentTime + 0.03);
  } catch { /* no sound, no problem */ }
}

// Anything about Gaster is written in Wingdings. wd("text") marks a piece of a
// message; hovering it shows the real words.
const wd = (text) => ({ text, wd: true });

function wdSpan(el, text) {
  el.classList.add("wd");
  el.textContent = text;
  el.title = text;
  return el;
}

// msg is a string, or a list of strings and wd() pieces.
function say(msg, error = false) {
  const el = $("dialogText");
  $("dialog").classList.toggle("error", error);
  const parts = (Array.isArray(msg) ? msg : [msg]).map((p) => (typeof p === "string" ? { text: p } : p));
  el.textContent = "";
  const spans = parts.map((p) => {
    const s = document.createElement("span");
    if (p.wd) { s.className = "wd"; s.title = p.text; }
    el.appendChild(s);
    return s;
  });
  const run = ++typing;
  let part = 0, i = 0;
  const step = () => {
    if (run !== typing || part >= parts.length) return;
    const text = parts[part].text;
    spans[part].textContent = text.slice(0, ++i);
    if (i % 2 === 0 && text[i - 1] !== " ") blip();
    if (i >= text.length) { part++; i = 0; }
    if (part < parts.length) setTimeout(step, 22);
  };
  step();
}

// ---------------------------------------------------------------- sparkle corners

const SPARKLE = '<svg viewBox="0 0 16 16"><path d="M8 0L9.4 6.6 16 8 9.4 9.4 8 16 6.6 9.4 0 8 6.6 6.6Z" fill="currentColor"/></svg>';
for (const box of document.querySelectorAll(".box")) {
  for (const pos of ["tl", "tr", "bl", "br"]) {
    const c = document.createElement("span");
    c.className = "corner " + pos;
    c.innerHTML = SPARKLE;
    box.appendChild(c);
  }
}

// ---------------------------------------------------------------- tabs

for (const btn of document.querySelectorAll("#menu button[data-tab]")) {
  btn.addEventListener("click", () => {
    document.querySelectorAll("#menu button").forEach((b) => b.classList.toggle("active", b === btn));
    document.querySelectorAll(".tab").forEach((t) => t.classList.add("hidden"));
    $("tab-" + btn.dataset.tab).classList.remove("hidden");
    if (btn.dataset.tab === "wallpaper") loadWalls();
    if (btn.dataset.tab === "live") loadLive();
    if (btn.dataset.tab === "taskbar") loadMods();
    if (btn.dataset.tab === "widgets") loadWidgets();
    if (btn.dataset.tab === "themes") loadThemes();
  });
}

// ---------------------------------------------------------------- colors tab

function swatch(hex, name, onPick) {
  const wrap = document.createElement("div");
  wrap.className = "swatch-wrap";
  const b = document.createElement("button");
  b.className = "swatch";
  b.style.background = hex;
  b.dataset.hex = hex;
  b.title = name ? `${name} ${hex}` : hex;
  b.addEventListener("click", () => onPick(hex, name));
  wrap.appendChild(b);
  if (name) {
    const n = document.createElement("span");
    n.className = "swatch-name";
    if (name === "Gaster") wdSpan(n, name);
    else n.textContent = name;
    wrap.appendChild(n);
  }
  return wrap;
}

for (const [hex, name] of ACCENTS) {
  $("swatches").appendChild(
    swatch(hex, name, () => apply({ accent: hex }, name === "Gaster"
      ? ["Your accent is now ", wd("Gaster. Dark, darker, yet darker.")]
      : `Your accent is now ${name}. It fills you with determination.`))
  );
}

$("customColor").addEventListener("change", (e) =>
  apply({ accent: e.target.value }, `Accent set to ${e.target.value}.`)
);

for (const seg of document.querySelectorAll("#tab-colors .seg")) {
  for (const b of seg.querySelectorAll("button")) {
    b.addEventListener("click", () => {
      const dark = b.dataset.val === "true";
      const what = seg.dataset.key === "appsDark" ? "Apps" : "Windows";
      apply({ [seg.dataset.key]: dark }, dark
        ? [`${what} went dark. `, wd("Darker, yet darker.")]
        : `${what} went light. The sun is out.`);
    });
  }
}

for (const cb of document.querySelectorAll("#tab-colors input[type=checkbox]")) {
  cb.addEventListener("change", () =>
    apply({ [cb.dataset.key]: cb.checked }, cb.checked ? "Turned it on." : "Turned it off.")
  );
}

function render() {
  renderVersion();
  document.documentElement.style.setProperty("--accent", state.accent);
  $("nowAccent").style.background = state.accent;
  $("nowAccentText").textContent = state.accent;
  $("nowMode").textContent = `Apps ${state.appsDark ? "dark" : "light"} · Windows ${state.systemDark ? "dark" : "light"}`;
  $("customColor").value = state.accent;

  for (const seg of document.querySelectorAll("#tab-colors .seg")) {
    for (const b of seg.querySelectorAll("button")) {
      b.classList.toggle("on", String(state[seg.dataset.key]) === b.dataset.val);
    }
  }
  for (const cb of document.querySelectorAll("#tab-colors input[type=checkbox]")) {
    cb.checked = !!state[cb.dataset.key];
  }
  for (const s of document.querySelectorAll("#swatches .swatch")) {
    s.classList.toggle("on", s.dataset.hex.toLowerCase() === state.accent);
  }
  $("wallStyle").value = state.wallpaperStyle;
  for (const w of document.querySelectorAll(".wall[data-id]")) {
    w.classList.toggle("on", !state.live && w.dataset.id === state.wallpaper);
  }
  for (const w of document.querySelectorAll(".wall[data-live]")) {
    w.classList.toggle("on", w.dataset.live === state.live);
  }
  $("nowLive").textContent = state.live ? "Live wallpaper on" : "";
  $("liveKeyboard").checked = !!state.liveKeyboard;
  renderTaskbar();
  renderLooks();
  if (state.backup) $("backupDate").textContent = ` (${state.backup})`;
}

// ---------------------------------------------------------------- wallpaper tab

const wallUrl = (id) => "/wall?id=" + encodeURIComponent(id);

async function loadWalls() {
  const list = await api("/api/wallpapers");
  const grid = $("walls");
  grid.innerHTML = "";
  const shown = list.filter((w) => wallFilter === "all" || w.source === wallFilter);
  if (!shown.length) grid.innerHTML = '<div class="empty">* Nothing here yet. Add an image!</div>';
  for (const w of shown) {
    const b = document.createElement("button");
    b.className = "wall";
    b.dataset.id = w.id;
    b.style.backgroundImage = `url("${wallUrl(w.id)}")`;
    b.innerHTML = `<span></span>`;
    b.querySelector("span").textContent = w.name;
    b.addEventListener("click", () => apply({ wallpaper: w.id }, `Wallpaper changed to "${w.name}".`));
    grid.appendChild(b);
  }
  render();
}

for (const b of document.querySelectorAll("#wallFilter button")) {
  b.addEventListener("click", () => {
    wallFilter = b.dataset.val;
    document.querySelectorAll("#wallFilter button").forEach((x) => x.classList.toggle("on", x === b));
    loadWalls();
  });
}

$("wallStyle").addEventListener("change", (e) =>
  apply({ wallpaperStyle: e.target.value }, `Wallpaper fit: ${e.target.value}.`)
);

async function upload(file, kind) {
  return api("/api/upload", {
    method: "POST",
    body: file,
    headers: { "X-Filename": file.name, "X-Kind": kind },
  });
}

$("wallUpload").addEventListener("change", async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  try {
    const { id } = await upload(file, "wallpaper");
    await apply({ wallpaper: id }, `Added "${file.name}" and made it your wallpaper.`);
    loadWalls();
  } catch (err) {
    say(err.message, true);
  }
  e.target.value = "";
});

// ---------------------------------------------------------------- live wallpapers

let liveFilter = "all";
const liveFile = (id) => "/livefile?id=" + encodeURIComponent(id);
const liveThumb = (id, kind = "thumb") => `/livethumb?id=${encodeURIComponent(id)}&kind=${kind}`;
const LIVE_TAGS = { winux: "WINUX", yours: "YOURS", lively: "LIVELY" };

function livePreview(w) {
  if (w.kind === "web") {
    const f = document.createElement("iframe");
    f.src = liveFile(w.id);
    f.loading = "lazy";
    f.tabIndex = -1;
    return f;
  }
  if (w.kind === "video") {
    const v = document.createElement("video");
    v.src = liveFile(w.id);
    v.muted = true;
    v.loop = true;
    v.preload = "metadata";
    return v;
  }
  const img = document.createElement("img");
  img.loading = "lazy";
  img.alt = "";
  img.src = w.kind === "gif" ? liveFile(w.id) : liveThumb(w.id, w.thumb ? "thumb" : "preview");
  return img;
}

async function loadLive() {
  $("liveMissing").hidden = state.lively;
  $("webviewMissing").hidden = !state.lively || state.webview2;
  $("liveBody").hidden = !state.lively;
  if (!state.lively) return;
  const list = await api("/api/live");
  const grid = $("liveWalls");
  grid.innerHTML = "";
  const shown = list.filter((w) => liveFilter === "all" || w.source === liveFilter);
  if (!shown.length) grid.innerHTML = '<div class="empty">* Nothing here yet. Add a video or GIF!</div>';
  for (const w of shown) {
    const b = document.createElement("button");
    b.className = "wall";
    b.dataset.live = w.id;
    const media = livePreview(w);
    b.appendChild(media);
    b.insertAdjacentHTML("beforeend", `<span class="tag"></span><span class="name"></span>`);
    b.querySelector(".tag").textContent = LIVE_TAGS[w.source];
    addExtras(b, w.extras);
    if (w.wingdings) wdSpan(b.querySelector(".name"), w.name);
    else b.querySelector(".name").textContent = w.name;

    // Hover = play the preview (video plays, Lively items swap to their animated GIF).
    b.addEventListener("mouseenter", () => {
      if (w.kind === "video") media.play().catch(() => {});
      if (w.kind === "lively" && w.preview) media.src = liveThumb(w.id, "preview");
    });
    b.addEventListener("mouseleave", () => {
      if (w.kind === "video") media.pause();
      if (w.kind === "lively" && w.thumb) media.src = liveThumb(w.id, "thumb");
    });
    b.addEventListener("click", () => apply({ live: w.id }, w.wingdings
      ? [wd(w.name), " is now alive on your desktop."]
      : `"${w.name}" is now alive on your desktop.`));
    grid.appendChild(b);
  }
  render();
}

for (const b of document.querySelectorAll("#liveFilter button")) {
  b.addEventListener("click", () => {
    liveFilter = b.dataset.val;
    document.querySelectorAll("#liveFilter button").forEach((x) => x.classList.toggle("on", x === b));
    loadLive();
  });
}

$("liveKeyboard").addEventListener("change", async (e) => {
  e.target.disabled = true;
  say("Restarting Lively... one sec.");
  try {
    state = { ...state, ...(await api("/api/lively-keyboard", { method: "POST", body: { on: e.target.checked } })) };
    say(e.target.checked ? "Wallpapers can hear your keyboard now. Click the desktop and press the arrow keys!" : "Wallpapers can't use your keyboard anymore.");
  } catch (err) {
    say(err.message, true);
  }
  e.target.checked = !!state.liveKeyboard;
  e.target.disabled = false;
});

$("liveStop").addEventListener("click", () =>
  apply({ live: null }, "The live wallpaper fell asleep. Your normal wallpaper is back.")
);

$("liveUpload").addEventListener("change", async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  say(`Uploading "${file.name}"...`);
  try {
    const { id } = await upload(file, "live");
    await apply({ live: id }, `"${file.name}" is now your live wallpaper.`);
    loadLive();
  } catch (err) {
    say(err.message, true);
  }
  e.target.value = "";
});

// ---------------------------------------------------------------- taskbar

const TB_SAYS = {
  tbStyle: { normal: "The taskbar is back to normal.", clear: "The taskbar turned invisible. Spooky.",
             blur: "The taskbar went blurry.", acrylic: "The taskbar is made of glass now.",
             opaque: "The taskbar is solid as a rock." },
  tbMax: { same: "Full-screen windows keep the same taskbar look.", acrylic: "Full-screen windows get a glass taskbar.",
           opaque: "Full-screen windows get a solid taskbar.", normal: "Full-screen windows get the normal taskbar." },
  taskbarAlign: { center: "Icons in the middle.", left: "Icons on the left, old-school." },
  searchMode: { hidden: "Search is hidden.", icon: "Search is just an icon.", box: "Search box is back.",
                label: "Search icon with a label." },
};

for (const seg of document.querySelectorAll("#tab-taskbar .seg")) {
  for (const b of seg.querySelectorAll("button")) {
    b.addEventListener("click", () =>
      apply({ [seg.dataset.key]: b.dataset.val }, TB_SAYS[seg.dataset.key][b.dataset.val])
    );
  }
}

for (const cb of document.querySelectorAll("#tab-taskbar input[data-tb]")) {
  cb.addEventListener("change", () => {
    const name = cb.dataset.tb === "autoHide" ? "Auto-hide" : "Task View button";
    apply({ [cb.dataset.tb]: cb.checked }, `${name} ${cb.checked ? "on" : "off"}.`);
  });
}

$("tbLine").addEventListener("change", (e) =>
  apply({ tbLine: e.target.checked }, e.target.checked ? "A thin line sits on top of the taskbar." : "Line removed.")
);
$("tbColor").addEventListener("change", (e) =>
  apply({ tbColor: e.target.value }, `Taskbar tint is now ${e.target.value}.`)
);
$("tbOpacity").addEventListener("input", (e) => ($("tbOpacityVal").textContent = e.target.value + "%"));
$("tbOpacity").addEventListener("change", (e) =>
  apply({ tbOpacity: Number(e.target.value) }, `Tint strength: ${e.target.value}%.`)
);
$("tbUseAccent").addEventListener("click", () =>
  apply({ tbColor: state.accent, tbOpacity: Math.max(state.tbOpacity, 20) }, "The taskbar now matches your accent color.")
);

function renderVersion() {
  if (state.version) $("version").textContent = "v" + state.version;
}

function renderTaskbar() {
  $("tbLookGroup").hidden = !state.ttb;
  $("tbMissing").hidden = state.ttb;
  for (const seg of document.querySelectorAll("#tab-taskbar .seg")) {
    for (const b of seg.querySelectorAll("button")) {
      b.classList.toggle("on", state[seg.dataset.key] === b.dataset.val);
    }
  }
  for (const cb of document.querySelectorAll("#tab-taskbar input[data-tb]")) cb.checked = !!state[cb.dataset.tb];
  $("tbLine").checked = !!state.tbLine;
  $("tbColor").value = state.tbColor || "#000000";
  $("tbOpacity").value = state.tbOpacity ?? 0;
  $("tbOpacityVal").textContent = (state.tbOpacity ?? 0) + "%";
  $("tbRestart").hidden = !state.needsRestart;
  // Windows 10 has no icon position switch and no "icon + label" search
  $("tbAlignGroup").hidden = !state.win11;
  document.querySelector('#tab-taskbar .seg[data-key="searchMode"] [data-val="label"]').hidden = !state.win11;
}

async function restartTaskbar() {
  await api("/api/refresh-taskbar", { method: "POST" });
  state.needsRestart = false;
  render();
  say("The taskbar blinked out of existence... and came back.");
}
$("tbRestartBtn").addEventListener("click", restartTaskbar);

async function loadMods() {
  $("whMissing").hidden = state.windhawk;
  $("whHow").hidden = !state.windhawk;
  $("mods").hidden = !state.windhawk;
  if (!state.windhawk) return;
  const mods = await api("/api/mods");
  $("mods").innerHTML = "";
  for (const m of mods) {
    const b = document.createElement("button");
    b.className = "mod" + (m.installed ? " installed" : "");
    b.innerHTML = `<div class="mod-name"></div><div class="mod-what"></div><span class="mod-tag"></span>`;
    b.querySelector(".mod-name").textContent = m.name;
    b.querySelector(".mod-what").textContent = m.what;
    b.querySelector(".mod-tag").textContent = m.installed ? (m.enabled ? "INSTALLED" : "TURNED OFF") : "GET IT";
    b.addEventListener("click", async () => {
      try {
        await api("/api/windhawk/open", { method: "POST" });
        say(m.installed
          ? `Opening Windhawk. "${m.name}" is in My Mods. Open its Settings to change it.`
          : `Opening Windhawk. Go to Explore, search "${m.name}", and click Install.`);
      } catch (e) {
        say(e.message, true);
      }
    });
    $("mods").appendChild(b);
  }
}

// Coming back from Windhawk? Re-check which mods are installed.
addEventListener("focus", () => {
  if (!$("tab-taskbar").classList.contains("hidden")) loadMods();
});

// ---------------------------------------------------------------- widgets

async function toggleWidget(w, el) {
  el.classList.add("busy");
  try {
    renderWidgets(await api("/api/widget", { method: "POST", body: { config: w.config, on: !w.active } }));
    state.widgets = (await api("/api/state")).widgets;
    say(w.active ? `${w.name} went to sleep.` : `${w.name} appeared on your desktop!`);
  } catch (e) {
    say(e.message, true);
  }
  el.classList.remove("busy");
}

function renderWidgets(data) {
  const mine = $("winuxWidgets");
  mine.innerHTML = "";
  for (const w of data.mine) {
    const b = document.createElement("button");
    b.className = "mod" + (w.active ? " on" : "");
    b.innerHTML = `<div class="mod-name"></div><div class="mod-what"></div><span class="mod-tag"></span>`;
    b.querySelector(".mod-name").textContent = w.name;
    b.querySelector(".mod-what").textContent = w.what;
    b.querySelector(".mod-tag").textContent = w.active ? "ON" : "OFF";
    b.addEventListener("click", () => toggleWidget(w, b));
    mine.appendChild(b);
  }

  // Group your widgets by their skin folder (Avengers, illustro, ...).
  const groups = {};
  for (const w of data.yours) (groups[w.config.split("\\")[0]] ||= []).push(w);
  const box = $("yourWidgets");
  box.innerHTML = Object.keys(groups).length ? "" : '<div class="empty">* None found.</div>';
  for (const [name, list] of Object.entries(groups)) {
    const g = document.createElement("div");
    g.className = "widget-group";
    g.innerHTML = `<div class="widget-group-name"></div><div class="widget-row"></div>`;
    g.querySelector(".widget-group-name").textContent = name.toUpperCase();
    for (const w of list) {
      const c = document.createElement("button");
      c.className = "chip" + (w.active ? " on" : "");
      c.textContent = w.config.includes("\\") ? w.config.split("\\").slice(1).join(" / ") : w.config;
      c.title = w.active ? "Click to turn off" : "Click to turn on";
      c.addEventListener("click", () => toggleWidget({ ...w, name: c.textContent }, c));
      g.querySelector(".widget-row").appendChild(c);
    }
    box.appendChild(g);
  }
}

async function loadWidgets() {
  $("rmMissing").hidden = state.rainmeter;
  $("rmBody").hidden = !state.rainmeter;
  if (state.rainmeter) renderWidgets(await api("/api/widgets"));
}

// ---------------------------------------------------------------- icons + cursors + sounds

const LOOK_SAYS = {
  cursors: { default: "Your cursor is back to normal.", pixel: "Your cursor went pixel.",
             "pixel-accent": "Your cursor matches your accent now.", soul: "Your cursor is a SOUL now. Stay determined." },
  icons: { default: "Desktop icons are back to normal.", pixel: "Your desktop icons went pixel. Check your desktop!" },
  sounds: { default: "Windows sounds are back.", chiptune: "Windows sounds 8-bit now. *blip*", silent: "Shhh. Windows is silent now." },
};

for (const group of document.querySelectorAll(".looks")) {
  for (const b of group.querySelectorAll(".look")) {
    b.addEventListener("click", async () => {
      if (group.dataset.key !== "appIcons") {
        return apply({ [group.dataset.key]: b.dataset.val }, LOOK_SAYS[group.dataset.key][b.dataset.val]);
      }
      // app icons take a few seconds, and Windows may ask for permission
      say("* Changing app icons... if Windows asks for permission, click Yes.");
      group.classList.add("busy");
      await apply({ appIcons: b.dataset.val });
      group.classList.remove("busy");
      const r = state.appIconsResult;
      if (!r) return;
      const done = b.dataset.val === "pixel"
        ? `${r.changed} app shortcuts went pixel!`
        : `${r.changed} app shortcuts are back to normal.`;
      say(r.admin ? done + " (Pinned taskbar icons may need RESTART TASKBAR.)"
                  : done + " Shared shortcuts and folders were skipped (no permission).");
    });
  }
}

const SOUND_TESTS = [["blip", "Click"], ["info", "Info"], ["warning", "Warning"], ["error", "Error"],
                     ["save", "Notification"], ["heal", "Mail"], ["plug-in", "USB in"], ["unplug", "USB out"], ["alert", "Allow?"]];
for (const [file, name] of SOUND_TESTS) {
  const c = document.createElement("button");
  c.className = "chip on";
  c.textContent = "▶ " + name;
  c.addEventListener("click", () => new Audio(`/gen/sounds/${file}.wav`).play());
  $("soundTests").appendChild(c);
}

function renderLooks() {
  $("accentCursorPic").src = `/gen/previews/cursors-pixel-accent.png?v=${(state.accent || "").slice(1)}`;
  for (const group of document.querySelectorAll(".looks")) {
    for (const b of group.querySelectorAll(".look")) b.classList.toggle("on", state[group.dataset.key] === b.dataset.val);
  }
}

// ---------------------------------------------------------------- art -> theme

function hsv(r, g, b) {
  const max = Math.max(r, g, b) / 255;
  const min = Math.min(r, g, b) / 255;
  return { s: max ? (max - min) / max : 0, v: max };
}

const toHex = (r, g, b) => "#" + [r, g, b].map((c) => Math.round(c).toString(16).padStart(2, "0")).join("");

function analyzeArt(img) {
  const size = 96;
  const scale = Math.min(1, size / Math.max(img.width, img.height));
  const w = Math.max(1, Math.round(img.width * scale));
  const h = Math.max(1, Math.round(img.height * scale));
  const c = document.createElement("canvas");
  c.width = w;
  c.height = h;
  const ctx = c.getContext("2d", { willReadFrequently: true });
  ctx.drawImage(img, 0, 0, w, h);
  const px = ctx.getImageData(0, 0, w, h).data;

  // Group similar colors into buckets and count them.
  const buckets = new Map();
  let lum = 0, seen = 0;
  for (let i = 0; i < px.length; i += 4) {
    if (px[i + 3] < 128) continue; // skip transparent pixels
    const [r, g, b] = [px[i], px[i + 1], px[i + 2]];
    lum += (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255;
    seen++;
    const key = (r >> 5) * 64 + (g >> 5) * 8 + (b >> 5);
    const k = buckets.get(key) || { r: 0, g: 0, b: 0, n: 0 };
    k.r += r; k.g += g; k.b += b; k.n++;
    buckets.set(key, k);
  }
  const colors = [...buckets.values()]
    .map((k) => ({ r: k.r / k.n, g: k.g / k.n, b: k.b / k.n, n: k.n }))
    .sort((a, b) => b.n - a.n);

  // Accent = the most eye-catching color that still shows up a decent amount.
  let best = null, bestScore = -1;
  for (const col of colors) {
    const { s, v } = hsv(col.r, col.g, col.b);
    if (v < 0.2) continue;
    const score = Math.sqrt(col.n) * (s * v + 0.04);
    if (score > bestScore) { best = col; bestScore = score; }
  }
  best = best || colors[0] || { r: 255, g: 230, b: 0 };

  return {
    colors: colors.slice(0, 10).map((c) => toHex(c.r, c.g, c.b)),
    accent: toHex(best.r, best.g, best.b),
    dark: seen ? lum / seen < 0.55 : true,
  };
}

function showArt(file) {
  if (!/\.(png|jpe?g|bmp)$/i.test(file.name)) {
    say("That one isn't a PNG or JPG. In FireAlpaca, use File → Export to save a PNG.", true);
    return;
  }
  const url = URL.createObjectURL(file);
  const img = new Image();
  img.onload = () => {
    const result = analyzeArt(img);
    art = { file, ...result };
    $("artPreview").src = url;
    $("artPreview").hidden = false;
    $("artDropText").hidden = true;
    $("artResult").hidden = false;
    $("artName").value = file.name.replace(/\.[^.]+$/, "").replace(/[_-]+/g, " ").slice(0, 40);
    renderArt();
    say("Your art is full of colors. Pick the accent you like, then apply it.");
  };
  img.src = url;
}

function renderArt() {
  const box = $("artColors");
  box.innerHTML = "";
  for (const hex of art.colors) {
    const s = swatch(hex, "", (h) => { art.accent = h; renderArt(); });
    s.querySelector(".swatch").classList.toggle("on", hex === art.accent);
    box.appendChild(s);
  }
  $("artSummary").textContent =
    `* Accent ${art.accent} · ${art.dark ? "Dark" : "Light"} mode (your art is mostly ${art.dark ? "dark" : "bright"})`;
}

$("artUpload").addEventListener("change", (e) => e.target.files[0] && showArt(e.target.files[0]));
const drop = $("artDrop");
drop.addEventListener("dragover", (e) => { e.preventDefault(); drop.classList.add("over"); });
drop.addEventListener("dragleave", () => drop.classList.remove("over"));
drop.addEventListener("drop", (e) => {
  e.preventDefault();
  drop.classList.remove("over");
  if (e.dataTransfer.files[0]) showArt(e.dataTransfer.files[0]);
});

$("artApply").addEventListener("click", async () => {
  if (!art) return;
  const btn = $("artApply");
  btn.disabled = true;
  try {
    const name = $("artName").value.trim() || "My Art";
    const settings = {
      appsDark: art.dark,
      systemDark: art.dark,
      transparency: true,
      accent: art.accent,
      accentOnTaskbar: art.dark,
      accentOnTitlebars: true,
    };
    if (state.ttb) Object.assign(settings, { tbStyle: "acrylic", tbColor: art.accent, tbOpacity: 20, tbMax: "same" });
    // Always keep the art in the inbox so Claude can look at it later.
    const { id } = await upload(art.file, "art");
    if ($("artUseWall").checked) {
      settings.wallpaper = id;
      settings.wallpaperStyle = $("artStyle").value;
    }
    await api("/api/themes", { method: "POST", body: { name, settings, blurb: "Made from my art." } });
    await apply(settings, `"${name}" is now your look, and it's saved in THEMES.`);
  } catch (e) {
    say(e.message, true);
  }
  btn.disabled = false;
});

// ---------------------------------------------------------------- themes

// Labels for wallpapers that do something special, top right of the thumbnail.
const EXTRA_LABELS = { playable: "▶ PLAYABLE", music: "♪ MUSIC" };
function addExtras(el, extras) {
  if (!extras || !extras.length) return;
  const box = document.createElement("div");
  box.className = "extras";
  for (const x of extras) {
    const tag = document.createElement("span");
    tag.className = "extra extra-" + x;
    tag.textContent = EXTRA_LABELS[x] || x.toUpperCase();
    box.appendChild(tag);
  }
  el.appendChild(box);
}

function themeCard(t, deletable) {
  const s = t.settings || {};
  const b = document.createElement("button");
  b.className = "theme";
  b.innerHTML = `
    <div class="theme-preview"><div class="theme-bar"></div></div>
    <div class="theme-body"><div class="theme-name"></div><div class="theme-blurb"></div></div>`;
  const preview = b.querySelector(".theme-preview");
  if (s.live) {
    const tag = document.createElement("span");
    tag.className = "theme-live";
    tag.textContent = "LIVE";
    preview.appendChild(tag);
  }
  if (s.live && s.live.startsWith("mine:")) {
    const f = document.createElement("iframe");
    f.src = liveFile(s.live);
    f.tabIndex = -1;
    preview.prepend(f);
  } else if (s.wallpaper) preview.style.backgroundImage = `url("${wallUrl(s.wallpaper)}")`;
  else preview.style.background = s.appsDark === false ? "#e9e9ee" : "#0b0b0d";
  addExtras(preview, t.extras);
  b.querySelector(".theme-bar").style.background = s.accent || "#888";
  if (t.wingdings) {
    wdSpan(b.querySelector(".theme-name"), t.name);
    wdSpan(b.querySelector(".theme-blurb"), t.blurb || "");
  } else {
    b.querySelector(".theme-name").textContent = t.name;
    b.querySelector(".theme-blurb").textContent = t.blurb || "";
  }
  b.addEventListener("click", () => apply(s, t.wingdings ? ["Switched to ", wd(t.name), "."] : `Switched to "${t.name}".`));

  if (deletable) {
    const del = document.createElement("span");
    del.className = "theme-del";
    del.textContent = "×";
    del.title = "Delete theme";
    del.addEventListener("click", async (e) => {
      e.stopPropagation();
      if (!confirm(`Delete the theme "${t.name}"?`)) return;
      await api("/api/themes?id=" + encodeURIComponent(t.id), { method: "DELETE" });
      say(`"${t.name}" is gone.`);
      loadThemes();
    });
    b.appendChild(del);

    // SHARE: download this theme as one .winux file (with its wallpaper inside)
    const share = document.createElement("span");
    share.className = "theme-share";
    share.textContent = "SHARE";
    share.title = "Save this theme as a file to send to friends";
    share.addEventListener("click", async (e) => {
      e.stopPropagation();
      try {
        const doc = await api("/api/theme-export?id=" + encodeURIComponent(t.id));
        const blob = new Blob([JSON.stringify(doc)], { type: "application/json" });
        const link = document.createElement("a");
        link.href = URL.createObjectURL(blob);
        link.download = (t.name || "theme").replace(/[^A-Za-z0-9 _-]+/g, "") + ".winux";
        link.click();
        setTimeout(() => URL.revokeObjectURL(link.href), 5000);
        say(`"${t.name}" saved as a .winux file. Send it to a friend!`);
      } catch (err) {
        say(err.message, true);
      }
    });
    b.appendChild(share);
  }
  return b;
}

// IMPORT THEME: open a .winux file a friend sent
$("importTheme").addEventListener("change", async (e) => {
  const file = e.target.files[0];
  e.target.value = "";
  if (!file) return;
  try {
    const doc = JSON.parse(await file.text());
    await api("/api/theme-import", { method: "POST", body: doc });
    say(`Imported "${doc.name || "a theme"}"! It's in Your themes. Click it to try it on.`);
    loadThemes();
  } catch (err) {
    say(err instanceof SyntaxError ? "That isn't a WinUx theme file." : err.message, true);
  }
});

async function loadThemes() {
  const { presets, mine } = await api("/api/themes");
  $("presetThemes").innerHTML = "";
  presets.forEach((t) => $("presetThemes").appendChild(themeCard(t, false)));
  $("myThemes").innerHTML = mine.length ? "" : '<div class="empty">* No themes yet. Save your current look!</div>';
  mine.forEach((t) => $("myThemes").appendChild(themeCard(t, true)));
}

$("saveTheme").addEventListener("click", async () => {
  const name = $("themeName").value.trim();
  if (!name) return say("Give your look a name first.", true);
  const keys = ["appsDark", "systemDark", "transparency", "accent", "accentOnTaskbar", "accentOnTitlebars", "wallpaperStyle",
                "taskbarAlign", "searchMode", "taskView", "autoHide", "cursors", "sounds", "icons"];
  if (state.ttb) keys.push("tbStyle", "tbColor", "tbOpacity", "tbLine", "tbMax");
  if (state.rainmeter) keys.push("widgets");
  const settings = Object.fromEntries(keys.map((k) => [k, state[k]]));
  if (state.wallpaper) settings.wallpaper = state.wallpaper;
  if (state.lively) settings.live = state.live && state.live !== "other" ? state.live : null;
  try {
    await api("/api/themes", { method: "POST", body: { name, settings } });
    $("themeName").value = "";
    say(`Saved "${name}". Click it anytime to come back to this look.`);
    loadThemes();
  } catch (e) {
    say(e.message, true);
  }
});

// ---------------------------------------------------------------- backup

$("restore").addEventListener("click", async () => {
  if (!confirm("Put Windows back exactly how it was before WinUx?")) return;
  try {
    state = { ...state, ...(await api("/api/restore", { method: "POST" })) };
    render();
    say(state.needsRestart
      ? "Everything is back. Click RESTART TASKBAR below to finish putting the taskbar back."
      : "Everything is back the way it was. Like nothing ever happened.");
  } catch (e) {
    say(e.message, true);
  }
});

$("refreshTaskbar").addEventListener("click", restartTaskbar);

function renderStartup(items) {
  const box = $("startupList");
  box.innerHTML = "";
  for (const [key, it] of Object.entries(items)) {
    if (!it.installed) continue;
    const row = document.createElement("label");
    row.className = "toggle";
    row.innerHTML = `<input type="checkbox"><span><b class="st-name"></b> <small class="st-what"></small></span>`;
    const cb = row.querySelector("input");
    cb.checked = it.on;
    cb.disabled = !!it.fixed;
    row.querySelector(".st-name").textContent = it.name;
    row.querySelector(".st-what").textContent = "- " + it.what;
    cb.addEventListener("change", async () => {
      try {
        renderStartup(await api("/api/startup", { method: "POST", body: { key, on: cb.checked } }));
        say(cb.checked ? `${it.name} will start when your PC turns on.` : `${it.name} won't start by itself anymore.`);
      } catch (e) {
        say(e.message, true);
      }
    });
    box.appendChild(row);
  }
}

document.querySelector('#menu button[data-tab="backup"]').addEventListener("click", async () =>
  renderStartup(await api("/api/startup"))
);

// ---------------------------------------------------------------- start

(async () => {
  try {
    state = await api("/api/state");
    render();
    say("Welcome to WinUx. Your original look is safely backed up. Pick something to change.");
  } catch (e) {
    say("Couldn't talk to the WinUx helper. Is it running?", true);
  }
})();
