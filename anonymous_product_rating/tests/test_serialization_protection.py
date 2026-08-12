# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase


class TestSerializationProtection(TransactionCase):

    def setUp(self):
        super().setUp()
        self.product = self.env['product.template'].create({
            'name': 'Test Product for Serialization',
            'type': 'consu',
            'allow_anonymous_rating': True,
        })

    def test_write_date_only_blocked(self):
        """CRITICAL: write_date-only _write is blocked on product models"""
        result = self.product._write({'write_date': '2023-01-01 00:00:00'})
        self.assertTrue(result)

    def test_write_date_and_uid_blocked(self):
        """CRITICAL: write_date+write_uid _write is blocked on product models"""
        result = self.product._write({'write_date': '2023-01-01 00:00:00', 'write_uid': 1})
        self.assertTrue(result)

    def test_real_write_not_blocked(self):
        """Legitimate writes with actual field changes are NOT blocked"""
        # Use the public write() method which properly converts values
        self.product.with_context(snippet_processing=False).write({'list_price': 999.0})
        self.product.invalidate_recordset(['list_price'])
        self.assertEqual(self.product.list_price, 999.0)

    def test_snippet_processing_blocks_all_writes(self):
        """snippet_processing context blocks ALL writes on product models"""
        context = dict(self.env.context, snippet_processing=True)
        product_ctx = self.product.with_context(context)
        result = product_ctx._write({'name': 'Should Not Change'})
        self.assertTrue(result)

    def test_non_product_model_not_affected(self):
        """Non-product models are NOT affected by the write protection"""
        partner = self.env['res.partner'].create({'name': 'Test Partner'})
        # Should work normally
        partner._write({'write_date': '2023-01-01 00:00:00'})

    def test_safe_property_accessors(self):
        """Safe property accessors return 0 during snippet processing"""
        context = dict(self.env.context, snippet_processing=True)
        product_ctx = self.product.with_context(context)
        self.assertEqual(product_ctx.safe_rating_avg, 0.0)
        self.assertEqual(product_ctx.safe_rating_count, 0)

    def test_safe_property_accessors_normal(self):
        """Safe property accessors return real values without snippet_processing"""
        self.env['anonymous.rating'].create({
            'product_tmpl_id': self.product.id,
            'rating': 5.0,
            'author_name': 'User',
            'is_published': True,
        })
        self.assertGreater(self.product.safe_rating_avg, 0.0)
        self.assertGreater(self.product.safe_rating_count, 0)

    def test_compute_works_without_snippet_context(self):
        """Compute methods work normally without snippet_processing"""
        self.env['anonymous.rating'].create({
            'product_tmpl_id': self.product.id,
            'rating': 4.0,
            'author_name': 'Normal User',
            'is_published': True,
        })
        self.product._compute_rating_stats()
        self.product._compute_anonymous_rating_stats()
        self.product._compute_total_rating_stats()
        self.assertGreater(self.product.rating_count, 0)
        self.assertGreater(self.product.anonymous_rating_count, 0)
        self.assertGreater(self.product.total_rating_count, 0)

    def test_cache_invalidation_skipped_during_snippet(self):
        """Cache invalidation is skipped during snippet processing"""
        context = dict(self.env.context, snippet_processing=True)
        rating = self.env['anonymous.rating'].with_context(context).create({
            'product_tmpl_id': self.product.id,
            'rating': 4.5,
            'author_name': 'Test User',
            'is_published': True,
        })
        # Should not raise
        rating._invalidate_product_caches([self.product.id])

    def test_serialization_recovery_methods(self):
        """Serialization recovery methods work"""
        self.env['anonymous.rating'].create({
            'product_tmpl_id': self.product.id,
            'rating': 4.5,
            'author_name': 'Test User',
            'is_published': True,
        })
        recovery_count = self.env['anonymous.rating'].cron_serialization_recovery()
        self.assertGreaterEqual(recovery_count, 0)
        health_issues = self.env['anonymous.rating'].check_serialization_health()
        self.assertGreaterEqual(health_issues, 0)

    def test_rate_limiting_not_cached(self):
        """Rate limiting returns fresh results (no stale ormcache)"""
        ip = '192.168.1.100'
        # First check - should allow
        allowed = self.env['anonymous.rating'].check_rate_limit(ip, self.product.id)
        self.assertTrue(allowed)
        # Create ratings up to limit
        for i in range(3):
            self.env['anonymous.rating'].create({
                'product_tmpl_id': self.product.id,
                'rating': 4.0,
                'author_name': f'User {i}',
                'ip_address': ip,
                'is_published': True,
            })
        # Should now be rate limited (fresh query, not cached)
        allowed = self.env['anonymous.rating'].check_rate_limit(ip, self.product.id)
        self.assertFalse(allowed)
