class MissingEnviromentVariable(Exception):
    pass


class StatusCodeNotOK(Exception):
    pass


class JsonConvertingError(Exception):
    pass


class GetRequestError(Exception):
    pass


class IncorrectHomeworkStatus(Exception):
    pass


class NoMatchStatusHomework(Exception):
    pass


class SendMessageError(Exception):
    pass