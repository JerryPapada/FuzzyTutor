from rest_framework import status
from rest_framework.test import APITestCase


class DocumentationEndpointTests(APITestCase):
    def test_openapi_schema_endpoint_is_available(self):
        response = self.client.get("/api/schema/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("openapi", response.data)
        self.assertIn("paths", response.data)
        self.assertIn("/api/fuzzy/evaluate/", response.data["paths"])
        self.assertIn("/api/learning/submissions/", response.data["paths"])

    def test_swagger_ui_endpoint_is_available(self):
        response = self.client.get("/api/docs/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
