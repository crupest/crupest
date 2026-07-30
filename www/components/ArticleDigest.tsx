import { Fragment, type ElementType } from "react";
import Link from "next/link";

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
  const summaryLines = article.summary.split("\n");

  return (
    <section className={styles["article-digest"]}>
      <span className={styles["date"]}>{formatDate(article.date)}</span>
      <Heading className={styles["title"]}>
        <Link href={article.path}>{article.title}</Link>
      </Heading>
      <p className={styles["content"]}>
        {summaryLines.map((l, i) => (
          <Fragment key={i}>
            {l} {i !== summaryLines.length - 1 && <br />}
          </Fragment>
        ))}
        {" ... "}
        <Link className="mono-link" href={article.path}>
          Read more
        </Link>
      </p>
    </section>
  );
}
