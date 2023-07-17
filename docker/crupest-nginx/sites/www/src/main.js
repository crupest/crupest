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

/** @type {HTMLDivElement} */
const sloganElement = document.querySelector("#slogan");
const sloganTextElement = document.querySelector("#slogan .slogan-text");

/** @type {"good" | "bad"} */
let sloganState = "good";
const slogans = {
  "good": sloganTextElement.textContent,
  "bad": "The world is a piece of shit, so let's make it a little better!"
}

function toggleSlogan() {
  const newState = sloganState === "good" ? "bad" : "good";
  sloganElement.classList.remove(sloganState)
  sloganElement.classList.add(newState);
  sloganTextElement.textContent = slogans[newState];
  sloganState = newState;
}

sloganElement.addEventListener("click", toggleSlogan);


document.addEventListener("DOMContentLoaded", async () => {
  console.log("Try to fetch GitHub project(number: 2) of crupest.");

  const todoMessage = document.getElementById("todo-message");
  const todoContainer = document.getElementById("todo-container");

  const res = await fetch("/api/todos");
  const body = await res.json();

  if (res.status !== 200) {
    todoMessage.style.color = "red";
    todoMessage.textContent =
      "Failed to fetch TODOs. (Maybe due to rate limit. Please try later.)";
    console.log(
      `Failed to get GitHub project info. Status: ${res.status}. Body: ${body}`
    );
  } else {
    body.forEach((item) => {
      const { status, title, color } = item;
      const li = document.createElement("li");
      const statusSpan = document.createElement("span");
      const titleSpan = document.createElement("span");
      statusSpan.textContent = status;
      statusSpan.style.color = color;
      titleSpan.textContent = title;
      li.appendChild(statusSpan);
      li.append(" : ");
      li.append(titleSpan);
      todoContainer.appendChild(li);
    });

    todoMessage.parentElement.removeChild(todoMessage);
  }
});
