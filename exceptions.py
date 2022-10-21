"""Module with custom exceptions."""


class SendMessageFailure(Exception):
    """Send message failure exception."""

    pass


class APIResponseStatusCodeException(Exception):
    """API status code exception."""

    pass


class CheckResponseException(Exception):
    """Wrong API response format exception."""

    pass


class UnknownHWStatusException(Exception):
    """Unknown homework status exception."""

    pass


class MissingRequiredTokenException(Exception):
    """Environment variables unavaliable exception."""

    pass


class IncorrectAPIResponseException(Exception):
    """Incorrect API response exception."""

    pass


class EmptyHWNameOrStatus(Exception):
    """None homework name or status exception."""

    pass
