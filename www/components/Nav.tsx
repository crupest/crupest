import { Fragment } from "react";
import Link from "next/link";

interface BreadcrumbItem {
  name: string;
  href: string;
}

function buildBreadcrumbs(slug: string[]): BreadcrumbItem[] {
  const crumbs: BreadcrumbItem[] = [{ name: "home", href: "/" }];

  for (let i = 0; i < slug.length; i++) {
    crumbs.push({
      name: slug[i],
      href: "/" + slug.slice(0, i + 1).join("/") + "/",
    });
  }

  return crumbs;
}

export default function Nav({ slug }: { slug: string[] }) {
  const crumbs = buildBreadcrumbs(slug);

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
