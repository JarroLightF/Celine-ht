import base64
from PyPDF2 import PdfWriter, PdfReader
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter


def write_watermark(original_file, watermark):
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=letter)
    # these, for some reason, are points. A4 = 792x612. Left/bottom boh.
    can.drawString(510, 740, watermark)
    can.save()
    packet.seek(0)
    new_pdf = PdfReader(packet)
    output = PdfWriter()
    page = original_file.pages[0]
    page.merge_page(new_pdf.pages[0])
    output.add_page(page)
    for p in range(1, len(original_file.pages)):
        output.add_page(original_file.pages[p])
    output_stream = open("edited.pdf", "wb")
    output.write(output_stream)
    output_stream.close()
    tempMemory = io.BytesIO()
    output.write(tempMemory)
    newFileData = tempMemory.getvalue()
    newEncodedPDF = base64.b64encode(newFileData)
    with open('cio.txt', 'wb') as theFile:
        theFile.write(newEncodedPDF)


base64_code = ""

base64_img_bytes = base64_code.encode('utf-8')
content = base64.decodebytes(base64_img_bytes)

my_pdf = PdfReader(io.BytesIO(content))
watermark = "Ciaoneee"
write_watermark(my_pdf, watermark)
