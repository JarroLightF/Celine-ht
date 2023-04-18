import logging
import json
import azure.functions as func
import io
import base64
import jsonschema
from jsonschema import validate
from PyPDF2 import PdfWriter, PdfReader
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

payload_schema = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "id": {
                "type": "integer"
            },
            "content": {
                "type": "string"
            },
            "watermark": {
                "type": "string"
            }
        },
        "required": [
            "id",
            "content",
            "watermark"
        ]
    }
}


def create_overlay_page(watermark):
    watermark_y = 740
    watermark_x = 570
    overlay_page = io.BytesIO()
    temp_pdf = canvas.Canvas(overlay_page, pagesize=letter)
    temp_pdf.setFont("Helvetica", 20)
    temp_pdf.drawRightString(watermark_x, watermark_y, watermark)
    temp_pdf.save()
    overlay_page.seek(0)
    return overlay_page


def print_watermark(list_of_documents):

    for d in list_of_documents:
        document = d["item"]
        try:
            overlay_page = create_overlay_page(document["watermark"])
            new_pdf = PdfReader(overlay_page)
            output_pdf = PdfWriter()
            original_pdf = base64.decodebytes(
                document["content"].encode('ascii'))
            original_pdf = PdfReader(io.BytesIO(original_pdf))
            first_page = original_pdf.pages[0]
            page_to_extract = original_pdf.pages[0]
            first_page.merge_page(new_pdf.pages[0])
            output_pdf.add_page(first_page)
            for p in range(1, len(original_pdf.pages)):
                output_pdf.add_page(original_pdf.pages[p])
            tempMemory = io.BytesIO()
            output_pdf.write(tempMemory)
            newFileData = tempMemory.getvalue()
            newEncodedPDF = base64.b64encode(newFileData)
            document["content"] = newEncodedPDF.decode()
            document["text"] = page_to_extract.extract_text()
            d["item"] = document
            d["statusCode"] = 201
            d["message"] = "Watermark applied."
        except:
            d["statusCode"] = 500
            d["message"] = "Failed to apply watermark."

    return list_of_documents


def is_base64(sb):
    try:
        if isinstance(sb, str):
            sb_bytes = bytes(sb, 'ascii')
        elif isinstance(sb, bytes):
            sb_bytes = sb
        else:
            raise ValueError("Argument must be string or bytes")
        return base64.b64encode(base64.b64decode(sb_bytes)) == sb_bytes
    except Exception:
        return False


def validate_document(document):
    return is_base64(document["content"])


def validate_documents(list_of_documents):
    out_list = []
    for document in list_of_documents:
        is_valid_base_64 = validate_document(document)
        out_list.append(
            {
                "statusCode": 201 if is_valid_base_64 else 400,
                "message":  "Updated" if is_valid_base_64 else "Not a valid base64 string.",
                "item": document
            }
        )
    return out_list


def is_json(payload):
    try:
        json.loads(payload)
    except ValueError as err:
        return False
    return True


def has_valid_schema(payload):
    try:
        validate(instance=payload, schema=payload_schema)
    except jsonschema.exceptions.ValidationError as err:
        return False
    return True


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    payload = req.get_json()

    if has_valid_schema(payload):
        list_of_documents = validate_documents(payload)
        list_of_documents = print_watermark(list_of_documents)
        return func.HttpResponse(
            json.dumps(list_of_documents),
            status_code=200,
            mimetype="application/json",
            charset='utf-8',
        )
    else:
        return func.HttpResponse(
            json.dumps({"message": "Bad request. Invalid schema."}),
            status_code=400,
            mimetype="application/json",
            charset='utf-8',
        )
