"""GPU benchmark harness tests; CPU-only CI doesn't require PyTorch."""
import importlib.util
import unittest
from verunai.gpu_research import neural_benchmark


class TestGPUResearch(unittest.TestCase):
    def test_bad_dimensions_refused(self):
        for options in ({"steps": 1}, {"width": 2}, {"batch": 1}, {"device": "quantum"}):
            with self.subTest(options=options), self.assertRaises(ValueError):
                neural_benchmark(**options)

    @unittest.skipUnless(importlib.util.find_spec("torch") is not None, "PyTorch optional")
    def test_real_cpu_training_loss_decreases(self):
        result = neural_benchmark(steps=12, width=32, batch=24, device="cpu")
        self.assertTrue(result["improved_on_training_data"])
        self.assertEqual(result["device"], "cpu")
        self.assertGreater(result["training_steps_per_second"], 0)


if __name__ == "__main__":
    unittest.main()
