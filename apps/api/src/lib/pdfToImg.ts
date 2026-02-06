import { pdf } from "pdf-to-img";

export const pdfToImage = async(file:File)=>{
    try {
        const buffer = Buffer.from(await file.arrayBuffer());
        const document = await pdf(buffer);
        return document;
    } catch (error) {
        console.error(error);
    }
}