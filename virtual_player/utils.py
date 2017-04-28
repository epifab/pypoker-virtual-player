def ensure_string(val):
    try:
        val.encode("utf-8")
    except AttributeError:
        return str(val)
