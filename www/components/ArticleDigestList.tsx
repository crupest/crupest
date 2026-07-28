import { Fragment, type ElementType } from "react";

import ArticleDigest, { ArticleDigestProps } from "./ArticleDigest";

import styles from "./article-digest.module.css";

export type ArticleDigestListProps = {
  articles: ArticleDigestProps["article"][];
} & {
  headingComponent?: ElementType;
};

export default function ArticleDigestList(props: ArticleDigestListProps) {
  return (
    <>
      {props.articles.map((article, i) => (
        <Fragment key={article.path}>
          {i > 0 && <hr className={styles["article-digest-hr"]} />}
          <ArticleDigest
            article={article}
            headingComponent={props.headingComponent}
          />
        </Fragment>
      ))}
    </>
  );
}
