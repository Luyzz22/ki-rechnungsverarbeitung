import { execSync } from "node:child_process";
import { createHash } from "node:crypto";

// Next.js generates a random BUILD_ID on every build and embeds it in every
// rendered page, so two builds of the same source produce different bytes. That
// makes the release artifact impossible to reproduce and therefore impossible
// to verify by rebuilding — which is the whole point of shipping a hashed
// tarball to the production host. Deriving it from the commit fixes that: the
// same commit always produces the same output.
//
// SBS_BUILD_ID wins, so a CI system without a git checkout can supply it. If
// neither is available the build falls back to Next's random id: a reproducible
// build is not possible from an unidentified tree, and pretending otherwise
// would be worse than admitting it.
// The id ends up in public asset URLs (/_next/static/<buildId>/…), so the commit
// is hashed rather than published: deterministic, but it does not hand a visitor
// the exact revision of a private repository.
function buildId() {
  if (process.env.SBS_BUILD_ID) return process.env.SBS_BUILD_ID;
  let commit;
  try {
    commit = execSync("git rev-parse HEAD", { stdio: ["ignore", "pipe", "ignore"] })
      .toString()
      .trim();
  } catch {
    return null;
  }
  return createHash("sha256").update(commit).digest("base64url").slice(0, 21);
}

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  generateBuildId: buildId,
  reactStrictMode: true,
  poweredByHeader: false,
  images: {
    formats: ["image/avif", "image/webp"],
  },
  // Baseline headers so the application is still safe when run without a
  // reverse proxy. In production nginx is authoritative and strips these before
  // adding its own, so no response ever carries two values for the same header
  // — see infra/nginx/snippets/sbs-web-proxy.conf.
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "X-Frame-Options", value: "DENY" },
          {
            key: "Permissions-Policy",
            value: "camera=(), microphone=(), geolocation=(), interest-cohort=()",
          },
        ],
      },
    ];
  },
};

export default nextConfig;
