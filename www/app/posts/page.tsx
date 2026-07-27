import { getArticles } from "@/lib/content";
import ArticleDigestList from "@/components/ArticleDigestList";
import Nav from "@/components/Nav";

// TODO:
import "../article.css";

export const metadata = {
  title: "Posts",
  description: "List of Posts",
};

export default async function Posts() {
  const articles = await getArticles({
    postOnly: true,
    sort: true,
  });

  return (
    <>
      <Nav />
      <h1>Posts</h1>
      <hr />
      <ArticleDigestList articles={articles} headingComponent="h2" />
    </>
  );
}
