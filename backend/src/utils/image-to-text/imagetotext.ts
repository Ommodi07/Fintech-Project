import { createWorker } from 'tesseract.js';
import fs from 'fs';

(async () => {
  const worker = await createWorker('eng');
  const ret = await worker.recognize('./image.png');
  const file = fs.createWriteStream('./src/utils/image-to-text/output.txt');
  file.write(ret.data.text);
  file.end();
  await worker.terminate();
})();