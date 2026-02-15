class JobFinderError(Exception):
    pass

class ProviderError(JobFinderError):
    def __init__(self, message: str, provider: str = "Unknown"):
        self.provider = provider
        super().__init__(f"[{provider}] {message}")

class RetryableProviderError(ProviderError):
    """Temporary issues (429, 500, network)"""
    pass
    
class FatalProviderError(ProviderError):
    """Permanent issues (404, 403, Bad Config)"""
    pass