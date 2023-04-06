import azure.functions as func
import io
import base64
import json
import jsonschema
from jsonschema import validate
from PyPDF2 import PdfWriter, PdfReader
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

document_schema = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "id": {
                "type": "integer"
            },
            "name": {
                "type": "string"
            },
            "content": {
                "type": "string"
            }
        },
        "required": [
            "id",
            "name",
            "content"
        ]
    }
}


def create_overlay_page(watermark):
    watermark_y = 740
    watermark_x = 510
    overlay_page = io.BytesIO()
    temp_pdf = canvas.Canvas(overlay_page, pagesize=letter)
    temp_pdf.drawString(watermark_x, watermark_y, watermark)
    temp_pdf.save()
    overlay_page.seek(0)
    return overlay_page


def print_watermark(list_of_documents):
    watermark_y = 740
    watermark_x = 510
    for document in list_of_documents:
        overlay_page = create_overlay_page(document.watermark)
        new_pdf = PdfReader(overlay_page)
        output = PdfWriter()
        content = base64.decodebytes(document.content.encode('utf-8'))
        my_pdf = PdfReader(io.BytesIO(content))
        page = my_pdf.pages[0]
        page.merge_page(new_pdf.pages[0])
        output.add_page(page)
        for p in range(1, len(my_pdf.pages)):
            output.add_page(my_pdf.pages[p])
        tempMemory = io.BytesIO()
        output.write(tempMemory)
        newFileData = tempMemory.getvalue()
        newEncodedPDF = base64.b64encode(newFileData)
        document["content"] = newEncodedPDF

    return list_of_documents


def is_base64(s):
    try:
        return base64.b64encode(base64.b64decode(s)) == s
    except Exception:
        return False


def validate_document(document):
    result = is_base64(document["content"])


def validate_documents(list_of_documents):
    for document in list_of_documents:
        is_valid_base_64 = validate_document(document)
        document["statusCode"] = 201 if is_valid_base_64 else 400
        document["errorDescription"] = "" if is_valid_base_64 else "Not a valid base64 string."
    return list_of_documents


def is_json(payload):
    try:
        json.loads(payload)
    except ValueError as err:
        return False
    return True


def has_valid_schema(payload):
    try:
        validate(instance=payload, schema=document_schema)
    except jsonschema.exceptions.ValidationError as err:
        return False
    return True


def main(req: func.HttpRequest) -> func.HttpResponse:
    payload = req.get_body()
    if is_json(payload):
        payload = json.loads(payload)
        if has_valid_schema(payload):
            list_of_documents = validate_documents(payload)
            list_of_documents = print_watermark(list_of_documents)
            return func.HttpResponse(
                json.dumps(list_of_documents),
                mimetype="application/json",
                charset='utf-8',
            )
        else:
            return func.HttpResponse(
                json.dumps({"ciao": "asddsa"}),
                mimetype="application/json",
                charset='utf-8',
            )
    else:
        return func.HttpResponse(
            json.dumps({"ciao": "asddsa"}),
            mimetype="application/json",
            charset='utf-8',
        )
