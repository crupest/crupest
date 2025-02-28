browser.storage.local.get("proxyUrl").then(({ proxyUrl }) => {
  console.log("Saved proxy url is", proxyUrl);
  document.getElementById("proxy_url").value = proxyUrl;
  document.getElementById("proxy_url").addEventListener("input", (e) => {
    const { value } = e.currentTarget;
    browser.storage.local
      .set({
        proxyUrl: value,
      })
      .then(() => {
        console.log("New proxy url saved!", value);
      });
  });
});
