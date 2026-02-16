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

class CompanyAlreadyExistsError(JobFinderError):
    """Raised when a company already exists."""
    pass

class CompanyNotFoundError(JobFinderError):
    """Raised when a company is not found."""
    pass

class CompanyValidationError(JobFinderError):
    """Raised when a company status transition is invalid."""
    pass