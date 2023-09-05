import json
import azure.functions as func
import io
import base64
import jsonschema
from PyPDF2 import PdfReader
from jsonschema import validate

# from PyPDF2 import PdfReader

payload_schema = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {"ID": {"type": "integer"}, "CONTENT": {"type": "string"}},
        "required": ["ID", "CONTENT"],
    },
}


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


def has_valid_schema(payload):
    try:
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

    if has_valid_schema(payload):
        out_array = []
        for item in payload:
            try:
                full_extracted_text = ""
                original_pdf = base64.decodebytes(item["CONTENT"].encode("ascii"))
                if len(item["CONTENT"].encode("ascii"))>0:
                    try:
                        original_pdf = PdfReader(io.BytesIO(original_pdf))
                        for page in original_pdf.pages:
                            full_extracted_text = full_extracted_text + page.extract_text()
                        item["EXTRACTED_TEXT"] = full_extracted_text
                        out_array.append(item)
                    except:
                        item["EXTRACTED_TEXT"] = ""
                        out_array.append(item)
                else:
                    item["EXTRACTED_TEXT"] = ""
                    out_array.append(item)
            except:
                item["EXTRACTED_TEXT"] = ""
                out_array.append(item)
        return func.HttpResponse(
            json.dumps(out_array),
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
