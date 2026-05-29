import type { NextConfig } from "next";

const basePath = process.env.NEXT_PUBLIC_BASE_PATH || "";
const isDemo = process.env.NEXT_PUBLIC_DEMO_MODE === "true";

const nextConfig: NextConfig = {
  output: isDemo ? "export" : undefined,
  basePath: basePath || undefined,
  assetPrefix: basePath || undefined,
  trailingSlash: isDemo,
  images: {
    unoptimized: true,
  },
};

export default nextConfig;
