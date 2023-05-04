import logging

import azure.functions as func

import json
import jsonschema
from jsonschema import validate

import re

payload_schema = {
  "type": "array",
  "items": {
      "type": "object",
      "properties": {
        "STRING_TO_CHECK": {
          "type": "string"
        },
        "PATTERNS": {
          "type": "array",
          "items": 
            {
              "type": "string"
            }
        }
      },
      "required": [
        "STRING_TO_CHECK",
        "PATTERNS"
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
            temp = '(?:% s)' % '|'.join(item["PATTERNS"])
            res = False
            try:
                re.compile(temp)
                if re.match(temp, item["STRING_TO_CHECK"]):
                    res = True
                    matching_regex = temp
                    out_array.append(
                        {
                            "STRING_TO_CHECK": item["STRING_TO_CHECK"],
                            "PATTERNS":        matching_regex,
                            "IS_MATCH":        res
                        }
                    )
                else:
                    out_array.append(
                        {
                            "STRING_TO_CHECK": item["STRING_TO_CHECK"],
                            "PATTERNS":        temp,
                            "IS_MATCH":        False
                        }
                    )
            except re.error:
                return func.HttpResponse(
                    json.dumps({"message": "Invalid Pattern"}),
                    status_code=400,
                    mimetype="application/json",
                    charset='utf-8',
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
        
