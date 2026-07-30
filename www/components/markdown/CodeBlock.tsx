import { ReactNode } from "react";

import styles from "./code-block.module.css";
import CopyButton from "./CodeCopyButton";

export default function CodeBlock({
  children,
  "data-language": language = "",
  ...props
}: {
  "data-language"?: string;
  children: ReactNode;
}) {
  return (
    <div className={styles.codeblock}>
      <div>
        <span className={styles["lang-label"]}>{language}</span>
        <CopyButton className={styles["clipboard-button"]} />
      </div>
      <pre {...props}>{children}</pre>
    </div>
  );
}
