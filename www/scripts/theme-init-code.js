const key = "force-color-scheme";
let theme = localStorage.getItem(key);
if (![null, "dark", "light"].includes(theme)) {
  console.log("invalid saved theme: " + theme);
  localStorage.removeItem(key);
  theme = null;
}
if (theme == null) {
  theme = window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}
document.documentElement.dataset["theme"] = theme;
