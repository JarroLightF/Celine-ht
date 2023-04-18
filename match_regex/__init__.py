import logging

import azure.functions as func

import json
import jsonschema
from jsonschema import validate

import re

payload_schema = {
    "type": "array",
    "items":{
        "type": "object",
        "properties": {
            "STRING_TO_CHECK": {"type": "string"},
            "PATTERN": {"type":"string"}
        },
        "required":[
            "STRING_TO_CHECK",
            "PATTERN"
        ]
    }
}

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
            status_code= 400,
            mimetype="application/json",
            charset='utf-8',
        )
    
    out_array = []
    if has_valid_schema(payload):
        for item in payload:
            out_array.append(
                {
                    "STRING_TO_CHECK": item["STRING_TO_CHECK"],
                    "PATTERN":         item["PATTERN"],
                    "IS_MATCH":        bool(re.match(item["PATTERN"], item["STRING_TO_CHECK"]))
                }
            )
        return func.HttpResponse(
            json.dumps(out_array),
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
        
