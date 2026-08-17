from django.test import SimpleTestCase
from drf_spectacular.generators import SchemaGenerator


class OpenApiSchemaTests(SimpleTestCase):
    def test_schema_contains_core_api_paths(self):
        schema = SchemaGenerator().get_schema(request=None, public=True)

        expected_paths = {
            '/api/v1/catalog/products/',
            '/api/v1/inventory/movements/history/',
            '/api/v1/sales/',
            '/api/v1/sales/{sale_id}/complete/',
            '/api/v1/sales/{sale_id}/cancel/',
            '/api/v1/dashboard/',
        }

        self.assertTrue(expected_paths.issubset(set(schema['paths'])))
