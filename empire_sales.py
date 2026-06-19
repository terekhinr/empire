"""Каркас empire_sales — webhook и health (ТЗ §4.6, фаза 4)."""

from __future__ import annotations

import logging
import os

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from empire_flags import load_empire_flags
from sales_db import init_sales_db, npd_limit_alert

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("empire.sales")

app = FastAPI(title="empire_sales", version="0.1.0")
WEBHOOK_SECRET = os.getenv("YOOKASSA_WEBHOOK_SECRET", "")


@app.on_event("startup")
def _startup():
    init_sales_db()


@app.get("/health")
def health():
    flags = load_empire_flags()
    alert = npd_limit_alert()
    return {
        "status": "ok",
        "stop_sales": flags.get("stop_sales", True),
        "npd": alert,
    }


@app.get("/products")
def products_list():
    from sales_db import list_products

    return {"products": list_products()}


@app.post("/webhook/yookassa")
async def yookassa_webhook(
    request: Request,
    x_webhook_secret: str | None = Header(default=None, alias="X-Webhook-Secret"),
):
    if load_empire_flags().get("stop_sales"):
        raise HTTPException(503, "stop_sales")
    if WEBHOOK_SECRET and x_webhook_secret != WEBHOOK_SECRET:
        raise HTTPException(401, "invalid secret")
    body = await request.json()
    logger.info("yookassa_event type=%s", body.get("event"))
    return JSONResponse({"ok": True, "mode": "stub_logged"})


def main():
    import uvicorn

    port = int(os.getenv("EMPIRE_SALES_PORT", "8002"))
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")


if __name__ == "__main__":
    main()
