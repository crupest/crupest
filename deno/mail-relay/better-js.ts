declare global {
  interface Date {
    toFileNameString(dateOnly?: boolean): string;
  }
}

Object.defineProperty(Date.prototype, "toFileNameString", {
  value: function (this: Date, dateOnly?: boolean) {
    const str = this.toISOString();
    return dateOnly === true
      ? str.slice(0, str.indexOf("T"))
      : str.replaceAll(/:|\./g, "-");
  },
});
