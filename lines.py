const pdfjsLib = require("pdfjs-dist");

async function GetTextFromPDF(path) {
    let doc = await pdfjsLib.getDocument(path).promise;
    let page1 = await doc.getPage(1);
    let content = await page1.getTextContent();
    let strings = content.items.map(function(item) {
        return item.str;
    });
    return strings;
}
module.exports = { GetTextFromPDF }



const pdfExport = require('./pdfreader');
pdfExport.GetTextFromPDF('/Users/sureshreddy/Documents/Prepared/GIDS_QC_speaker_notes.pdf').then(data => console.log(data));
