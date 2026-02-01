import Tesseract from "tesseract.js";

enum PSM{
    SINGLE_COLUMN =6
}

export const TESSERACT_CONFIG = {
    lang:'en',
    oem:1,
    psm:PSM
};