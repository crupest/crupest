import Image from "next/image";
import Link from "next/link";

import ThemeScheme from "@/components/ThemeScheme";

import "./base.css";

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html suppressHydrationWarning>
      <head>
        <meta charSet="utf-8" />
        <meta httpEquiv="X-UA-Compatible" content="IE=edge" />
        <link rel="icon" href="/favicon.ico" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <script
          dangerouslySetInnerHTML={{
            __html: `(()=>{var e="force-color-scheme",l=localStorage.getItem(e);[null,"dark","light"].includes(l)||(console.log("invalid saved theme: "+l),localStorage.removeItem(e),l=null),null==l&&(l=window.matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light"),document.documentElement.dataset.theme=l;})()`,
          }}
        />
      </head>
      <body>
        <ThemeScheme />
        <article id="main-article">
          {children}
          <hr />
          <footer className="mono-link">
            <p id="license">
              <small>
                This work is licensed under{" "}
                <Link
                  rel="license noopener noreferrer"
                  href="https://creativecommons.org/licenses/by-nc/4.0/"
                  target="_blank"
                >
                  <span id="license-text">CC BY-NC 4.0</span>{" "}
                  <span id="license-img-container">
                    <Image
                      src="https://mirrors.creativecommons.org/presskit/icons/cc.svg"
                      alt="License by-nc cc icon"
                      width="10"
                      height="10"
                    />{" "}
                    <Image
                      src="https://mirrors.creativecommons.org/presskit/icons/by.svg"
                      alt="License by-nc by icon"
                      width="10"
                      height="10"
                    />{" "}
                    <Image
                      src="https://mirrors.creativecommons.org/presskit/icons/nc.svg"
                      alt="License by-nc nc icon"
                      width="10"
                      height="10"
                    />
                  </span>
                </Link>
              </small>
            </p>
          </footer>
        </article>
      </body>
    </html>
  );
}
