/** 브라우저에서 PDF 텍스트를 추출한다 (pdf.js는 필요할 때만 불러온다). */
export async function pdfToText(file: File): Promise<string> {
  const [pdfjs, worker] = await Promise.all([
    import('pdfjs-dist'),
    import('pdfjs-dist/build/pdf.worker.min.mjs?url'),
  ]);
  pdfjs.GlobalWorkerOptions.workerSrc = worker.default;

  const doc = await pdfjs.getDocument({ data: await file.arrayBuffer() }).promise;
  const pages: string[] = [];
  for (let i = 1; i <= doc.numPages; i++) {
    const content = await (await doc.getPage(i)).getTextContent();
    let page = '';
    for (const item of content.items) {
      if (!('str' in item)) continue;
      page += item.str + (item.hasEOL ? '\n' : '');
    }
    pages.push(page);
  }
  await doc.destroy();
  return pages.join('\n');
}
