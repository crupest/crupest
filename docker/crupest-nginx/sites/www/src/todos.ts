export interface Todo {
  status: string;
  title: string;
  closed: boolean;
  color: string;
}

export async function fetchTodos(): Promise<Todo[]> {
  console.log("Try to fetch TODOs from server.");

  if (process.env.NODE_ENV !== "production") {
    console.log("YaY! We are developers. 🍻 Use mock TODOs. (After 2s)");
    // await new Promise((resolve) => setTimeout(resolve, 2000));
    return (await import("./mock-todos")).default;
  } else {
    const res = await fetch("/api/todos");
    const body: Todo[] = await res.json();

    if (res.status !== 200) {
      console.error(
        `Failed to get TODOs. Status: ${res.status}. Body: ${body}`,
      );
      throw new Error(
        "Failed to fetch TODOs. (Maybe due to rate limit. Please try later.)",
      );
    }
    return body;
  }
}
