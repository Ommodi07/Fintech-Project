import { Hono } from "hono";
import { extractText } from "../lib/tesseract";
import { HTTPException } from "hono/http-exception";
import { pdfToImage } from "../lib/pdfToImg";
import { ai } from "../utils/gemini";

const schema = {
  type: "object",
  properties: {
    document_type: { type: "string" },
    invoice_number: { type: "string" },
    date: { type: "string" },
    vendor: { type: "string" },
    total_amount: { type: "number" },
    line_items: {
      type: "array",
      items: {
        type: "object",
        properties: {
          description: { type: "string" },
          quantity: { type: "number" },
          price: { type: "number" }
        },
        required: ["description", "quantity", "price"]
      }
    }
  },
  required: ["document_type"]
};


export const ocrRouter = new Hono().post("/",async(c)=>{
    const body = await c.req.parseBody();
    if(!(body["file"] instanceof File)){
        throw new HTTPException(400,{message:"A image or pdf is required"});
    }
    const file = body["file"]
    const document = await pdfToImage(file);
    if(document === undefined){
        throw new HTTPException(500,{message:"Error while converting image from pdf"})
    };
    let textdata:string = ""
    for await(const image of document){
        const data = await extractText(image);
        if(data === undefined){
            throw new HTTPException(500,{message:"Error while doing ocr"});
        }
        textdata += data;
    }
const response = await ai.models.generateContent({
  model: "gemini-2.5-flash",
  contents: [
    {
      role: "user",
      parts: [
        {
          text: `
You are an OCR post-processing system.
Extract structured information from the following OCR text.
If a field is missing, return null(not string "null").

OCR TEXT:
${textdata}
          `
        }
      ]
    }
  ],
  config: {
    temperature: 0,
    responseMimeType: "application/json",
    responseJsonSchema: schema,
  }
});

    return c.json({message:"hello",response},200)
})