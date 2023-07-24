const { PDFDocument } = require('pdf-lib');
const { PDFJS } = require('pdfjs-dist/es5/build/pdf');

async function extractAndCreatePDF(inputPath, contentToMatch, outputPath) {
  try {
    // Read the input PDF
    const pdfBytes = await PDFJS.getDocument(inputPath).promise;
    const numPages = pdfBytes.numPages;

    // Create a new PDF
    const newPDFDoc = await PDFDocument.create();

    for (let pageNum = 1; pageNum <= numPages; pageNum++) {
      const page = await pdfBytes.getPage(pageNum);
      const content = await page.getTextContent();
      const text = content.items.map(item => item.str).join('');

      if (text.includes(contentToMatch)) {
        const [copiedPage] = await newPDFDoc.copyPages(pdfBytes, [pageNum - 1]);
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
