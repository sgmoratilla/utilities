# from http://stackoverflow.com/questions/12571905/finding-on-which-page-a-search-string-is-located-in-a-pdf-document-using-python
import re
from PyPDF2 import PdfFileWriter, PdfFileReader


class PdfSplitter:
    def __init__(self, filename='', f=None):
        if f is not None:
            self.f = f
        elif filename != '':
            self.f = file(filename, "rb")
        else:
            raise ValueError("Either filename or f must be specified")
        self.pdfDoc = PdfFileReader(self.f)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def find(self, text):
        pageFound = None
        for i in range(0, self.pdfDoc.getNumPages()):
            content = ""
            content += self.pdfDoc.getPage(i).extractText() + "\n"
            content1 = content.encode('ascii', 'ignore').lower()
            reSearch = re.search(text, content1)
            if reSearch is not None:
                pageFound = i
                break
        return pageFound

    def write_page(self, xPageStart, xPageEnd, filename):
        output = PdfFileWriter()
        for i in range(xPageStart, xPageEnd):
            output.addPage(self.pdfDoc.getPage(i))
            os = file(filename, "wb")
            output.write(os)
            os.close()

    def close(self):
        # type: () -> object
        self.f.close()
        self.f = None
        self.pdfDoc = None


from pdfminer.pdfparser import PDFParser
from pdfminer.pdfinterp import PDFResourceManager
# the internal API has changed between versions upstream,
# allow both here..
try:
    from pdfminer.pdfparser import PDFDocument
    from pdfminer.pdfparser import PDFSyntaxError
except ImportError:
    from pdfminer.pdfdocument import PDFDocument
    from pdfminer.pdfdocument import PDFSyntaxError
try:
    from pdfminer.pdfparser import PDFPage
except ImportError:
    from pdfminer.pdfpage import PDFPage
from pdfminer.pdfinterp import PDFPageInterpreter
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from cStringIO import StringIO


class PdfException(Exception):
    pass


class CachedPdfReader:
    def __init__(self, filename='', f=None):
        if f is not None:
            self.f = f
        elif filename != '':
            self.f = file(filename, "rb")
        else:
            raise ValueError("Either filename or f must be specified")
        self.parser = PDFParser(self.f)
        try:
            self.document = PDFDocument(self.parser)
        except PDFSyntaxError as e:
            raise PdfException(e)
        if not self.document.is_extractable:
            print(filename, "Warning: could not extract text from pdf file.")
        self.rsrcmgr = PDFResourceManager()
        self._initialize()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def _initialize(self):
        self.cachedText = []
        for page in PDFPage.create_pages(self.document):
            retstr = StringIO()
            device = TextConverter(self.rsrcmgr, retstr, codec='ascii', laparams=LAParams())
            interpreter = PDFPageInterpreter(self.rsrcmgr, device)
            interpreter.process_page(page)
            self.cachedText.append(retstr.getvalue().lower())

        return self.cachedText

    def find(self, text):
        pageFound = None
        nPages = len(self.cachedText)
        text = text.lower()
        for i in range(0, nPages):
            reSearch = re.search(text, self.cachedText[i])
            if reSearch is not None:
                pageFound = i
                break
        return pageFound

    def close(self):
        # type: () -> object
        self.f.close()
        self.f = None
        self.parser = None
        self.document = None
        self.rsrcmgr = None
