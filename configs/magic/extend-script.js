// Define main function (script entry)

function main(config, profileName) {
  delete config.dns;
  delete config.tun;
  delete config.hosts;

  delete config["cfw-latency-timeout"]
  delete config["cfw-latency-url"]
  delete config["cfw-conn-break-strategy"]

  config["proxies"] = [config["crupest-proxy"], ...config["proxies"]]
  delete config["crupest-proxy"]

  select_proxy = { name: "node-select", type: "select", proxies: ["fallback", ...config.proxies.map(p => p.name)] }
  fallback_proxy = config["crupest-fallback"]
  config["proxy-groups"] = [ select_proxy, fallback_proxy ]
  delete config["crupest-fallback"]

  return config;
}
