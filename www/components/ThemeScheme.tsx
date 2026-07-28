"use client";

import { useEffect, useRef, useState } from "react";

import Toast from "./Toast";

type Theme = "dark" | "light";

const localStorageKey = "force-color-scheme";

function fromMediaQuery(value: boolean | null) {
  if (value == null)
    value = window.matchMedia("(prefers-color-scheme: dark)").matches;
  return value ? "dark" : "light";
}

function applyScheme(theme: Theme | null) {
  if (theme == null) theme = fromMediaQuery(null);
  document.querySelector("html")!.dataset["theme"] = theme;
  return theme;
}

function getScheme(): Theme | null {
  const saved = localStorage.getItem(localStorageKey);
  if ([null, "dark", "light"].includes(saved)) {
    return saved as Theme | null;
  } else {
    console.log("invalid saved theme: " + saved);
    localStorage.removeItem(localStorageKey);
    return null;
  }
}

function setScheme(value: Theme | null): { message: string } {
  if (value == null) {
    localStorage.removeItem(localStorageKey);
  } else {
    localStorage.setItem(localStorageKey, value);
  }

  const real = applyScheme(value);
  return {
    message:
      "theme: " + (value == null ? "system" : "force") + "(" + real + ")",
  };
}

function next(value: Theme | null) {
  function opposite(scheme: Theme) {
    return scheme === "dark" ? "light" : "dark";
  }

  const sys = fromMediaQuery(null);
  if (value == null) {
    return opposite(sys);
  } else {
    if (value === sys) {
      return null;
    } else {
      return opposite(value);
    }
  }
}

export default function ThemeScheme() {
  const [message, setMessage] = useState<string>("");
  const toastTimer = useRef<number | null>(null);

  useEffect(() => {
    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
    applyScheme(getScheme());
    const mediaQueryChangeHandler = (e: globalThis.MediaQueryListEvent) => {
      if (getScheme() == null) {
        applyScheme(fromMediaQuery(e.matches));
      }
    };
    mediaQuery.addEventListener("change", mediaQueryChangeHandler);

    const keyDownHandler = (e: globalThis.KeyboardEvent) => {
      if (e.key === "t" && !e.ctrlKey && !e.metaKey && !e.altKey) {
        const tag = (e.target as HTMLElement | null)?.tagName;
        if (tag === "INPUT" || tag === "TEXTAREA") return;
        if (toastTimer.current) window.clearTimeout(toastTimer.current);
        const { message } = setScheme(next(getScheme()));
        setMessage(message);
        toastTimer.current = window.setTimeout(() => setMessage(""), 3000);
      }
    };
    document.addEventListener("keydown", keyDownHandler);

    return () => {
      if (toastTimer.current) window.clearTimeout(toastTimer.current);
      mediaQuery.removeEventListener("change", mediaQueryChangeHandler);
      document.removeEventListener("keydown", keyDownHandler);
    };
  }, []);

  return <>{message && <Toast message={message} />}</>;
}
