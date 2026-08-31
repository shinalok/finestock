import unittest
from finestock.model import Price

class TestPrice(unittest.TestCase):
    def test_price_creation(self):
        # workday, code, price, open, high, low, close, volume, volume_amt
        price = Price.from_values(
            "20250101", "005930", 70000, 69000, 71000, 68000, 70000, 1000, 70000000
        )
        self.assertEqual(price.code, "005930")
        self.assertEqual(price.price, 70000.0)
        self.assertEqual(price.volume, 1000)

if __name__ == '__main__':
    unittest.main()
