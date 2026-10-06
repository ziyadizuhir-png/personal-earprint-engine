/** @type {import('next').NextConfig} */
const isPages = process.env.GITHUB_PAGES === "true";

module.exports = {
  output: isPages ? "export" : undefined,
  basePath: isPages ? "/personal-earprint-engine" : "",
  assetPrefix: isPages ? "/personal-earprint-engine/" : undefined,
  trailingSlash: true,
  images: { unoptimized: true },
};
