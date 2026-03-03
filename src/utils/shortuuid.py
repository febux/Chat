"""
ShortUUID is a short, URL-safe unique identifier as defined by RFC 4122.
It's a 32-character hexadecimal string, which is shorter and easier to remember than a longer.
"""

import uuid

DEFAULT_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def _int_to_base(n: int, alphabet: str = DEFAULT_ALPHABET) -> str:
    """
    Converts an integer to base len(alphabet).

    :param n: The number to convert.
    :param alphabet: The alphabet to use for conversion.
    :return: The converted string.
    """
    if n == 0:
        return alphabet[0]

    base = len(alphabet)
    chars: list[str] = []
    while n > 0:
        n, rem = divmod(n, base)
        chars.append(alphabet[rem])

    return "".join(reversed(chars))


def _base_to_int(s: str, alphabet: str = DEFAULT_ALPHABET) -> int:
    """
    Reverse conversion: string to number.

    :param s: The string to convert.
    :param alphabet: The alphabet to use for conversion.
    :return: The converted number.
    """
    base = len(alphabet)
    lookup = {ch: i for i, ch in enumerate(alphabet)}
    n = 0
    for ch in s:
        n = n * base + lookup[ch]
    return n


def encode_uuid(u: uuid.UUID, alphabet: str = DEFAULT_ALPHABET) -> str:
    """
    Convert UUID to shortuuid string (~22 characters).

    :param u: The UUID to convert.
    :param alphabet: The alphabet to use for conversion.
    :return: The converted shortuuid string.
    """
    return _int_to_base(u.int, alphabet)


def decode_uuid(s: str, alphabet: str = DEFAULT_ALPHABET) -> uuid.UUID:
    """
    Reverse: shortuuid-string -> UUID.

    :param s: The shortuuid-string to convert.
    :param alphabet: The alphabet to use for conversion.
    :return: The converted UUID.
    """
    n = _base_to_int(s, alphabet)
    return uuid.UUID(int=n)


def shortuuid(alphabet: str = DEFAULT_ALPHABET) -> str:
    """
    Generate a new shortuuid for uuid4().

    :param alphabet: The alphabet to use for conversion.
    :return: The new shortuuid string.
    """
    return encode_uuid(uuid.uuid4(), alphabet)
