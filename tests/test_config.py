import os
import tempfile
import unittest
from pathlib import Path

from src.config import load_env_file, load_project_env


class ConfigTests(unittest.TestCase):
    def test_load_env_file_sets_values_from_dotenv(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / ".env"
            env_path.write_text(
                "DEEPSEEK_API_KEY=sk-test\nDEEPSEEK_MODEL=deepseek-v4-flash\n",
                encoding="utf-8",
            )
            old_key = os.environ.pop("DEEPSEEK_API_KEY", None)
            old_model = os.environ.pop("DEEPSEEK_MODEL", None)
            try:
                load_env_file(env_path)

                self.assertEqual(os.environ["DEEPSEEK_API_KEY"], "sk-test")
                self.assertEqual(os.environ["DEEPSEEK_MODEL"], "deepseek-v4-flash")
            finally:
                os.environ.pop("DEEPSEEK_API_KEY", None)
                os.environ.pop("DEEPSEEK_MODEL", None)
                if old_key is not None:
                    os.environ["DEEPSEEK_API_KEY"] = old_key
                if old_model is not None:
                    os.environ["DEEPSEEK_MODEL"] = old_model

    def test_load_env_file_does_not_override_existing_environment(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / ".env"
            env_path.write_text("DEEPSEEK_API_KEY=from-file\n", encoding="utf-8")
            old_key = os.environ.get("DEEPSEEK_API_KEY")
            os.environ["DEEPSEEK_API_KEY"] = "from-shell"
            try:
                load_env_file(env_path)

                self.assertEqual(os.environ["DEEPSEEK_API_KEY"], "from-shell")
            finally:
                if old_key is None:
                    os.environ.pop("DEEPSEEK_API_KEY", None)
                else:
                    os.environ["DEEPSEEK_API_KEY"] = old_key

    def test_load_project_env_reads_env_local_after_env(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / ".env").write_text("DEEPSEEK_MODEL=from-env\n", encoding="utf-8")
            (root / ".env.local").write_text("DEEPSEEK_MODEL=from-local\n", encoding="utf-8")
            old_model = os.environ.pop("DEEPSEEK_MODEL", None)
            try:
                load_project_env(root)

                self.assertEqual(os.environ["DEEPSEEK_MODEL"], "from-local")
            finally:
                os.environ.pop("DEEPSEEK_MODEL", None)
                if old_model is not None:
                    os.environ["DEEPSEEK_MODEL"] = old_model

    def test_load_project_env_keeps_shell_values_above_env_local(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / ".env.local").write_text("DEEPSEEK_API_KEY=from-local\n", encoding="utf-8")
            old_key = os.environ.get("DEEPSEEK_API_KEY")
            os.environ["DEEPSEEK_API_KEY"] = "from-shell"
            try:
                load_project_env(root)

                self.assertEqual(os.environ["DEEPSEEK_API_KEY"], "from-shell")
            finally:
                if old_key is None:
                    os.environ.pop("DEEPSEEK_API_KEY", None)
                else:
                    os.environ["DEEPSEEK_API_KEY"] = old_key


if __name__ == "__main__":
    unittest.main()
