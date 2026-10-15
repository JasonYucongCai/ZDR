import random
import unittest
from fractions import Fraction

from zdr_fixtures.mathematics import (
    OPERATIONS, FalseEquation, english_integer, generate_equation,
    mandarin_integer, number_text,
)


class MathematicsTests(unittest.TestCase):
    def test_every_operation_is_false_under_independent_exact_arithmetic(self):
        rng = random.Random(20261014)
        for operation in OPERATIONS:
            for _ in range(1000):
                equation = generate_equation(rng, operation)
                left, right = equation.left, equation.right
                if operation == "add":
                    actual = Fraction(left + right)
                elif operation == "subtract":
                    actual = Fraction(left - right)
                elif operation == "multiply":
                    actual = Fraction(left * right)
                elif operation == "divide":
                    self.assertNotEqual(right, 0)
                    actual = Fraction(left, right)
                else:
                    actual = Fraction(left ** right)
                self.assertNotEqual(actual, equation.claimed)
                self.assertTrue(equation.is_false)
                self.assertEqual(set(equation.render()), {"math", "en", "zh"})

    def test_known_translation(self):
        equation = FalseEquation("add", 2, 3, Fraction(6))
        self.assertEqual(equation.render(), {
            "math": "(2) + (3) = (6)",
            "en": "Two plus three equals six.",
            "zh": "\u4e8c\u52a0\u4e09\u7b49\u4e8e\u516d\u3002",
        })
        self.assertEqual(number_text(Fraction(-3, 2), "en"), "negative three over two")
        self.assertEqual(number_text(Fraction(-3, 2), "zh"), "\u8d1f\u4e8c\u5206\u4e4b\u4e09")

    def test_integer_words_and_range(self):
        self.assertEqual(english_integer(20104), "twenty thousand one hundred four")
        self.assertEqual(mandarin_integer(1001), "\u4e00\u5343\u96f6\u4e00")
        self.assertEqual(mandarin_integer(12), "\u5341\u4e8c")
        self.assertEqual(mandarin_integer(112), "\u4e00\u767e\u4e00\u5341\u4e8c")
        self.assertEqual(mandarin_integer(10012), "\u4e00\u4e07\u96f6\u4e00\u5341\u4e8c")
        for converter in (english_integer, mandarin_integer):
            with self.assertRaises(ValueError):
                converter(1_000_000)

    def test_deterministic_and_bad_operation(self):
        self.assertEqual(generate_equation(random.Random(7)), generate_equation(random.Random(7)))
        with self.assertRaises(ValueError):
            generate_equation(random.Random(7), "unknown")


if __name__ == "__main__":
    unittest.main()