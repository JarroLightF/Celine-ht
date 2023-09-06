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
                "type": ["number", "null"]
            },
            "DOC_AMOUNT":{
                "type": ["number", "null"]
            },
            "TAXABLE_AMOUNT":{
                "type": ["number", "null"]
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
    },
    "CURRENCY_SYMBOL": {
      "type": "string"
    },
    "INTRA_VAT_PERC": {
      "type": "number"
    }
  },
  "required": [
    "LAST_USED_PROTOCOL",
    "ITEMS",
    "IS_INTRA",
    "CURRENCY_SYMBOL",
    "INTRA_VAT_PERC"
  ]
}


def create_overlay_page(watermark, is_intra):
    watermark_y = 740
    watermark_x = 570
    overlay_page = io.BytesIO()
    temp_pdf = canvas.Canvas(overlay_page, pagesize=letter)
    temp_pdf.setFont("Helvetica", 20)
    if is_intra:
        temp_pdf.drawRightString(watermark_x, watermark_y, "A" + str(watermark))
    else:
        temp_pdf.drawRightString(watermark_x, watermark_y, str(watermark))
    temp_pdf.save()
    overlay_page.seek(0)
    return overlay_page

def replace_last(string, old, new):
    if old not in string:
        return string

    index = string.rfind(old)

    return string[:index] + new + string[index+len(old):]

def create_is_intra_overlay(VAT, TAX, DOC, currency, vat_perc):
    TAX_y = 210
    TAX_x = 560
    VAT_y = 190
    VAT_x = 560
    DOC_y = 170
    DOC_x = 560
    overlay_page = io.BytesIO()
    temp_pdf = canvas.Canvas(overlay_page, pagesize=letter)
    temp_pdf.setFont("Helvetica", 10)
    temp_pdf.drawRightString(TAX_x, TAX_y, "Taxable amt: " + str(replace_last('{:,.2f}'.format(TAX).replace(',','.'), ".", ",")) + " " + str(currency))
    temp_pdf.drawRightString(VAT_x, VAT_y, "VAT (" + str(int(vat_perc*100)) + "%): " + str(replace_last('{:,.2f}'.format(VAT).replace(',','.'), ".", ",")) + " " + str(currency))
    temp_pdf.drawRightString(DOC_x, DOC_y, "Total: " + str(replace_last('{:,.2f}'.format(DOC).replace(',','.'), ".", ",")) + " " + str(currency))
    temp_pdf.save()
    overlay_page.seek(0)
    return overlay_page


def print_watermark(list_of_documents, last_used_protocol, is_intra, currency, vat_perc):
    protocol = last_used_protocol
    for d in list_of_documents:
        try:
            document = d["item"]
            protocol = protocol + 1
            if is_intra:
                is_intra_overlay_page = create_is_intra_overlay(document["VAT_AMOUNT"] or 0, document["TAXABLE_AMOUNT"] or 0, document["DOC_AMOUNT"] or 0, currency, vat_perc)
            overlay_page = create_overlay_page(document["PROTOCOL"] or protocol, is_intra)
            new_pdf = PdfReader(overlay_page)
            if is_intra:
              new_is_intra_pdf = PdfReader(is_intra_overlay_page)
            output_pdf = PdfWriter()
            original_pdf = base64.decodebytes(document["CONTENT"].encode("ascii"))
            original_pdf = PdfReader(io.BytesIO(original_pdf))
            first_page = original_pdf.pages[0]
            if is_intra:
              last_page = original_pdf.pages[len(original_pdf.pages)-1]
            first_page.merge_page(new_pdf.pages[0])
            if is_intra:
              last_page.merge_page(new_is_intra_pdf.pages[0])
            output_pdf.add_page(first_page)
            for p in range(1, len(original_pdf.pages)-1 if is_intra else len(original_pdf.pages)):
                output_pdf.add_page(original_pdf.pages[p])
            if is_intra:
              output_pdf.add_page(last_page)
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
        if payload["IS_INTRA"]:
          list_of_documents = print_watermark(list_of_documents, payload["LAST_USED_PROTOCOL"], payload["IS_INTRA"], payload["CURRENCY_SYMBOL"], payload["INTRA_VAT_PERC"])
        else:
          list_of_documents = print_watermark(list_of_documents, payload["LAST_USED_PROTOCOL"], payload["IS_INTRA"], "", "")
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
