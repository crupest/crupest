// deno-lint-ignore-file no-window

// Color scheme (dark/light theme) switcher
// This script runs in the browser and manages theme switching

function createResetTimer(cleanup, timeout = 1) {
  let tag = 0;
  return () => {
    clearTimeout(tag);
    tag = setTimeout(() => {
      cleanup();
    }, timeout * 1000);
  };
}

function createToast(duration = 1) {
  const toast = document.createElement("div");
  toast.className = "toast";

  const reset = createResetTimer(() => {
    toast.remove();
  }, duration);

  return (text) => {
    if (!toast.isConnected) {
      document.body.appendChild(toast);
    }
    toast.textContent = text;
    reset();
  };
}

const setToast = createToast();

const key = "force-color-scheme";
const dark = "dark";
const light = "light";

const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");

function fromMediaQuery(value) {
  if (value == null) value = mediaQuery.matches;
  return value ? dark : light;
}

function opposite(scheme) {
  return scheme === dark ? light : dark;
}

function updateScheme(theme) {
  if (theme == null) theme = fromMediaQuery(null);
  document.querySelector("html").dataset["theme"] = theme;
  return theme;
}

mediaQuery.addEventListener(
  "change",
  (e) => updateScheme(current || fromMediaQuery(e.matches)),
);

let current = null;

{
  const saved = localStorage.getItem(key);
  if ([null, dark, light].includes(saved)) {
    current = saved;
  } else {
    console.log("invalid saved theme: " + saved);
    localStorage.removeItem(key);
  }
}

updateScheme(current);

function saveScheme(value) {
  current = value;

  if (value == null) {
    localStorage.removeItem(key);
  } else {
    localStorage.setItem(key, value);
  }

  const real = updateScheme(value);
  setToast(
    "theme: " + (current == null ? "system" : "force") + "(" + real + ")",
  );
}

function next() {
  const sys = fromMediaQuery(null);
  if (current == null) {
    return opposite(sys);
  } else {
    if (current === sys) {
      return null;
    } else {
      return opposite(current);
    }
  }
}

// Make theme toggle available via keyboard shortcut or click
document.addEventListener("keydown", (e) => {
  if (e.key === "t" && !e.ctrlKey && !e.metaKey && !e.altKey) {
    const target = e.target;
    if (
      target && (target.tagName === "INPUT" || target.tagName === "TEXTAREA")
    ) return;
    saveScheme(next());
  }
});
