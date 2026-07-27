"use client";

import { useEffect } from "react";

declare global {
  interface Window {
    copyCodeBlock?: (codeBlockCount: number) => void;
  }
}

/**
 * Exposes `copyCodeBlock` on `window` so inline `onclick` handlers
 * in rendered markdown can call it. Needed because Next.js bundles
 * modules — raw HTML can't reach imports, only globals.
 */
export default function CopyCodeBlock() {
  useEffect(() => {
    window.copyCodeBlock = function (codeBlockCount: number) {
      const codeBlock = document.getElementById(`code-block-${codeBlockCount}`);
      if (!codeBlock) return;

      const code = codeBlock.querySelector("pre");
      if (!code) return;

      navigator.clipboard.writeText(code.textContent);
    };

    return () => {
      delete window.copyCodeBlock;
    };
  }, []);

  return null;
}
