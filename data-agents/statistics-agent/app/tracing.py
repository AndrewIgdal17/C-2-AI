from app.config import OTEL_ENABLED, OTEL_ENDPOINT

if OTEL_ENABLED:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider, ReadableSpan
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

    class FilteringProcessor(BatchSpanProcessor):
        NOISE = {"http send", "http receive"}
        def on_end(self, span: ReadableSpan) -> None:
            for noise in self.NOISE:
                if noise in span.name:
                    return
            super().on_end(span)

    resource = Resource.create({"service.name": "statistics-agent"})
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=OTEL_ENDPOINT, insecure=True)
    provider.add_span_processor(FilteringProcessor(exporter))
    trace.set_tracer_provider(provider)

    HTTPXClientInstrumentor().instrument()

    tracer = trace.get_tracer("statistics-agent")

    def instrument_app(app):
        FastAPIInstrumentor.instrument_app(app, excluded_urls="health")
else:
    from opentelemetry import trace

    tracer = trace.get_tracer("statistics-agent")

    def instrument_app(app):
        pass
