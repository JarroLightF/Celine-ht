import requests
import logging
import json
from final import is_json, is_base64, has_valid_schema, validate_documents, print_watermark
import azure.functions as func


def main2(data):
    logging.info('Python HTTP trigger function processed a request.')

    payload = data
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
            return {
                "data": json.dumps({"ciao": "asddsa"}),
                "data2":  406,
                "data3":  "application/json",
                "data4":  'utf-8',
            }
    else:
        return {
            "data": json.dumps({"ciao": "asddsa"}),
            "data2":  406,
            "data3":  "application/json",
            "data4":  'utf-8',
        }


with open("test.json", "rb") as file:
    data = file.read()
requests.post(
    "http://localhost:7071/api/celineWatermark",
    data
)
