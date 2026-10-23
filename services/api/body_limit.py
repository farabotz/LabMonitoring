from starlette.exceptions import HTTPException


class BodyLimitMiddleware:
    """Limit actual streamed bytes, including chunked multipart, before spooling."""
    def __init__(self, app, maximum=6_000_000):
        self.app, self.maximum = app, maximum

    async def __call__(self, scope, receive, send):
        total = 0
        async def bounded_receive():
            nonlocal total
            message = await receive()
            if message["type"] == "http.request":
                total += len(message.get("body", b""))
                if total > self.maximum:
                    raise HTTPException(413, "Sampel terlalu besar.")
            return message
        await self.app(scope, bounded_receive if scope["type"] == "http" else receive, send)
