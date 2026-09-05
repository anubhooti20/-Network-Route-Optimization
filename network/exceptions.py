from rest_framework.views import exception_handler


def _first_message(data):
    if isinstance(data, dict):
        if "error" in data and not isinstance(data["error"], (list, dict)):
            return str(data["error"])
        for value in data.values():
            message = _first_message(value)
            if message:
                return message
        return None
    if isinstance(data, list) and data:
        return _first_message(data[0])
    if data is None:
        return None
    return str(data)


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return None

    if isinstance(response.data, dict) and set(response.data.keys()) == {"error"}:
        if not isinstance(response.data["error"], (list, dict)):
            return response

    message = _first_message(response.data) or "Invalid request"
    response.data = {"error": message}
    return response
