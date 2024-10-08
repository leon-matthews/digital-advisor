
import math


def round_significant(number, digits=2):
    """
    Round number to the given number of sigificant digits. eg::

        >>> round_significant(1235, digits=2)
        1200

    Returns: Number rounded to the given number of digits
    """
    digits = int(digits)
    if digits <= 0:
        raise ValueError("Must have more than zero significant digits")

    if not number:
        return 0
    number = float(number)
    magnitude = int(math.floor(math.log10(abs(number))))
    ndigits = digits - magnitude - 1
    return round(number, ndigits)
