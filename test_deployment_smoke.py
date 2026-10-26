"""Offline smoke tests for the deployed application's basic configuration.

Run with: python -m unittest test_deployment_smoke.py -v
These tests do not imply that external odds or ESPN endpoints are healthy.
"""
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parent


class DeploymentSmokeTests(unittest.TestCase):
    def test_streamlit_entrypoint_exists(self):
        source = (ROOT / "app.py").read_text(encoding="utf-8")
        self.assertIn("st.set_page_config", source)
        self.assertIn('"NFL"', source)
        self.assertIn('"NCAAF"', source)

    def test_required_runtime_dependencies(self):
        requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
        for dependency in ("streamlit", "pandas", "numpy", "requests"):
            with self.subTest(dependency=dependency):
                self.assertIn(dependency, requirements)

    def test_no_false_claim_of_live_caliente_in_deploy_docs(self):
        instructions = (ROOT / "README_DEPLOY.md").read_text(encoding="utf-8").lower()
        self.assertIn("no existe aún una conexión continua a caliente", instructions)


if __name__ == "__main__":
    unittest.main()
