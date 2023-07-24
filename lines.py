const { PDFDocument, rgb } = require('pdf-lib');
const fs = require('fs').promises;

async function extractAndCreatePDF(inputPath, startPage, endPage, outputPath) {
  try {
    // Read the input PDF
    const pdfBytes = await fs.readFile(inputPath);

    // Load the input PDF into a PDFDocument object
    const pdfDoc = await PDFDocument.load(pdfBytes);

    // Create a new PDF with the specified pages
    const newPDFDoc = await PDFDocument.create();

    for (let pageNum = startPage; pageNum <= endPage; pageNum++) {
      const [copiedPage] = await newPDFDoc.copyPages(pdfDoc, [pageNum - 1]);
      newPDFDoc.addPage(copiedPage);
    }

    // Serialize the new PDF to bytes
    const newPDFBytes = await newPDFDoc.save();

    // Write the new PDF to the output file
    await fs.writeFile(outputPath, newPDFBytes);

    console.log(`Pages ${startPage}-${endPage} extracted and a new PDF created at: ${outputPath}`);
  } catch (err) {
    console.error('Error:', err.message);
  }
}

// Usage example
extractAndCreatePDF('input.pdf', 2, 4, 'output.pdf');
