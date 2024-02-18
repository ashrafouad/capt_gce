import unittest

test_strings = [
    ("", "a", 1),
    ("a", "", 1),
    ("", "", 0),
    ("levenshtein", "levenshtein", 0),
    ("DwAyNE", "DUANE", 2),
    ("dwayne", "DuAnE", 5),
    ("aarrgh", "aargh", 1),
    ("aargh", "aarrgh", 1),
    ("sitting", "kitten", 3),
    ("gumbo", "gambol", 2),
    ("saturday", "sunday", 3),
    ("a", "b", 1),
    ("ab", "ac", 1),
    ("ac", "bc", 1),
    ("abc", "axc", 1),
    ("xabxcdxxefxgx", "1ab2cd34ef5g6", 6),
    ("xabxcdxxefxgx", "abcdefg", 6),
    ("javawasneat", "scalaisgreat", 7),
    ("example", "samples", 3),
    ("sturgeon", "urgently", 6),
    ("levenshtein", "frankenstein", 6),
    ("distance", "difference", 5),
    ("kitten", "sitting", 3),
    ("Tier", "Tor", 2),
    ("😄", "😦", 1),
    ("😘", "😘", 0),
]


class Levenshtein(unittest.TestCase):
    def test_distances(self):
        for a, b, expected in test_strings:
            self.assertEqual(a(a, b), expected, f"left input = {a}, right input= {b}")

    def test_associativity(self):
        for a, b, _ in test_strings:
            self.assertEqual(
                a(a, b),
                a(b, a),
                f"left input = {a}, right input= {b}",
            )


if __name__ == "__main__":
    unittest.main()
