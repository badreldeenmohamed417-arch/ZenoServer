class ZenoError(Exception):
    """Base error for the Zeno Knowledge Engine."""

class ConfigurationError(ZenoError): pass
class ExtractionError(ZenoError): pass
class ValidationError(ZenoError): pass
class EmbeddingError(ZenoError): pass
class VectorStoreError(ZenoError): pass
class RetrievalError(ZenoError): pass
class LLMError(ZenoError): pass
