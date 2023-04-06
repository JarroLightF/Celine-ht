import logging
import json
from final import is_json, is_base64, has_valid_schema, validate_documents, print_watermark
import azure.functions as func


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    payload = req.get_body()
    print(payload[:200])
    if is_json(payload["data"]):
        json_payload = json.loads(payload["data"])
        if has_valid_schema(json_payload):
            list_of_documents = validate_documents(json_payload)
            list_of_documents = print_watermark(list_of_documents)
            return func.HttpResponse(
                json.dumps(list_of_documents),
                status_code=200,
                mimetype="application/json",
                charset='utf-8',
            )
        else:
            return func.HttpResponse(
                json.dumps({"ciao": "asddsa"}),
                status_code=406,
                mimetype="application/json",
                charset='utf-8',
            )
    else:
        return func.HttpResponse(
            json.dumps({"ciao": "asddsa"}),
            status_code=405,
            mimetype="application/json",
            charset='utf-8',
        )
