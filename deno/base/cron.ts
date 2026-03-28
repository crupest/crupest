export type CronCallback = (task: CronTask) => Promise<void> | void;

export interface CronTaskConfig {
  readonly name: string;
  readonly interval: number | Temporal.Duration;
  readonly callback: CronCallback;
  readonly enableNow?: boolean;
}

export class CronTask {
  #name: string;
  #interval_ms: number;
  #callback: CronCallback;
  #timerTag: number | null = null;

  constructor({ name, interval, callback, enableNow }: CronTaskConfig) {
    this.#interval_ms = interval instanceof Temporal.Duration
      ? interval.total("millisecond")
      : interval;

    if (this.#interval_ms <= 0) {
      throw new Error("Cron task interval must be positive.");
    }

    this.#name = name;
    this.#callback = callback;

    if (enableNow === true) {
      this.enable();
    }
  }

  get name(): string {
    return this.#name;
  }

  get interval(): Temporal.Duration {
    return Temporal.Duration.from({ milliseconds: this.#interval_ms });
  }

  get enabled(): boolean {
    return this.#timerTag != null;
  }

  get callback(): CronCallback {
    return this.#callback;
  }

  enable() {
    if (this.#timerTag == null) {
      this.#timerTag = setInterval(
        this.#callback,
        this.#interval_ms,
        this,
      );
    }
  }

  disable() {
    if (this.#timerTag != null) {
      clearInterval(this.#timerTag);
      this.#timerTag = null;
    }
  }
}
