import json
import jsonschema
from jsonschema import validate
from datetime import datetime

class ESGValidator:
    def __init__(self, schema_path="config/schema.json"):
        with open(schema_path, "r") as f:
            self.schema = json.load(f)

    def validate_report(self, report_dict):
        """
        Validate a single report dict against JSON schema.
        Returns (is_valid, errors)
        """
        try:
            validate(instance=report_dict, schema=self.schema)
            return True, None
        except jsonschema.ValidationError as e:
            return False, str(e)

    def add_provenance(self, report_dict, source_file, pages=None):
        """
        Add provenance info: source file, extraction timestamp, page numbers
        """
        report_dict["source_file"] = source_file
        report_dict["extracted_at"] = datetime.utcnow().isoformat()
        if pages:
            report_dict["pages"] = pages
        return report_dict
