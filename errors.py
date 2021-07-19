class BotError(Exception):...

class HTMLError(BotError): ...
class ElementNotFound(HTMLError): ...

class AccessError(BotError):
    def __init__(self, *args: object, cause="TOKEN and bot safety") -> None:
        BotError.__init__(self, *args)
        self.cause = cause
class FunctionNotAllowedError(AccessError): ...

class NewsError(BotError): ...

class TeamworkError(BotError): ...
class TeamCreationError(BotError):
    TOO_MANY = 0
    GENERAL = None
    def __init__(self, *args, code=None):
        BotError.__init__(self, *args)
        self.code = code