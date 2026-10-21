import { defineConfig } from "vitest/config";

export default defineConfig({
  resolve: {
    // Resolve the "@/..." import alias from tsconfig.json.
    tsconfigPaths: true,
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./vitest.setup.ts"],
    include: ["__tests__/**/*.test.{ts,tsx}"],
    // Testing Library needs React's development build; force it even if the shell
    // exports NODE_ENV=production.
    env: { NODE_ENV: "test" },
  },
});
