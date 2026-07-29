"use client";

import { usePathname } from "next/navigation";

import Nav from "./Nav";

export default function NavClient() {
  const pathname = usePathname();
  const slug = pathname.split("/").filter(Boolean);

  return <Nav slug={slug} />;
}
