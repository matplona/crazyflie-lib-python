
class SetterException(Exception):
    """ When the attribute can't be set"""
    def __init__(self, attr_name : str) -> None:
        super().__init__("The attribute {} can't be set manually".format(attr_name))
