import type { NextConfig } from 'next';

const repository = 'Data_next';
const isGitHubPages = process.env.GITHUB_ACTIONS === 'true';

const nextConfig: NextConfig = {
  output: 'export',
  trailingSlash: true,
  basePath: isGitHubPages ? `/${repository}` : '',
  assetPrefix: isGitHubPages ? `/${repository}/` : '',
  images: { unoptimized: true },
};

export default nextConfig;
