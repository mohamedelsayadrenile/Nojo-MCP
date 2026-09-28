class NojoAPIError(Exception):
    pass


class TokenExchangeRejectedError(NojoAPIError):
    pass


class NojoAPIRequestError(NojoAPIError):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
