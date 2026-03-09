"""OpenTelemetry telemetry setup with Application Insights support.

This module provides a centralized way to configure OpenTelemetry tracing and
metrics for the MCP server and client.  When the
``APPLICATIONINSIGHTS_CONNECTION_STRING`` environment variable is set the
telemetry data is exported to Azure Application Insights; otherwise a console
exporter is used as a fallback.
"""

import os
import logging
from typing import Optional

from opentelemetry import trace, metrics
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    ConsoleMetricExporter,
    PeriodicExportingMetricReader,
)

logger = logging.getLogger(__name__)

# Track whether telemetry has already been initialized so that calling
# ``setup_telemetry`` multiple times is safe (idempotent).
_telemetry_initialized = False


def setup_telemetry(service_name: str = "mcp-service") -> None:
    """Initialize OpenTelemetry tracing and metrics.

    If ``APPLICATIONINSIGHTS_CONNECTION_STRING`` is present in the environment
    the Azure Monitor exporters are used so that data flows into Application
    Insights.  Otherwise a console exporter is used which writes spans/metrics
    to stdout – useful for local development.

    This function is idempotent and safe to call multiple times.

    Args:
        service_name: Logical service name recorded in every span/metric.
    """
    global _telemetry_initialized  # noqa: PLW0603
    if _telemetry_initialized:
        return

    resource = Resource.create({SERVICE_NAME: service_name})
    connection_string = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")

    if connection_string:
        tracer_provider, meter_provider = _build_azure_monitor_providers(
            resource, connection_string
        )
    else:
        tracer_provider, meter_provider = _build_console_providers(resource)

    trace.set_tracer_provider(tracer_provider)
    metrics.set_meter_provider(meter_provider)

    _telemetry_initialized = True


def _build_azure_monitor_providers(
    resource: Resource, connection_string: str
) -> tuple:
    """Create tracer/meter providers backed by Azure Monitor (Application Insights)."""
    try:
        from azure.monitor.opentelemetry.exporter import (
            AzureMonitorTraceExporter,
            AzureMonitorMetricExporter,
        )

        tracer_provider = TracerProvider(resource=resource)
        tracer_provider.add_span_processor(
            BatchSpanProcessor(
                AzureMonitorTraceExporter(connection_string=connection_string)
            )
        )

        metric_reader = PeriodicExportingMetricReader(
            AzureMonitorMetricExporter(connection_string=connection_string),
            export_interval_millis=60_000,
        )
        meter_provider = MeterProvider(
            resource=resource, metric_readers=[metric_reader]
        )

        logger.info(
            "OpenTelemetry configured with Azure Monitor (Application Insights)"
        )
        return tracer_provider, meter_provider

    except ImportError as exc:
        logger.warning(
            "Failed to load azure-monitor-opentelemetry-exporter (%s); "
            "falling back to console exporter. "
            "Ensure it is installed and compatible with the opentelemetry-sdk version: "
            "pip install azure-monitor-opentelemetry-exporter",
            exc,
        )
        return _build_console_providers(resource)


def _build_console_providers(resource: Resource) -> tuple:
    """Create tracer/meter providers that write to stdout."""
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

    metric_reader = PeriodicExportingMetricReader(
        ConsoleMetricExporter(),
        export_interval_millis=60_000,
    )
    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])

    logger.info(
        "OpenTelemetry configured with console exporter "
        "(set APPLICATIONINSIGHTS_CONNECTION_STRING for Application Insights)"
    )
    return tracer_provider, meter_provider


def get_tracer(name: str) -> trace.Tracer:
    """Return an OpenTelemetry :class:`~opentelemetry.trace.Tracer`.

    Args:
        name: Instrumentation scope name (typically ``__name__``).
    """
    return trace.get_tracer(name)


def get_meter(name: str) -> metrics.Meter:
    """Return an OpenTelemetry :class:`~opentelemetry.metrics.Meter`.

    Args:
        name: Instrumentation scope name (typically ``__name__``).
    """
    return metrics.get_meter(name)


def record_exception(span: Optional[trace.Span], exc: Exception) -> None:
    """Record an exception on the current span and set its status to ERROR.

    Args:
        span: The span to record the exception on.  If ``None`` this is a no-op.
        exc: The exception to record.
    """
    if span is None:
        return
    span.record_exception(exc)
    span.set_status(trace.StatusCode.ERROR, str(exc))
