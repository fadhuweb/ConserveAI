"""Fill the Jan-May 2026 gap in daily_features and forecasts tables."""

import sys
import logging
from datetime import date, timedelta

sys.path.insert(0, ".")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

from src.backend.jobs.daily_forecast import run_and_save, _init_gee

_init_gee()

start   = date(2026, 1, 1)
end     = date(2026, 6, 3)
current = start
total   = (end - start).days + 1
done    = 0

while current <= end:
    logger.info("Processing %s  (%d/%d)", current, done + 1, total)
    run_and_save(current)
    current += timedelta(days=1)
    done += 1

logger.info("Gap fill complete — %d days processed.", done)