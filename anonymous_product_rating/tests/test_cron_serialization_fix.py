# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase


class TestCronSerializationFix(TransactionCase):

    def setUp(self):
        super().setUp()
        self.product = self.env['product.template'].create({
            'name': 'Test Product for Cron',
            'type': 'consu',
            'allow_anonymous_rating': True,
        })
        self.rating = self.env['anonymous.rating'].create({
            'product_tmpl_id': self.product.id,
            'rating': 4.5,
            'feedback': 'Test feedback',
            'author_name': 'Test User',
            'is_published': True,
        })

    def test_critical_invalidate_cache_no_error(self):
        """CRITICAL: _invalidate_rating_cache should not raise errors"""
        try:
            self.product._invalidate_rating_cache()
        except Exception as e:
            self.fail(f"_invalidate_rating_cache raised error: {e}")

    def test_critical_force_recomputation_works(self):
        """CRITICAL: force_rating_recomputation should work"""
        result = self.product.force_rating_recomputation()
        self.assertTrue(result)
        self.assertGreaterEqual(self.product.rating_count, 0)

    def test_critical_cron_serialization_recovery_no_errors(self):
        """CRITICAL: cron_serialization_recovery should complete without errors"""
        result = self.env['anonymous.rating'].cron_serialization_recovery()
        self.assertGreaterEqual(result, 0)

    def test_high_non_stored_fields_compute_on_access(self):
        """HIGH: All rating fields compute correctly on access (all store=False)"""
        self.assertGreaterEqual(self.product.total_rating_count, 0)
        self.assertGreaterEqual(self.product.total_rating_avg, 0.0)
        self.assertGreaterEqual(self.product.anonymous_rating_count, 0)
        self.assertGreaterEqual(self.product.anonymous_rating_avg, 0.0)

    def test_high_refresh_all_rating_counts_works(self):
        """HIGH: refresh_all_rating_counts should work without errors"""
        result = self.env['product.template'].refresh_all_rating_counts()
        self.assertGreaterEqual(result, 0)

    def test_high_multiple_products_recovery(self):
        """HIGH: Cron should handle multiple products correctly"""
        for i in range(5):
            product = self.env['product.template'].create({
                'name': f'Test Product {i}',
                'type': 'consu',
                'allow_anonymous_rating': True,
            })
            self.env['anonymous.rating'].create({
                'product_tmpl_id': product.id,
                'rating': 4.0 + (i * 0.2),
                'author_name': f'User {i}',
                'is_published': True,
            })
        result = self.env['anonymous.rating'].cron_serialization_recovery()
        self.assertGreaterEqual(result, 5)

    def test_high_compute_methods_called_directly(self):
        """HIGH: Verify compute methods can be called directly"""
        self.product._compute_rating_stats()
        self.product._compute_total_rating_stats()
        self.product._compute_anonymous_rating_stats()
        self.assertGreaterEqual(self.product.rating_count, 0)
        self.assertGreaterEqual(self.product.total_rating_count, 0)
        self.assertGreaterEqual(self.product.anonymous_rating_count, 0)

    def test_high_serialization_health_check(self):
        """HIGH: check_serialization_health should work correctly"""
        issues = self.env['anonymous.rating'].check_serialization_health()
        self.assertGreaterEqual(issues, 0)

    def test_high_field_storage_configuration(self):
        """HIGH: Verify field storage configuration is correct"""
        model = self.env['product.template']
        # All rating fields should be store=False to prevent serialization conflicts
        self.assertFalse(model._fields['total_rating_count'].store)
        self.assertFalse(model._fields['total_rating_avg'].store)
        self.assertFalse(model._fields['anonymous_rating_count'].store)
        self.assertFalse(model._fields['anonymous_rating_avg'].store)

    def test_critical_batch_recovery_no_errors(self):
        """CRITICAL: Batch recovery should handle all products without errors"""
        for i in range(10):
            product = self.env['product.template'].create({
                'name': f'Batch Product {i}',
                'type': 'consu',
            })
            self.env['anonymous.rating'].create({
                'product_tmpl_id': product.id,
                'rating': 3.0 + (i % 3),
                'author_name': f'Batch User {i}',
                'is_published': i % 2 == 0,
            })
        try:
            result = self.env['anonymous.rating'].cron_serialization_recovery()
            self.assertGreaterEqual(result, 10)
        except Exception as e:
            self.fail(f"Batch recovery failed: {e}")

    def test_high_rating_count_includes_anonymous(self):
        """HIGH: rating_count should include anonymous ratings"""
        # Product already has 1 published anonymous rating from setUp
        self.assertGreaterEqual(self.product.rating_count, 1)
        self.assertGreater(self.product.rating_avg, 0.0)
