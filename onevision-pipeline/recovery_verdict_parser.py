import json

def parse_recovery_verdict(text, strict_parser):
    try:
        return strict_parser(text)
    except json.JSONDecodeError as error:
        if not error.msg.startswith('Invalid control character'):
            raise
        value = text.strip()
        if value.startswith('```'):
            value = value.split('\n', 1)[1].rsplit('```', 1)[0].strip()
        verdict = json.loads(value, strict=False)
        # The strict parser below still validates the exact schema and types.
        # Only JSON whitespace controls in the explanation may be normalized.
        if not isinstance(verdict, dict) or not isinstance(verdict.get('reason'), str):
            raise error
        reason = verdict['reason']
        if any(ord(c) < 32 and c not in '\t\n\r' for c in reason):
            raise error
        return strict_parser(json.dumps(verdict, ensure_ascii=False))
