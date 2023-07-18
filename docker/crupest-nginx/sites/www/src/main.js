import "./style.css";

const happy = "happy";
const angry = "angry";

function emotionOpposite(emotion) {
  if (emotion === happy) {
    return angry;
  } else if (emotion === angry) {
    return happy;
  }
}

function emotionElement(emotion) {
  return document.querySelector(`.slogan.${emotion}`);
}

function emotionElementHeight(emotion) {
  return emotionElement(emotion).clientHeight;
}

function setBodyPaddingForEmotion(emotion) {
  document.body.style.paddingTop = `${emotionElementHeight(emotion)}px`;
}

const sloganEmotionKey = "sloganEmotion";

const savedEmotion = localStorage.getItem(sloganEmotionKey) ?? happy;
if (savedEmotion !== happy && savedEmotion !== angry) {
  console.error(`Invalid saved emotion: ${savedEmotion}`);
}

setBodyPaddingForEmotion(savedEmotion);
setTimeout(() => {
  document.body.style.transition = "padding-top 1s";
})

/** @type {HTMLDivElement} */
const sloganContainer = document.querySelector(".slogan-container")

setTimeout(() => {
  sloganContainer.dataset.sloganEmotion = savedEmotion;
  setBodyPaddingForEmotion(savedEmotion);
}, 500);

for (const emotion of [happy, angry]) {
  emotionElement(emotion).addEventListener("click", () => {
    const opposite = emotionOpposite(emotion);
    localStorage.setItem(sloganEmotionKey, opposite);
    sloganContainer.dataset.sloganEmotion = opposite;
    setBodyPaddingForEmotion(opposite);
  });
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
