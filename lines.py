const { PDFDocument, rgb } = require('pdf-lib');
const fs = require('fs').promises;

async function extractAndCreatePDF(inputPath, contentToMatch, outputPath) {
  try {
    // Read the input PDF
    const pdfBytes = await fs.readFile(inputPath);

    // Load the input PDF into a PDFDocument object
    const pdfDoc = await PDFDocument.load(pdfBytes);

    // Create a new PDF
    const newPDFDoc = await PDFDocument.create();

    for (let pageNum = 0; pageNum < pdfDoc.getPageCount(); pageNum++) {
      const page = pdfDoc.getPage(pageNum);
      const content = await page.getText();
      if (content.includes(contentToMatch)) {
        const [copiedPage] = await newPDFDoc.copyPages(pdfDoc, [pageNum]);
        newPDFDoc.addPage(copiedPage);
      }
    }

    // Serialize the new PDF to bytes
    const newPDFBytes = await newPDFDoc.save();

    // Write the new PDF to the output file
    await fs.writeFile(outputPath, newPDFBytes);

    console.log(`Pages with content "${contentToMatch}" extracted and a new PDF created at: ${outputPath}`);
  } catch (err) {
    console.error('Error:', err.message);
  }
}

// Usage example
extractAndCreatePDF('input.pdf', 'keyword to match', 'output.pdf');
