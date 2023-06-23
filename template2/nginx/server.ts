// Used to generate json schema.
// Note: path in every service is removed before passing to the service.

// For example:
// Given
//   path: /a/b
//   to: http://c.com/d
// Then
//   url: /a/b/c
//   redirect to: http://c.com/d/c (/a/b is removed)
export interface RedirectService {
  type: "redirect";
  path: string; // must be a path
  to: string; // must be a url
  code?: number; // default to 307
}

// For example:
// Given
//   path: /a/b
//   root: /e/f
// Then
//   url: /a/b/c/d
//   file path: /e/f/c/d (/a/b is removed)
export interface StaticFileService {
  type: "static-file";
  path: string;
  root: string;
}

// For example:
// Given
//   path: /a/b
//   upstream: another-server:1234
// Then
//   url: /a/b/c/d
//   proxy to: another-server:1234/c/d (/a/b is removed)
export interface ReverseProxyService {
  type: "reverse-proxy";
  path: string;
  upstream: string;
}

export type Service = RedirectService | StaticFileService | ReverseProxyService;

export interface SubDomain {
  name: string; // @ for root domain
  services: Service[];
  no_cert?: boolean; // default to false, if true, we don't get a ssl cert from Let's Encrypt for this domain
}

export interface Server {
  domains: SubDomain[];
}
