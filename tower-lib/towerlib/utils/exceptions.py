class TowerException(Exception):
    pass

class UnkownHost(TowerException):
    pass

class DiscoveringTimeOut(TowerException):
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
