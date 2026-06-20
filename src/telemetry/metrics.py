try:
    from prometheus_client import Counter, Histogram
    HAVE_PROM = True
except Exception:
    # Lightweight stubs so code can run without prometheus_client installed
    HAVE_PROM = False

    class Counter:
        def __init__(self, *args, **kwargs):
            self._val = 0

        def inc(self, amt=1):
            self._val += amt

    class Histogram:
        def __init__(self, *args, **kwargs):
            pass

        def observe(self, value):
            pass


def init_metrics():
    metrics = {}
    metrics['ollama_requests_total'] = Counter('ollama_requests_total', 'Total Ollama requests')
    metrics['ollama_requests_failed'] = Counter('ollama_requests_failed', 'Failed Ollama requests')
    metrics['ollama_request_latency_seconds'] = Histogram('ollama_request_latency_seconds', 'Ollama request latency seconds')
    metrics['classification_requests_total'] = Counter('classification_requests_total', 'Total classification requests')
    metrics['classification_latency_seconds'] = Histogram('classification_latency_seconds', 'Classifier latency seconds')
    return metrics
