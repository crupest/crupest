import { ReactNode } from "react";
import parse from "node-html-parser";

import styles from "./code-block.module.css";
import CopyButton from "./CopyButton";

export default async function CodeBlock({ children }: { children: ReactNode }) {
  const ReactDOMServer = (await import("react-dom/server")).default;
  const htmlString = ReactDOMServer.renderToStaticMarkup(children);
  let language = "";
  const root = parse(htmlString);
  const codeElement = root.firstElementChild!;
  for (const className of codeElement.classList.values()) {
    const prefix = "language-";
    if (className.startsWith(prefix)) {
      language = className.slice(prefix.length);
      break;
    }
  }
  let code = codeElement.textContent;
  if (code.length > 0 && code.at(-1) === "\n") {
    code = code.slice(0, -1);
  }

  return (
    <div className={styles.codeblock}>
      <div>
        <span className={styles["lang-label"]}>{language}</span>
        <CopyButton copyText={code} className={styles["clipboard-button"]} />
      </div>
      <pre>{children}</pre>
    </div>
  );
}
