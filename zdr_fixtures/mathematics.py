"""Construct false equalities from exact arithmetic, without evaluating strings."""

from dataclasses import dataclass
from fractions import Fraction
from random import Random


OPERATIONS = ("add", "subtract", "multiply", "divide", "power")
SMALL = (
    "zero", "one", "two", "three", "four", "five", "six", "seven",
    "eight", "nine", "ten", "eleven", "twelve", "thirteen", "fourteen",
    "fifteen", "sixteen", "seventeen", "eighteen", "nineteen",
)
TENS = ("", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety")
ZH_DIGITS = "\u96f6\u4e00\u4e8c\u4e09\u56db\u4e94\u516d\u4e03\u516b\u4e5d"


def english_integer(value: int) -> str:
    if value < 0:
        return "negative " + english_integer(-value)
    if value < 20:
        return SMALL[value]
    if value < 100:
        tens, units = divmod(value, 10)
        return TENS[tens] + ("-" + SMALL[units] if units else "")
    if value < 1000:
        hundreds, remainder = divmod(value, 100)
        return SMALL[hundreds] + " hundred" + (" " + english_integer(remainder) if remainder else "")
    if value < 1_000_000:
        thousands, remainder = divmod(value, 1000)
        return english_integer(thousands) + " thousand" + (" " + english_integer(remainder) if remainder else "")
    raise ValueError("Number outside the supported verbalization range")


def mandarin_integer(value: int) -> str:
    if value < 0:
        return "\u8d1f" + mandarin_integer(-value)
    if value < 10:
        return ZH_DIGITS[value]
    if value >= 1_000_000:
        raise ValueError("Number outside the supported verbalization range")
    for unit, name in ((10000, "\u4e07"), (1000, "\u5343"), (100, "\u767e"), (10, "\u5341")):
        if value >= unit:
            leading, remainder = divmod(value, unit)
            prefix = "" if unit == 10 and leading == 1 else mandarin_integer(leading)
            result = prefix + name
            if remainder:
                gap = "\u96f6" if unit >= 100 and remainder < unit // 10 else ""
                leading_one = "\u4e00" if 10 <= remainder < 20 else ""
                result += gap + leading_one + mandarin_integer(remainder)
            return result
    raise ValueError("Unsupported integer")


def number_text(value: Fraction, language: str) -> str:
    if language not in ("en", "zh"):
        raise ValueError("Language must be en or zh")
    integer_text = english_integer if language == "en" else mandarin_integer
    if value.denominator == 1:
        return integer_text(value.numerator)
    if language == "en":
        return integer_text(value.numerator) + " over " + integer_text(value.denominator)
    sign = "\u8d1f" if value < 0 else ""
    return sign + integer_text(value.denominator) + "\u5206\u4e4b" + integer_text(abs(value.numerator))


def calculate(operation: str, left: int, right: int) -> Fraction:
    if operation == "add":
        return Fraction(left + right)
    if operation == "subtract":
        return Fraction(left - right)
    if operation == "multiply":
        return Fraction(left * right)
    if operation == "divide":
        return Fraction(left, right)
    if operation == "power":
        return Fraction(left ** right)
    raise ValueError(f"Unknown operation: {operation}")


@dataclass(frozen=True)
class FalseEquation:
    operation: str
    left: int
    right: int
    claimed: Fraction

    @property
    def actual(self) -> Fraction:
        return calculate(self.operation, self.left, self.right)

    @property
    def is_false(self) -> bool:
        return self.claimed != self.actual

    def render(self) -> dict[str, str]:
        symbols = {"add": "+", "subtract": "-", "multiply": "*", "divide": "/", "power": "^"}
        english_ops = {
            "add": "plus", "subtract": "minus", "multiply": "multiplied by",
            "divide": "divided by", "power": "raised to the power of",
        }
        mandarin_ops = {
            "add": "\u52a0", "subtract": "\u51cf", "multiply": "\u4e58\u4ee5",
            "divide": "\u9664\u4ee5", "power": "\u7684",
        }
        english = f"{english_integer(self.left)} {english_ops[self.operation]} {english_integer(self.right)}"
        mandarin = mandarin_integer(self.left) + mandarin_ops[self.operation] + mandarin_integer(self.right)
        if self.operation == "power":
            mandarin += "\u6b21\u65b9"
        return {
            "math": f"({self.left}) {symbols[self.operation]} ({self.right}) = ({self.claimed})",
            "en": english.capitalize() + " equals " + number_text(self.claimed, "en") + ".",
            "zh": mandarin + "\u7b49\u4e8e" + number_text(self.claimed, "zh") + "\u3002",
        }


def generate_equation(rng: Random, operation: str | None = None) -> FalseEquation:
    selected = operation if operation is not None else rng.choice(OPERATIONS)
    if selected not in OPERATIONS:
        raise ValueError(f"Unknown operation: {selected}")
    left = rng.randint(-50, 50)
    right = rng.randint(-50, 50)
    if selected == "divide":
        right = rng.choice(tuple(number for number in range(-20, 21) if number))
    if selected == "power":
        left, right = rng.randint(-12, 12), rng.randint(2, 4)
    actual = calculate(selected, left, right)
    offset = rng.choice(tuple(number for number in range(-9, 10) if number))
    return FalseEquation(selected, left, right, actual + offset)