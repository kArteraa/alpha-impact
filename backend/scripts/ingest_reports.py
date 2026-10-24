import asyncio

from sqlalchemy.ext.asyncio import async_sessionmaker

from apps.services.house_view.ingest.config import load_config
from apps.services.house_view.ingest.ocr import TesseractOcr
from apps.services.house_view.ingest.pipeline import ingest_reports
from main import build_container
from shared.config.paths import RAW_DIR
from shared.contracts.ports import LLMGateway


async def main() -> None:
    config = load_config()
    container = build_container()
    try:
        result = await ingest_reports(
            container.resolve(async_sessionmaker),
            container.resolve(LLMGateway),
            TesseractOcr(config.ocr_languages, config.ocr_timeout_seconds),
            RAW_DIR,
            config,
        )
        print(f"pages: {result.pages}")
        print(f"claims: {result.claims}")
        print(f"failed pages: {', '.join(result.failed) or '-'}")
        print(f"truncated pages: {', '.join(result.truncated) or '-'}")
    finally:
        await container.aclose()


if __name__ == "__main__":
    asyncio.run(main())
