import "dotenv/config"
import { Hono } from "hono";
import { ocrRouter } from "./routes/ocr.route";
import { serve } from "@hono/node-server";
import { logger } from "hono/logger";
import { createAuthServer } from "@repo/auth/src/server";
import { createDatabase } from "@repo/database/src/index";
import { cors } from "hono/cors";

const db = createDatabase({
    connectionString: process.env.DATABASE_URL!,
});

const auth = createAuthServer({
    database: db,
    email: {
        userMail: process.env.USER_MAIL!,
        googleAppPassword: process.env.GOOGLE_APP_PASSWORD!,
    },
    betterAuth: {
        secret: process.env.BETTER_AUTH_SECRET!,
        baseURL: process.env.BETTER_AUTH_URL!,
        trustedOrigins: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
    },
});

const app = new Hono();
app.use(logger());
app.use(
  cors({
    origin: ["http://localhost:3000", "http://127.0.0.1:3000"],
    allowMethods: ["GET", "HEAD", "PUT", "POST", "DELETE", "PATCH", "OPTIONS"],
    allowHeaders: ["Content-Type", "Authorization", "Accept"],
    credentials: true,
  })
)
app.get("/", async (c) => {
    return c.json({ message: "Hello kavyaraj" })
})

app.on(
  ["POST", "GET", "PUT", "PATCH", "DELETE", "OPTIONS"],
  "/api/auth/*",
  async (c) => {
    const res = await auth.handler(c.req.raw);
    return res;
  }
);
const routes = app.basePath("/api").route("/bank-statement", ocrRouter);

export type AppType = typeof routes;



serve({
    fetch: app.fetch,
    port: Number(process.env.SERVER_PORT!),
})

console.log(`Server running on http://localhost:${process.env.SERVER_PORT!}`);