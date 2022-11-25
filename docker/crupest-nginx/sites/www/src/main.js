import { Octokit } from "https://cdn.skypack.dev/octokit";
import "./style.css";

const colorStripContainer = document.getElementById("color-strip-container");

const colorStripText = "FANCYSTRIP";

for (let i = 0; i < 10; i++) {
  const colorStripBlock = document.createElement("span");

  const hsl = `hsl(${i * 36}, 100%, 50%)`;
  colorStripBlock.classList.add("color-strip-block");
  colorStripBlock.style.backgroundColor = hsl;
  colorStripBlock.textContent = colorStripText[i];
  colorStripContainer.appendChild(colorStripBlock);
}

document.addEventListener("DOMContentLoaded", async () => {
  console.log("Try to fetch GitHub project(number: 2) of crupest.");

  const todoMessage = document.getElementById("todo-message");
  const todoContainer = document.getElementById("todo-container");

  // TODO: we need another way to do this! 
  const octokit = new Octokit({
    auth: "xxx",
  });

  try {
    const res = await octokit.graphql(
      `
    {
      user(login: "crupest") {
        projectV2(number: 2) {
          items(last: 100) {
            nodes {
              __typename
              fieldValueByName(name: "Status")
              content {
                __typename
                ... on Issue {
                  title
                  closed
                }
                ... on PullRequest {
                  title
                  closed
                }
                ... on DraftIssue {
                  title
                }
              }
            }
          }
        }
      }
    }
    `
    );

    const items = res.user.projectV2.items.nodes.map((node) => node.content);

    items.forEach((item) => {
      if (item.__typename == "DraftIssue") {
        item.closed = false;
      }
      const { title, closed } = item;
      const li = document.createElement("li");
      const span = document.createElement("span");
      span.textContent = closed ? "Done:" : "Todo:";
      span.style.color = closed ? "green" : "blue";
      li.appendChild(span);
      li.append(title);
      todoContainer.appendChild(li);
    });

    todoMessage.parentElement.removeChild(todoMessage);
  } catch (e) {
    todoMessage.style.color = "red";
    todoMessage.textContent = "Failed to fetch TODOs.";
    console.log("Failed to get GitHub project info.", e);
  }
});
