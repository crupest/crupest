"use client";

import { ReactNode, useEffect, useRef, useState } from "react";

import styles from "./code-block.module.css";

export default function CodeBlockClient({
  language,
  children,
}: {
  language: string;
  children: ReactNode;
}) {
  const pre = useRef<HTMLPreElement | null>(null);
  const [clipboardCheck, setClipboardCheck] = useState<boolean>(false);
  const clipboardAnimationTimer = useRef<number | null>(null);

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
          {language}
        </span>
        <button
          className={styles["clipboard-button"]}
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
        >
          {clipboardCheck ? (
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="16"
              height="16"
              fill="currentColor"
              className="bi bi-clipboard-check"
              viewBox="0 0 16 16"
            >
              <path
                fillRule="evenodd"
                d="M10.854 7.146a.5.5 0 0 1 0 .708l-3 3a.5.5 0 0 1-.708 0l-1.5-1.5a.5.5 0 1 1 .708-.708L7.5 9.793l2.646-2.647a.5.5 0 0 1 .708 0"
              />
              <path d="M4 1.5H3a2 2 0 0 0-2 2V14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V3.5a2 2 0 0 0-2-2h-1v1h1a1 1 0 0 1 1 1V14a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V3.5a1 1 0 0 1 1-1h1z" />
              <path d="M9.5 1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-3a.5.5 0 0 1-.5-.5v-1a.5.5 0 0 1 .5-.5zm-3-1A1.5 1.5 0 0 0 5 1.5v1A1.5 1.5 0 0 0 6.5 4h3A1.5 1.5 0 0 0 11 2.5v-1A1.5 1.5 0 0 0 9.5 0z" />
            </svg>
          ) : (
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="16"
              height="16"
              fill="currentColor"
              className="bi bi-clipboard"
              viewBox="0 0 16 16"
            >
              <path d="M4 1.5H3a2 2 0 0 0-2 2V14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V3.5a2 2 0 0 0-2-2h-1v1h1a1 1 0 0 1 1 1V14a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V3.5a1 1 0 0 1 1-1h1z" />
              <path d="M9.5 1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-3a.5.5 0 0 1-.5-.5v-1a.5.5 0 0 1 .5-.5zm-3-1A1.5 1.5 0 0 0 5 1.5v1A1.5 1.5 0 0 0 6.5 4h3A1.5 1.5 0 0 0 11 2.5v-1A1.5 1.5 0 0 0 9.5 0z" />
            </svg>
          )}
        </button>
      </div>
      <pre ref={pre}>{children}</pre>
    </div>
  );
}
