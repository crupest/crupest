import "./style.css";

class Emotion {
  static opposite_map = new Map<Emotion, Emotion>();

  constructor(public readonly name: string) {
  }

  get opposite(): Emotion {
    return Emotion.opposite_map.get(this)!;
  }

  get element(): HTMLDivElement {
    return document.querySelector<HTMLDivElement>(`.slogan.${this.name}`)!
  }

  get elementHeight(): number {
    return this.element.clientHeight;
  }

  apply() {
    localStorage.setItem(emotionKey, this.name);
    document.body.dataset.emotion = this.name;
    document.body.style.paddingTop = `${this.elementHeight}px`;
  }
}

const happy = new Emotion("happy")
const angry = new Emotion("angry")
Emotion.opposite_map.set(happy, angry)
Emotion.opposite_map.set(angry, happy)

const emotionKey = "emotion";
const savedEmotionName = localStorage.getItem(emotionKey) ?? happy.name;

for (const emotion of [happy, angry]) {
  if (emotion.name == savedEmotionName) {
    emotion.apply();
  }
  emotion.element.addEventListener("click", () => {
    emotion.opposite.apply();
  });
}

setTimeout(() => {
  document.body.style.transition = "padding-top 0.8s";
});
