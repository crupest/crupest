import { Fragment, type ElementType } from "react";

import { Article } from "@/lib/content";
import { formatDate } from "@/lib/utils";

import styles from "./article-digest.module.css";

export interface ArticleDigestProps {
  article: Pick<Article, "date" | "title" | "summary" | "path">;
  headingComponent?: ElementType;
}

export default function ArticleDigest(props: ArticleDigestProps) {
  const Heading = props.headingComponent ?? "h2";
  const article = props.article;

  return (
    <section className={styles["article-digest"]}>
      <span className={styles["date"]}>{formatDate(article.date)}</span>
      <Heading className={styles["title"]}>
        <a href={article.path}>{article.title}</a>
      </Heading>
      <p className={styles["content"]}>
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
