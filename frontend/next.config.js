/** @type {import('next').NextConfig} */
const isPages = process.env.GITHUB_PAGES === "true";

module.exports = {
  output: isPages ? "export" : undefined,
  basePath: isPages ? "/personal-earprint-engine" : "",
  assetPrefix: isPages ? "/personal-earprint-engine/" : undefined,
  trailingSlash: true,
  images: { unoptimized: true },
  async rewrites() {
    if (isPages || process.env.NEXT_PUBLIC_API_URL) return [];
    return [{ source: "/api/:path*", destination: `${process.env.API_ORIGIN || "http://127.0.0.1:8000"}/api/:path*` }];
  },
};
