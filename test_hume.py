import asyncio, httpx
async def test():
    async with httpx.AsyncClient() as client:
        try:
            await client.post('http://httpbin.org/post', json={'a':1}, files={'f': b'data'})
        except Exception as e:
            import traceback; traceback.print_exc()
asyncio.run(test())
