const buttons = {
  direct: document.getElementById("direct_button"),
  system: document.getElementById("system_button"),
  proxy: document.getElementById("proxy_button"),
};

function setSelectedButton(button) {
  for (const key in buttons) {
    buttons[key].classList.remove("selected");
  }
  buttons[button].classList.add("selected");
}

browser.proxy.settings.get({}).then(({ value }) => {
  console.log("current proxy settings: ", value);
  if (value.proxyType === "none") {
    setSelectedButton("direct");
  } else if (value.proxyType === "system") {
    setSelectedButton("system");
  } else if (value.proxyType === "manual") {
    setSelectedButton("proxy");
  }
});

browser.storage.local.get("proxyUrl").then(({ proxyUrl }) => {
  console.log("Saved proxy url is ", proxyUrl);

  const proxyConfigs = {
    direct: {
      proxyType: "none",
    },
    system: {
      proxyType: "system",
    },
    proxy: {
      proxyType: "manual",
      http: proxyUrl,
      httpProxyAll: true,
    },
  };

  for (const key in buttons) {
    buttons[key].addEventListener("click", () => {
      console.log("Try to set proxy to ", proxyConfigs[key]);
      browser.proxy.settings
        .set({ value: proxyConfigs[key] })
        .then((success) => {
          if (success) {
            setSelectedButton(key);
          }
        });
    });
  }
});

document.getElementById("settings_button").addEventListener("click", () => {
  browser.runtime.openOptionsPage();
});
