import uvicorn

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.web import create_application


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    uvicorn.run(
        create_application(settings),
        host=settings.host,
        port=settings.port,
        log_config=None,
    )


if __name__ == "__main__":
    main()
