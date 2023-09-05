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
  "type": "object",
  "properties": {
    "LAST_USED_PROTOCOL": {
      "type": "integer"
    },
    "ITEMS": {
      "type": "array",
      "items": 
        {
          "type": "object",
          "properties": {
            "ID": {
              "type": "integer"
            },
            "CONTENT": {
              "type": "string"
            },
            "PROTOCOL":{
                "type": ["string", "null"]
            }
          },
          "required": [
            "ID",
            "CONTENT"
          ]
        }
    },
    "IS_INTRA": {
      "type": "boolean"
    }
  },
  "required": [
    "LAST_USED_PROTOCOL",
    "ITEMS",
    "IS_INTRA"
  ]
}

is_intra_payload_schema = {
  "type": "object",
  "properties": {
    "LAST_USED_PROTOCOL": {
      "type": "integer"
    },
    "ITEMS": {
      "type": "array",
      "items": 
        {
          "type": "object",
          "properties": {
            "ID": {
              "type": "integer"
            },
            "CONTENT": {
              "type": "string"
            },
            "PROTOCOL":{
                "type": ["string", "null"]
            },
            "VAT_AMOUNT":{
                "type": "string"
            },
            "DOC_AMOUNT":{
                "type": "string"
            },
            "TAXABLE_AMOUNT":{
                "type": "string"
            }
          },
          "required": [
            "ID",
            "CONTENT",
            "VAT_AMOUNT",
            "DOC_AMOUNT",
            "TAXABLE_AMOUNT"
          ]
        }
    },
    "IS_INTRA": {
      "type": "boolean"
    }
  },
  "required": [
    "LAST_USED_PROTOCOL",
    "ITEMS",
    "IS_INTRA"
  ]
}


def create_overlay_page(watermark):
    watermark_y = 740
    watermark_x = 570
    overlay_page = io.BytesIO()
    temp_pdf = canvas.Canvas(overlay_page, pagesize=letter)
    temp_pdf.setFont("Helvetica", 20)
    temp_pdf.drawRightString(watermark_x, watermark_y, str(watermark))
    temp_pdf.save()
    overlay_page.seek(0)
    return overlay_page

def create_is_intra_overlay(watermark, VAT, TAX, DOC):
    VAT_y = 740
    VAT_x = 570
    TAX_y = 740
    TAX_x = 570
    DOC_y = 740
    DOC_x = 570
    overlay_page = io.BytesIO()
    temp_pdf = canvas.Canvas(overlay_page, pagesize=letter)
    temp_pdf.setFont("Helvetica", 20)
    temp_pdf.drawRightString(VAT_x, VAT_y, str(VAT))
    temp_pdf.drawRightString(TAX_x, TAX_y, str(TAX))
    temp_pdf.drawRightString(DOC_x, DOC_y, str(DOC))
    watermark_y = 740
    watermark_x = 570
    temp_pdf.drawRightString(watermark_x, watermark_y, "A" + str(watermark))
    temp_pdf.save()
    overlay_page.seek(0)
    return overlay_page


def print_watermark(list_of_documents, last_used_protocol, is_intra):
    protocol = last_used_protocol
    for d in list_of_documents:
        try:
            document = d["item"]
            protocol = protocol + 1
            if is_intra:
                print("here3")
                overlay_page = create_is_intra_overlay(document["PROTOCOL"] or protocol, document["VAT_AMOUNT"], document["TAXABLE_AMOUNT"], document["DOC_AMOUNT"])
            else:
                overlay_page = create_overlay_page(document["PROTOCOL"] or protocol)
            new_pdf = PdfReader(overlay_page)
            output_pdf = PdfWriter()
            original_pdf = base64.decodebytes(document["CONTENT"].encode("ascii"))
            original_pdf = PdfReader(io.BytesIO(original_pdf))
            first_page = original_pdf.pages[0]
            first_page.merge_page(new_pdf.pages[0])
            output_pdf.add_page(first_page)
            for p in range(1, len(original_pdf.pages)):
                output_pdf.add_page(original_pdf.pages[p])
            tempMemory = io.BytesIO()
            output_pdf.write(tempMemory)
            newFileData = tempMemory.getvalue()
            newEncodedPDF = base64.b64encode(newFileData)
            document["CONTENT"] = newEncodedPDF.decode()
            document["PROTOCOL"] = document["PROTOCOL"] or protocol
            d["item"] = document
            d["statusCode"] = 201
            d["message"] = "Watermark applied."
        except:
            protocol = protocol - 1
            d["statusCode"] = 500
            d["message"] = "Failed to apply watermark."

    return list_of_documents


def is_base64(sb):
    try:
        if isinstance(sb, str):
            sb_bytes = bytes(sb, "ascii")
        elif isinstance(sb, bytes):
            sb_bytes = sb
        else:
            raise ValueError("Argument must be string or bytes")
        return base64.b64encode(base64.b64decode(sb_bytes)) == sb_bytes
    except Exception:
        return False


def validate_document(document):
    return is_base64(document["CONTENT"])


def validate_documents(list_of_documents):
    out_list = []
    for document in list_of_documents:
        is_valid_base_64 = validate_document(document)
        out_list.append(
            {
                "statusCode": 201 if is_valid_base_64 else 400,
                "message": "Updated"
                if is_valid_base_64
                else "Not a valid base64 string.",
                "item": document,
            }
        )
    return out_list


def is_json(payload):
    try:
        json.loads(payload)
    except ValueError as err:
        return False
    return True


def has_valid_schema(payload, is_intra):
    try:
        if is_intra:
            validate(instance=payload, schema=is_intra_payload_schema)
        else:
            validate(instance=payload, schema=payload_schema)
    except jsonschema.exceptions.ValidationError as err:
        return False
    return True


def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        payload = req.get_json()
    except:
        return func.HttpResponse(
            json.dumps({"message": "Bad request. Not JSON data"}),
            status_code=400,
            mimetype="application/json",
            charset="utf-8",
        )

    if has_valid_schema(payload, payload["IS_INTRA"]):
        list_of_documents = validate_documents(payload["ITEMS"])
        list_of_documents = print_watermark(list_of_documents, payload["LAST_USED_PROTOCOL"], payload["IS_INTRA"])
        return func.HttpResponse(
            json.dumps(list_of_documents),
            status_code=200,
            mimetype="application/json",
            charset="utf-8",
        )
    else:
        return func.HttpResponse(
            json.dumps({"message": "Bad request. Invalid schema."}),
            status_code=400,
            mimetype="application/json",
            charset="utf-8",
        )
