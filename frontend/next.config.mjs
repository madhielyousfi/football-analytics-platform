/** @type {import('next').NextConfig} */
const isStatic = process.env.NEXT_PUBLIC_DATA_MODE === "static";
const basePath = process.env.NEXT_PUBLIC_BASE_PATH ?? "";

const nextConfig = {
  reactStrictMode: true,
  ...(isStatic ? { output: "export", images: { unoptimized: true } } : {
    images: { remotePatterns: [{ protocol: "https", hostname: "**" }] },
  }),
  ...(basePath ? { basePath, assetPrefix: `${basePath}/` } : {}),
  async rewrites() {
    if (isStatic) return [];
    const api = process.env.NEXT_PUBLIC_API_URL;
    if (!api) return [];
    return [{ source: "/api/:path*", destination: `${api}/api/:path*` }];
  },
};
export default nextConfig;
