import { createWorker} from "tesseract.js";
import { TESSERACT_CONFIG } from "../config/tesseract.config";


export async function extractText(img:Buffer<ArrayBufferLike>) {
   try {
    const worker = await createWorker('eng');
    const data = await worker.recognize(img);
    await worker.terminate();
    return data.data.text;
   } catch (error) {
    console.error(error)
   }
}