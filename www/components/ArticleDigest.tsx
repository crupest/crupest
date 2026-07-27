import { Fragment, type ElementType } from "react";

import { Article } from "@/lib/content";
import { formatDate } from "@/lib/utils";

export interface ArticleDigestProps {
  article: Pick<Article, "date" | "title" | "summary" | "path">;
  headingComponent?: ElementType;
}

export default function ArticleDigest(props: ArticleDigestProps) {
  const Heading = props.headingComponent ?? "h2";
  const article = props.article;

  return (
    <section className="article-digest">
      <span className="date">{formatDate(article.date)}</span>
      <Heading className="title">
        <a href={article.path}>{article.title}</a>
      </Heading>
      <p className="content">
        {article.summary.split("\n").map((l, i) => (
          <Fragment key={i}>
            {l} <br />
          </Fragment>
        ))}
      </p>
      <p>
        {"... "}
        <a className="mono-link" href={article.path}>
          Read more
        </a>
      </p>
    </section>
  );
}
