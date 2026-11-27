import asyncio
import importlib.util
import sys
from pathlib import Path
from asyncio import start_server

import uvloop

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

from helpers.logger import LOGGER
from bot import ItsMrULPBot, start_bot
from helpers.auth import setup_access_control
from helpers.cloud_sync import sync_from_channel_on_startup, register_channel_watcher

HANDLER_DIRS = [
    Path(__file__).parent / "core",
    Path(__file__).parent / "modules",
]


def load_handlers():
    for directory in HANDLER_DIRS:
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.py")):
            if path.name == "__init__.py":
                continue
            module_name = f"{directory.name}.{path.stem}"
            if module_name in sys.modules:
                continue
            try:
                spec = importlib.util.spec_from_file_location(module_name, path)
                if spec is None:
                    continue
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)
            except Exception as e:
                LOGGER.error(f"Failed to load {module_name}: {e}")


async def health_check_handler(reader, writer):
    await reader.read(1024)
    writer.write(b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: 2\r\n\r\nOK")
    await writer.drain()
    writer.close()


async def run_bot():
    await start_server(health_check_handler, "0.0.0.0", 8000)
    await start_bot()
    setup_access_control(ItsMrULPBot)
    register_channel_watcher(ItsMrULPBot)
    load_handlers()
    await sync_from_channel_on_startup(ItsMrULPBot)
    LOGGER.info("Bot Successfully Started!")
    await ItsMrULPBot.run_until_disconnected()


if __name__ == "__main__":
    try:
        loop.run_until_complete(run_bot())
    except KeyboardInterrupt:
        LOGGER.info("Bot stopped by user")
    except Exception as e:
        LOGGER.error(f"Fatal error: {e}")
        sys.exit(1)
