import asyncio
from app.services.ai_orchestrator import analyze_recording

async def main():
    try:
        res = await analyze_recording(b'test audio', 'tech-interview', 'demo')
        print(res)
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    asyncio.run(main())
