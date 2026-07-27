"use client";

import { Fragment } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

interface BreadcrumbItem {
  name: string;
  href: string;
}

function buildBreadcrumbs(path: string): BreadcrumbItem[] {
  const parts = path.split("/").filter(Boolean);
  const crumbs: BreadcrumbItem[] = [{ name: "home", href: "/" }];

  for (let i = 0; i < parts.length; i++) {
    crumbs.push({
      name: parts[i],
      href: "/" + parts.slice(0, i + 1).join("/") + "/",
    });
  }

  return crumbs;
}

export default function Nav() {
  const pathname = usePathname();
  const crumbs = buildBreadcrumbs(pathname);

  return (
    <nav className="mono">
      {crumbs.slice(0, -1).map((c) => (
        <Fragment key={c.href}>
          <Link className="mono-link" href={c.href}>
            {c.name}
          </Link>
          {" > "}
        </Fragment>
      ))}
      this
    </nav>
  );
}
