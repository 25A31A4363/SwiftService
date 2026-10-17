import unittest
from fastapi.testclient import TestClient
from backend.app.main import app

class TestFrontendServing(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_root_serves_html(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Swift Service", resp.text)
        self.assertIn("id=\"app\"", resp.text)

    def test_static_css_served(self):
        resp = self.client.get("/static/css/variables.css")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("--font-family-sans", resp.text)
        self.assertIn("--p1-critical", resp.text)

    def test_static_js_served(self):
        resp = self.client.get("/static/js/app.js")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Swift Service", resp.text)

        resp2 = self.client.get("/static/js/hierarchy-views.js")
        self.assertEqual(resp2.status_code, 200)
        self.assertIn("renderOrgHierarchyView", resp2.text)
        self.assertIn("renderOperatingStatusBadge", resp2.text)
        self.assertIn("renderTraceVisualChain", resp2.text)

        resp3 = self.client.get("/static/js/feedback-view.js")
        self.assertEqual(resp3.status_code, 200)
        self.assertIn("renderFeedbackView", resp3.text)
        self.assertIn("openFeedbackLifecycleModal", resp3.text)
        self.assertIn("openBulkImportModal", resp3.text)

if __name__ == "__main__":
    unittest.main()
