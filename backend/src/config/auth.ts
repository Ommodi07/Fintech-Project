import { betterAuth } from "better-auth";
import { Pool } from "pg";

// database init
const pool = new Pool({
    connectionString: process.env.DATABASE_URL,
});

// Initialize Better Auth
export const auth = betterAuth({
    database: pool,
    emailAndPassword: {
        enabled: true,
    },
    secret: process.env.BETTER_AUTH_SECRET!,
    baseURL: process.env.BETTER_AUTH_URL,
    trustedOrigins: ["http://localhost:3000"],
});