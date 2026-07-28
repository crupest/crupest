"use client";

import { ReactNode, useEffect, useRef, useState } from "react";
import clsx from "clsx";

import styles from "./code-block.module.css";

export default function CodeBlock({ children }: { children: ReactNode }) {
  const [lang, setLang] = useState<string>("");
  const pre = useRef<HTMLPreElement | null>(null);
  const [clipboardCheck, setClipboardCheck] = useState<boolean>(false);
  const clipboardAnimationTimer = useRef<number | null>(null);

  // We assume language is never changed here, though the correct deps
  // should be `[children]` or the class list of the code element.
  useEffect(() => {
    const codeElement = pre.current?.firstElementChild;
    if (!codeElement) return;
    for (const className of codeElement.classList) {
      const prefix = "language-";
      if (className.startsWith(prefix)) {
        setLang(className.slice(prefix.length));
        break;
      }
    }
  }, []);

  useEffect(() => {
    return () => {
      if (clipboardAnimationTimer.current != null) {
        window.clearTimeout(clipboardAnimationTimer.current);
      }
    };
  }, []);

  return (
    <div className={styles.codeblock}>
      <div>
        <span className={styles["lang-label"]} suppressHydrationWarning>
          {lang}
        </span>
        <button
          className={clsx(
            styles["clipboard-button"],
            clipboardCheck && styles["clipboard-button-check"],
          )}
          onClick={() => {
            const codeElement = pre.current?.firstElementChild;
            if (!codeElement) return;
            let text = codeElement.textContent;
            if (text.length > 0 && text.at(-1) === "\n") {
              text = text.slice(0, -1);
            }
            void navigator.clipboard.writeText(text).then(() => {
              setClipboardCheck(true);
              clipboardAnimationTimer.current = window.setTimeout(() => {
                setClipboardCheck(false);
              }, 3000);
            });
          }}
          aria-label="Copy following code"
        />
      </div>
      <pre ref={pre}>{children}</pre>
    </div>
  );
}
