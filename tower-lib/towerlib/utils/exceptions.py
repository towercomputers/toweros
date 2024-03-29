class TowerException(Exception):
    pass

class UnkownHost(TowerException):
    pass

class DiscoveringTimeOut(TowerException):
    pass

class DiscoveringException(TowerException):
    pass

class MissingEnvironmentValue(TowerException):
    pass

class InvalidChecksum(TowerException):
    pass

class NxTimeoutException(TowerException):
    pass

class NetworkException(TowerException):
    pass

class LockException(TowerException):
    pass

class BuildException(TowerException):
    pass

class InvalidColor(TowerException):
    pass

class ServerTimeoutException(TowerException):
    pass

class CommandNotFound(TowerException):
    pass
