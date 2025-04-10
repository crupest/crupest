export type CronCallback = (task: CronTask) => Promise<void>;

export interface CronTaskConfig {
  readonly name: string;
  readonly interval: number;
  readonly callback: CronCallback;
  readonly startNow?: boolean;
}

export class CronTask {
  #timerTag: number | null = null;

  constructor(public readonly config: CronTaskConfig) {
    if (config.interval <= 0) {
      throw new Error("Cron task interval must be positive.");
    }

    if (config.startNow === true) {
      this.start();
    }
  }

  get running(): boolean {
    return this.#timerTag != null;
  }

  start() {
    if (this.#timerTag == null) {
      this.#timerTag = setInterval(
        this.config.callback,
        this.config.interval,
        this,
      );
    }
  }

  stop() {
    if (this.#timerTag != null) {
      clearInterval(this.#timerTag);
      this.#timerTag = null;
    }
  }
}
