class NojoAPIError(Exception):
    pass


class TokenExchangeRejectedError(NojoAPIError):
    pass


class NojoAPIRequestError(NojoAPIError):
    pass
