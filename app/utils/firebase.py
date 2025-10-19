import urllib.parse

def encode_firebase_path(url):
    if not url:
        return None  # Handle None URLs gracefully
    try:
        base, path_query = url.split("/o/", 1)  # Split at "/o/"
        if "?" in path_query:
            path, query = path_query.split("?", 1)
        else:
            path, query = path_query, ""
        decoded_path = urllib.parse.unquote(path)
        encoded_path = urllib.parse.quote(decoded_path, safe="/")
        return f"{base}/o/{encoded_path}?{query}" if query else f"{base}/o/{encoded_path}"
    except Exception as e:
        print(f"Error encoding URL: {e}")
        return url
