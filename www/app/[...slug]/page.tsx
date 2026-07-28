import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { cachedGetArticle, getArticlePaths } from "@/lib/content";
import { formatDate } from "@/lib/utils";
import Nav from "@/components/Nav";
import CopyCodeBlock from "@/components/CopyCodeBlock";

// TODO:
import "./single.css";

export async function generateStaticParams() {
  const paths = await getArticlePaths();
  return paths.map((path) => ({
    slug: path.replaceAll("\\", "/").split("/").filter(Boolean),
  }));
}

export async function generateMetadata({
  params,
}: PageProps<"/[...slug]">): Promise<Metadata> {
  const { slug } = await params;
  const article = await cachedGetArticle(undefined, slug.join("/"));
  if (!article) return {};
  return {
    title: article.title,
    description: article.description ?? article.summary,
  };
}

function DateLabel({ date }: { date: Date }) {
  return <time dateTime={date.toISOString()}>{formatDate(date)}</time>;
}

export default async function Article({ params }: PageProps<"/[...slug]">) {
  const { slug } = await params;
  const article = await cachedGetArticle(undefined, slug.join("/"));

  if (article == null) {
    notFound();
  }

  return (
    <>
      <link
        rel="stylesheet"
        href="https://cdn.jsdelivr.net/npm/katex@0.18.1/dist/katex.min.css"
      />
      <CopyCodeBlock />
      <Nav />
      <h1 className="post-title">{article.title}</h1>
      <hr />
      <p className="post-info">
        <span className="created">
          <DateLabel date={article.date} />
        </span>
        | <span className="words">{article.wordCount} words</span>
        {article.lastmod &&
          article.lastmod.getTime() !== article.date.getTime() && (
            <span className="last-updated">
              Last updated: <DateLabel date={article.lastmod} />
            </span>
          )}
      </p>
      <div dangerouslySetInnerHTML={{ __html: article.renderedHtml }} />
    </>
  );
}
