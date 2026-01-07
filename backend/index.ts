import { Hono } from "hono";
import { cors } from "hono/cors";
import "dotenv/config";
import { auth } from "./src/config/auth";


// Initialize Hono app
const app = new Hono();

// Enable CORS
app.use("*", cors({
	origin: ["http://localhost:3000"],
	credentials: true,
}));

// Better Auth routes - handles signup, signin, signout automatically
app.on(["POST", "GET"], "/api/auth/*", (c) => auth.handler(c.req.raw));

// Health check endpoint
app.get("/", (c) => {
	return c.json({ message: "Server is running", status: "ok" });
});

// Custom signup endpoint (optional - better-auth handles this automatically at /api/auth/sign-up/email)
app.post("/api/signup", async (c) => {
	// console.log("/api/signup - ", c.status, "-");
	try {
		const body = await c.req.json();
		const { email, password, name } = body;

		if (!email || !password) {
			return c.json({ error: "Email and password are required" }, 400);
		}

		// Better auth will handle this at /api/auth/sign-up/email
		// This is just a custom wrapper
		return c.json({
			message: "Use /api/auth/sign-up/email endpoint",
			info: "Better-auth provides built-in signup at /api/auth/sign-up/email"
		});
	} catch (error) {
		return c.json({ error: "Signup failed" }, 500);
	}
});

// Custom signin endpoint (optional - better-auth handles this automatically at /api/auth/sign-in/email)
app.post("/api/signin", async (c) => {
	try {
		const body = await c.req.json();
		const { email, password } = body;

		if (!email || !password) {
			return c.json({ error: "Email and password are required" }, 400);
		}

		// Better auth will handle this at /api/auth/sign-in/email
		return c.json({
			message: "Use /api/auth/sign-in/email endpoint",
			info: "Better-auth provides built-in signin at /api/auth/sign-in/email"
		});
	} catch (error) {
		return c.json({ error: "Signin failed" }, 500);
	}
});

// Get current session
app.get("/api/session", async (c) => {
	const session = await auth.api.getSession({ headers: c.req.raw.headers });

	if (!session) {
		return c.json({ error: "Not authenticated" }, 401);
	}

	return c.json({ session });
});

// Start server
const PORT = process.env.PORT || 3001;
console.log(`🚀 Server running on http://localhost:${PORT}`);
console.log(`📝 Auth endpoints available at http://localhost:${PORT}/api/auth/*`);

export default {
	port: PORT,
	fetch: app.fetch,
};