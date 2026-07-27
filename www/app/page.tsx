import { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import clsx from "clsx";

import { getArticles } from "@/lib/content";
import ArticleDigestList from "@/components/ArticleDigestList";

import avatar from "./avatar.png";
import ghIcon from "./github.png";

import styles from "./page.module.css";

interface FriendProps {
  name: string;
  avatar: string;
  github: string;
  url?: string;
  tag?: string;
}

function Friend(props: FriendProps) {
  const ghUrl = `https://github.com/${props.github}`;
  const linkUrl = props.url ?? ghUrl;
  return (
    <div className={styles["friend"]}>
      <a rel="noopener noreferrer" href={linkUrl}>
        <Image
          className={styles["friend-avatar"]}
          alt={"Friend " + props.name + "'s avatar"}
          src={props.avatar}
          width="80"
          height="80"
        />
        <br />
        {props.name}
      </a>{" "}
      <a rel="noopener noreferrer" href={ghUrl}>
        <Image
          className={styles["friend-github"]}
          src={ghIcon}
          alt="github logo"
        />
      </a>
      <br />
      {props.tag && <span className={styles["friend-tag"]}>{props.tag}</span>}
    </div>
  );
}

export const metadata: Metadata = {
  title: "crupest's life",
  description: "crupest's Home Page",
};

export default async function Home() {
  const articles = await getArticles({
    postOnly: true,
    sort: true,
  });

  return (
    <>
      <Image
        className={styles["avatar"]}
        src={avatar}
        loading="eager"
        alt="My avatar"
        width="80"
        height="80"
      />
      <h1 id="title">
        Hello! This is <code>crupest</code> !
      </h1>
      <hr />
      <section>
        <p>Welcome to my home page! Nice to meet you here! 🥰</p>
        <p>
          Feel free to contact me via my email address{" "}
          <Link href="mailto:crupest@crupest.life">crupest@crupest.life</Link>,
          or just create an issue in any of my{" "}
          <Link rel="noopener noreferrer" href="https://github.com/crupest">
            GitHub
          </Link>{" "}
          repos. I love talking with people a lot.
        </p>
        <div className={clsx(styles["links"], "mono-link")}>
          goto:
          <ul>
            <li>
              <Link href="/git/">git</Link>
            </li>
            <li>
              <Link href="/notes/">notes</Link>
            </li>
            <li>
              <Link href="/notes/cheat-sheet/">cheat-sheet</Link>
            </li>
          </ul>
        </div>
      </section>
      <hr />
      <section className={styles["recent-posts"]}>
        <h2>
          Recent Posts{" "}
          <Link className="mono-link" href="/posts/">
            (all)
          </Link>
        </h2>
        <ArticleDigestList articles={articles} headingComponent="h3" />
      </section>
      <hr />
      <section>
        <h2 id="friends">
          My Friends <small>(more links are being collected ...)</small>
        </h2>
        <div className={styles["friends-container"]}>
          <Friend
            name="wsm"
            avatar="https://avatars.githubusercontent.com/u/74699943?v=4"
            github="wushuming666"
          />
          <Friend
            name="hsz"
            url="https://www.hszsoft.com"
            avatar="https://avatars.githubusercontent.com/u/63097618?v=4"
            github="hszSoft"
            tag="随性の程序员"
          />
        </div>
      </section>
    </>
  );
}
