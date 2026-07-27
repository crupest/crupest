import { Fragment, type ElementType } from "react";

import ArticleDigest, { ArticleDigestProps } from "./ArticleDigest";

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
          {i > 0 && <hr className="article-digest-hr" />}
          <ArticleDigest
            article={article}
            headingComponent={props.headingComponent}
          />
        </Fragment>
      ))}
    </>
  );
}
