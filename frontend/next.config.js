/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    const backendUrl = process.env.BACKEND_URL || "http://127.0.0.1:8000";
    return [
      {
        source: "/api/:path*",
        destination: `${backendUrl}/api/:path*`,
      },
    ];
  },
  env: {
    NEXT_PUBLIC_APP_NAME: "TradeAI",
    NEXT_PUBLIC_APP_VERSION: "1.0.0",
  },
};

module.exports = nextConfig;
