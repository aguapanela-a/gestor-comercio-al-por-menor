class DatabaseConfigurationError(RuntimeError):
    pass


class RemoteServiceError(RuntimeError):
    def __init__(self, service: str, status_code: int, message: str) -> None:
        super().__init__(message)
        self.service = service
        self.status_code = status_code
