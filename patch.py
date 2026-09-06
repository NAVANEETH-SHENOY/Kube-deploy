import re
with open("app/main.py", "r") as f:
    code = f.read()

old_code = re.search(r'@app\.middleware\("http"\)\nasync def form_to_json_middleware.*?return await call_next\(request\)', code, re.DOTALL)
if old_code:
    new_code = """class FormToJSONMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope["method"] in ["POST", "PUT", "PATCH"]:
            headers = dict(scope.get("headers", []))
            # Be careful with bytes comparison
            if b"application/x-www-form-urlencoded" in headers.get(b"content-type", b""):
                # Read the entire body
                body = b""
                more_body = True
                while more_body:
                    message = await receive()
                    body += message.get("body", b"")
                    more_body = message.get("more_body", False)
                
                # Parse the url-encoded form into a dict
                from urllib.parse import parse_qsl
                import json
                
                parsed = parse_qsl(body.decode('utf-8'), keep_blank_values=True)
                json_dict = dict(parsed)
                new_body = json.dumps(json_dict).encode("utf-8")
                
                # Overwrite headers so FastAPI sees it strictly as JSON
                headers[b"content-type"] = b"application/json"
                headers[b"content-length"] = str(len(new_body)).encode("utf-8")
                scope["headers"] = [(k, v) for k, v in headers.items()]

                # Yield the new JSON body
                received = False
                async def new_receive():
                    nonlocal received
                    if not received:
                        received = True
                        return {"type": "http.request", "body": new_body, "more_body": False}
                    return {"type": "http.request", "body": b"", "more_body": False}

                return await self.app(scope, new_receive, send)
        
        return await self.app(scope, receive, send)

# Add our pure ASGI middleware first (so it runs before routing)
app.add_middleware(FormToJSONMiddleware)"""
    with open("app/main.py", "w") as f:
        f.write(code.replace(old_code.group(0), new_code))
    print("PATCH APPLIED")
else:
    print("NOT FOUND")
