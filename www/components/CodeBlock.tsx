import { ReactNode } from "react";
import parse from "node-html-parser";

import CodeBlockClient from "./CodeBlockClient";

export default async function CodeBlock({ children }: { children: ReactNode }) {
  const ReactDOMServer = (await import("react-dom/server")).default;
  const htmlString = ReactDOMServer.renderToStaticMarkup(children);
  let language = "";
  const root = parse(htmlString);
  for (const className of root.firstElementChild!.classList.values()) {
    const prefix = "language-";
    if (className.startsWith(prefix)) {
      language = className.slice(prefix.length);
      break;
    }
  }

  return <CodeBlockClient language={language}>{children}</CodeBlockClient>;
}
