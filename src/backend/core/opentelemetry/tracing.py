"""
Opentelemetry tracing module.
"""

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from sqlalchemy.ext.asyncio import AsyncEngine

from src.backend.config.main import settings
from src.backend.core.logger import logger


def init_tracing(app: FastAPI, engine: AsyncEngine) -> None:
    """
    Initializes OpenTelemetry tracing for the given FastAPI app and SQLAlchemy engine.

    :param app: The FastAPI app.
    :param engine: The SQLAlchemy engine.
    :return: None
    """
    try:
        exporter = OTLPSpanExporter(
            endpoint=settings.app.OTEL_EXPORTER_OTLP_ENDPOINT,
        )
        provider = TracerProvider(
            resource=Resource.create(
                {
                    "service.name": settings.app.APP_NAME,
                    "deployment.environment": settings.app.APP_MODE,
                }
            )
        )
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)

        FastAPIInstrumentor.instrument_app(app)
        HTTPXClientInstrumentor().instrument()
        SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine)

        logger.info("OpenTelemetry tracing successfully initialized.")
    except Exception as e:
        logger.error(f"Failed to initialize OpenTelemetry tracing: {e}")
        raise
