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
      const span = document.createElement("span");
      span.textContent = status;
      span.style.color = color;
      li.appendChild(span);
      li.append(title);
      todoContainer.appendChild(li);
    });

    todoMessage.parentElement.removeChild(todoMessage);
  }
});
