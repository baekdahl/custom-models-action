class GenericException(Exception):
    def __init__(self, msg, code=-1):
        super().__init__(msg)
        self.code = code


class InvalidModelSchema(GenericException):
    def __init__(self, msg, code=-1):
        super().__init__(msg.split("\n")[-1], code)


class UnexpectedResult(GenericException):
    pass


class UnexpectedInput(GenericException):
    pass


class InvalidMemoryValue(GenericException):
    pass


class ModelMainEntryPointNotFound(GenericException):
    pass


class SharedAndLocalPathCollision(GenericException):
    pass


class UnInitializedGitTool(GenericException):
    pass


class NoCommonAncestor(GenericException):
    pass


class HttpRequesterException(GenericException):
    pass


class DataRobotClientError(GenericException):
    pass


class NonMergeCommitError(GenericException):
    pass