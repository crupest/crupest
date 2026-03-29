export class TaskScheduler {
  #maxConcurrentTasks: number;
  #tasks: (() => Promise<void>)[] = [];
  #running = 0;

  constructor(maxConcurrentTasks: number) {
    if (maxConcurrentTasks <= 0) {
      throw new RangeError("maxConcurrentTasks must be > 0");
    }
    this.#maxConcurrentTasks = maxConcurrentTasks;
  }

  /**
   * Enqueues a task to run within the concurrency limit.
   *
   * WARNING: Do not `await queue()` on this same scheduler from inside a
   * running task. If all slots are occupied, the outer task will hold a slot
   * while waiting for an inner slot that never frees — causing a deadlock.
   */
  queue(task: () => Promise<void>): Promise<void> {
    return new Promise((resolve, reject) => {
      this.#tasks.push(() =>
        Promise.resolve().then(task).then(resolve, reject)
      );
      this.#drain();
    });
  }

  #drain(): void {
    while (this.#running < this.#maxConcurrentTasks && this.#tasks.length > 0) {
      const task = this.#tasks.shift()!;
      this.#running++;
      task().finally(() => {
        this.#running--;
        this.#drain();
      });
    }
  }
}
