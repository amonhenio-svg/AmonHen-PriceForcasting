import { routes, deploymentEnv, type VercelConfig } from "@vercel/config/v1";

export const config: VercelConfig = {
  buildCommand: "npm run build",
  outputDirectory: "build",
  framework: "create-react-app",

  rewrites: [
    // Proxy all /api/* requests to the backend (Railway)
    routes.rewrite("/api/:path*", `${deploymentEnv("BACKEND_URL")}/api/$1`),

    // SPA fallback for client-side routing
    routes.rewrite("/((?!static/).*)", "/index.html"),
  ],
};
