declare global {
  interface Date {
    toFileNameString(dateOnly?: boolean): string;
  }
}

Object.defineProperty(Date.prototype, "toFileNameString", {
  value: function (dateOnly?: boolean) {
    const str = (this as Date).toISOString();
    return dateOnly === true
      ? str.slice(0, str.indexOf("T"))
      : str.replaceAll(/:|\./g, "-");
  },
});
