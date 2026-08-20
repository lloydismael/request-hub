from django.db import connection
from django.test import TestCase


class RequestLifecycleDatabaseDefaultTests(TestCase):
    def test_request_lifecycle_columns_have_persistent_postgresql_defaults(self):
        if connection.vendor != "postgresql":
            self.skipTest("PostgreSQL schema assertion")

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    attribute.attname,
                    attribute.attnotnull,
                    pg_get_expr(default_value.adbin, default_value.adrelid)
                FROM pg_attribute AS attribute
                JOIN pg_class AS relation
                  ON relation.oid = attribute.attrelid
                JOIN pg_namespace AS namespace
                  ON namespace.oid = relation.relnamespace
                LEFT JOIN pg_attrdef AS default_value
                  ON default_value.adrelid = attribute.attrelid
                 AND default_value.adnum = attribute.attnum
                WHERE namespace.nspname = current_schema()
                  AND relation.relname = 'hub_request'
                  AND attribute.attname IN ('assignment_revision', 'lifecycle_stage')
                  AND NOT attribute.attisdropped
                """
            )
            columns = {
                name: {"not_null": not_null, "default": default}
                for name, not_null, default in cursor.fetchall()
            }

        self.assertEqual(set(columns), {"assignment_revision", "lifecycle_stage"})
        self.assertTrue(columns["assignment_revision"]["not_null"])
        self.assertEqual(columns["assignment_revision"]["default"], "0")
        self.assertTrue(columns["lifecycle_stage"]["not_null"])
        self.assertIn("'created'", columns["lifecycle_stage"]["default"] or "")
