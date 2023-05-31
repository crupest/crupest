// Used to generate json schema.

// path should start with "/", end without "/" and contain no special characters in regex.
// the special case is root path "/", which is allowed.

// For example:
// Given
//   path: /a/b
//   to: http://c.com/d
// Then (no_strip_prefix is false)
//   url: /a/b/c
//   redirect to: http://c.com/d/c (/a/b is removed)
// Note:
// Contrary to reverse proxy, you would always want to strip the prefix path.
// Because there is no meaning to redirect to the new page with the original path.
// If you want a domain-only redirect, just specify the path as "/".
export interface RedirectService {
  type: "redirect";
  path: string; // must be a path, should start with "/", end without "/"
  to: string; // must be a url, should start with scheme (http:// or https://), end without "/"
  code?: number; // default to 307
}

// For example:
// Given
//   path: /a/b
//   root: /e/f
// Then (no_strip_prefix is false)
//   url: /a/b/c/d
//   file path: /e/f/c/d (/a/b is removed)
// Or (no_strip_prefix is true)
//   url: /a/b/c/d
//   file path: /e/f/a/b/c/d
export interface StaticFileService {
  type: "static-file";
  path: string; // must be a path, should start with "/", end without "/"
  root: string; // must be a path (directory), should start with "/", end without "/"
  no_strip_prefix?: boolean; // default to false. If true, the path prefix is not removed from the url when finding the file.
}

// For example:
// Given
//   path: /a/b
//   upstream: another-server:1234
// Then
//   url: /a/b/c/d
//   proxy to: another-server:1234/a/b/c/d
// Note:
//   Contrary to redirect, you would always want to keep the prefix path.
//   Because the upstream server will mess up the path handling if the prefix is not kept.
export interface ReverseProxyService {
  type: "reverse-proxy";
  path: string; // must be a path, should start with "/", end without "/"
  upstream: string; // should be a [host]:[port], like "localhost:1234"
}

export type Service = RedirectService | StaticFileService | ReverseProxyService;

export interface SubDomain {
  name: string; // @ for root domain
  services: Service[];
}

export interface Server {
  domains: SubDomain[];
}
