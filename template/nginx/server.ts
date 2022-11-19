// Used to generate json schema.

export interface ReverseProxySite {
  type: "reverse-proxy";
  subdomain: string;
  upstream: {
    name: string;
    server: string;
  };
}

export interface StaticFileSite {
  type: "static-file";
  subdomain: string;
  root: string;
}

export interface CertOnlySite {
  type: "cert-only";
  subdomain: string;
}

export type Site = ReverseProxySite | StaticFileSite | CertOnlySite;

export type Sites = Site[];

export interface Server {
  sites: Sites;
}
