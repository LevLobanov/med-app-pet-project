import asyncio
import uvicorn


async def main():
    config = uvicorn.Config("rest:app", host = "127.0.0.1", port = 8000, reload = True)
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        SystemExit(0)
