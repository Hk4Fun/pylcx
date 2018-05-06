__author__ = 'Hk4Fun'
__date__ = '2018/5/6 20:10'


class ChapError(Exception):
    pass


class ProtocolException(ChapError):
    def __init__(self, error_code):
        super().__init__(self)
        self.error_code = error_code

    def __str__(self):
        return 'Error packet code {}'.format(self.error_code)


class IdentifierException(ChapError):
    def __init__(self, error_id):
        super().__init__(self)
        self.error_id = error_id

    def __str__(self):
        return 'Error identifier {}'.format(self.error_id)


class VarifyError(ChapError):
    def __init__(self, ):
        super().__init__(self)

    def __str__(self):
        return 'Identity or secret is incorrect'


class ConnectIdException(ChapError):
    def __init__(self, error_id):
        super().__init__(self)
        self.error_id = error_id

    def __str__(self):
        return 'Error connect_id {}'.format(self.error_id)


class RequestIdException(ChapError):
    def __init__(self, error_id):
        super().__init__(self)
        self.error_id = error_id

    def __str__(self):
        return 'Error connect_id {}'.format(self.error_id)