import "./style.css";

import { fetchTodos } from "./todos";

const happy = "happy" as const;
const angry = "angry" as const;
type Emotion = typeof happy | typeof angry;

function emotionOpposite(emotion: Emotion): Emotion {
  if (emotion === happy) {
    return angry;
  } else {
    return happy;
  }
}

function emotionElement(emotion: Emotion): HTMLDivElement {
  return document.querySelector<HTMLDivElement>(`.slogan.${emotion}`)!;
}

function emotionElementHeight(emotion: Emotion): number {
  return emotionElement(emotion).clientHeight;
}

function updateBodyTopPadding(emotion: Emotion): void {
  document.body.style.paddingTop = `${emotionElementHeight(emotion)}px`;
}

const sloganEmotionKey = "sloganEmotion";

const savedEmotion =
  (localStorage.getItem(sloganEmotionKey) as Emotion | null) ?? happy;
if (savedEmotion !== happy && savedEmotion !== angry) {
  console.error(`Invalid saved emotion: ${savedEmotion}`);
}

updateBodyTopPadding(savedEmotion);
// Then we add transition animation.
setTimeout(() => {
  document.body.style.transition = "padding-top 1s";
});

const sloganContainer = document.querySelector(
  ".slogan-container"
) as HTMLDivElement;

setTimeout(() => {
  sloganContainer.dataset.sloganEmotion = savedEmotion;
}, 500);

const sloganLoadedPromise = new Promise<void>((resolve) => {
  setTimeout(() => {
    resolve();
  }, 1500);
});

for (const emotion of [happy, angry]) {
  emotionElement(emotion).addEventListener("click", () => {
    const opposite = emotionOpposite(emotion);
    localStorage.setItem(sloganEmotionKey, opposite);
    sloganContainer.dataset.sloganEmotion = opposite;
    updateBodyTopPadding(opposite);
  });
}

async function loadTodos(syncWith: Promise<unknown>): Promise<void> {
  const todoMessage = document.getElementById("todo-message")!;
  const todoContainer = document.getElementById("todo-container")!;

  try {
    const todosPromise = fetchTodos();
    await syncWith; // Let's wait this first.
    const todos = await todosPromise;
    todos.forEach((item) => {
      const { status, title, closed } = item;
      const li = document.createElement("li");
      li.dataset.status = closed ? "closed" : "open";
      // The color from api server is kind of ugly at present.
      // li.style.background = color;
      const statusSpan = document.createElement("span");
      const titleSpan = document.createElement("span");
      statusSpan.textContent = status;
      titleSpan.textContent = title;
      li.appendChild(statusSpan);
      li.append(" : ");
      li.append(titleSpan);
      todoContainer.appendChild(li);
    });
    todoMessage.parentElement!.removeChild(todoMessage);
  } catch (e) {
    todoMessage.style.color = "red";
    todoMessage.textContent = (e as Error).message;
  }
}

loadTodos(sloganLoadedPromise);
