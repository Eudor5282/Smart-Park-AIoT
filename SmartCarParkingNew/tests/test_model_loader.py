import importlib.util
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(__file__))
MODEL_PATH = os.path.join(ROOT, "Model", "keras_model.h5")
SERVER_PATH = os.path.join(ROOT, "cam_ai_server.py")


class ModelLoaderTests(unittest.TestCase):
    def test_loader_can_load_teachable_machine_model(self):
        spec = importlib.util.spec_from_file_location("cam_ai_server", SERVER_PATH)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        model = module._load_model_with_compat(MODEL_PATH)

        self.assertIsNotNone(model)
        self.assertTrue(hasattr(model, "predict"))


if __name__ == "__main__":
    unittest.main()
