require('dotenv').config();
import { Hono } from "hono";
import { ocrRouter } from "./routes/ocr.route";
import { serve } from "@hono/node-server";
import { logger } from "hono/logger";


const app = new Hono();
app.use(logger());
app.get("/",async(c)=>{
    return c.json({message:"Hello kavyaraj"})
})
const routes = app.basePath("/api").route("/bank-statement",ocrRouter);

export type AppType = typeof routes;


 serve({
    fetch:app.fetch,
    port:Number(process.env.PORT!),
})

console.log(`Server running on http://localhost:${process.env.PORT!}`);