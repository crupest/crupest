import { Metadata } from "next";

import { getArticles, parseArticles } from "@/lib/content";
import ArticleDigestList from "@/components/ArticleDigestList";
import Nav from "@/components/Nav";

export const metadata: Metadata = {
  title: "Posts",
  description: "List of Posts",
};

export default async function Posts() {
  const articles = await getArticles({
    postOnly: true,
    sort: true,
  });
  // Currently we don't do pagination, so all articles have to be parsed.
  const parsedArticles = await parseArticles(articles);

  return (
    <>
      <Nav slug={["posts"]} />
      <h1>Posts</h1>
      <hr />
      <ArticleDigestList articles={parsedArticles} headingComponent="h2" />
    </>
  );
}
