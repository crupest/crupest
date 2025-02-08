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

  select_proxy = { name: "node-select", type: "select", proxies: ["auto-select", ...config.proxies.map(p => p.name)] }
  auto_select_proxy = config["crupest-auto-select"]
  config["proxy-groups"] = [ select_proxy, auto_select_proxy ]
  delete config["crupest-auto-select"]

  return config;
}
