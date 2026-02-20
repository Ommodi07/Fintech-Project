import { betterAuth } from "better-auth";
import { drizzleAdapter } from "better-auth/adapters/drizzle";
import type { DataBase } from "@repo/database/src/index";
import { user, session, account, verification } from "@repo/database/src/db/schema/auth";
import { createEmailSender } from "./sendmail";
import { openAPI } from "better-auth/plugins";

export interface AuthServerConfig {
    database: DataBase;
    email: {
        userMail: string;
        googleAppPassword: string;
    };
    betterAuth: {
        secret: string;
        baseURL: string;
        /** Frontend origins to allow (e.g. Next.js app URL). Required when frontend and API differ. */
        trustedOrigins?: string[];
    };
}

export function createAuthServer(config: AuthServerConfig) {
    const sendEmail = createEmailSender(config.email);

    return betterAuth({
        database: drizzleAdapter(config.database, {
            provider: "pg",
            schema: {
                user,
                session,
                account,
                verification,
            },
        }),
        secret: config.betterAuth.secret,
        baseURL: config.betterAuth.baseURL,
        trustedOrigins: config.betterAuth.trustedOrigins,
        emailAndPassword: {
            enabled: true,
            requireEmailVerification: true,
            sendResetPassword: async ({ user, url, token }, request) => {
                void sendEmail({
                    to: user.email,
                    subject: "Reset your password",
                    text: `Click the link to reset your password: ${url}`,
                });
            },
            onPasswordReset: async ({ user }, request) => {
                await sendEmail({
                    to: user.email,
                    subject: "Your password was changed",
                    text: "If this wasn't you, contact support immediately.",
                });
                console.log(`Password for user ${user.email} has been reset.`);
            }
        },
        emailVerification: {
            sendVerificationEmail: async ({ user, url, token }, request) => {
                await sendEmail({
                    to: user.email,
                    subject: "Verify your email address",
                    text: `Click the link to verify your email: ${url}`,
                });
            },
        },
        plugins:[openAPI()]
    });
}