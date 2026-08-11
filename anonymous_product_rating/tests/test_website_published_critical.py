# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase


class TestWebsitePublishedCritical(TransactionCase):
    """Critical test cases for Solution 1: website_published field"""

    def setUp(self):
        super().setUp()
        self.product = self.env['product.template'].create({
            'name': 'Critical Test Product',
            'type': 'consu',
            'allow_anonymous_rating': True,
            'is_published': True,
        })

    def test_critical_no_attribute_error_on_access(self):
        """CRITICAL: Verify no AttributeError when accessing website_published"""
        rating = self.env['anonymous.rating'].create({
            'product_tmpl_id': self.product.id,
            'rating': 5.0,
            'author_name': 'Critical Test User',
            'is_published': True,
        })
        
        # This was the original error - should NOT raise AttributeError
        try:
            _ = rating.website_published
            _ = rating.is_published and rating.website_published
        except AttributeError as e:
            self.fail(f"AttributeError raised: {e}. Solution 1 failed!")

    def test_critical_lambda_filter_with_both_fields(self):
        """CRITICAL: Test lambda filtering with both is_published and website_published"""
        # Create multiple ratings
        ratings = self.env['anonymous.rating'].create([
            {
                'product_tmpl_id': self.product.id,
                'rating': 5.0,
                'author_name': f'User {i}',
                'is_published': i % 2 == 0,
            } for i in range(10)
        ])
        
        # This is the exact pattern used in seo_google_data
        try:
            filtered = ratings.filtered(
                lambda r: r.is_published and r.website_published
            )
            # Should have 5 published ratings (0, 2, 4, 6, 8)
            self.assertEqual(len(filtered), 5)
        except AttributeError as e:
            self.fail(f"Lambda filter failed with AttributeError: {e}")

    def test_critical_field_in_fields_registry(self):
        """CRITICAL: Verify field is in _fields registry (used by defensive code)"""
        model = self.env['anonymous.rating']
        
        # This check is used in Solution 3
        has_field = 'website_published' in model._fields
        
        self.assertTrue(has_field, 
            "website_published not in _fields - Solution 3 defensive check will fail!")

    def test_critical_sync_on_publish_action(self):
        """CRITICAL: Verify website_published syncs when using action_publish"""
        rating = self.env['anonymous.rating'].create({
            'product_tmpl_id': self.product.id,
            'rating': 4.5,
            'author_name': 'Test User',
            'is_published': False,
        })
        
        # Initially both False
        self.assertFalse(rating.is_published)
        self.assertFalse(rating.website_published)
        
        # Publish using action
        rating.action_publish()
        
        # Both should be True
        self.assertTrue(rating.is_published)
        self.assertTrue(rating.website_published)

    def test_critical_bulk_operations_sync(self):
        """CRITICAL: Verify website_published syncs in bulk operations"""
        ratings = self.env['anonymous.rating'].create([
            {
                'product_tmpl_id': self.product.id,
                'rating': 5.0,
                'author_name': f'User {i}',
                'is_published': False,
            } for i in range(5)
        ])
        
        # Bulk publish
        ratings.action_bulk_publish()
        
        # All should have both fields True
        for rating in ratings:
            self.assertTrue(rating.is_published)
            self.assertTrue(rating.website_published)

    def test_critical_domain_search_with_website_published(self):
        """CRITICAL: Verify domain search works with website_published"""
        # Create published and unpublished ratings for THIS product only
        published_rating = self.env['anonymous.rating'].create({
            'product_tmpl_id': self.product.id,
            'rating': 5.0,
            'author_name': 'Published User',
            'is_published': True,
        })
        
        unpublished_rating = self.env['anonymous.rating'].create({
            'product_tmpl_id': self.product.id,
            'rating': 3.0,
            'author_name': 'Unpublished User',
            'is_published': False,
        })
        
        # Search using website_published in domain for THIS product
        try:
            published = self.env['anonymous.rating'].search([
                ('product_tmpl_id', '=', self.product.id),
                ('website_published', '=', True)
            ])
            self.assertEqual(len(published), 1)
            self.assertEqual(published.id, published_rating.id)
            
            unpublished = self.env['anonymous.rating'].search([
                ('product_tmpl_id', '=', self.product.id),
                ('website_published', '=', False)
            ])
            self.assertEqual(len(unpublished), 1)
            self.assertEqual(unpublished.id, unpublished_rating.id)
        except Exception as e:
            self.fail(f"Domain search with website_published failed: {e}")

    def test_critical_write_updates_both_fields(self):
        """CRITICAL: Verify write() updates both fields correctly"""
        rating = self.env['anonymous.rating'].create({
            'product_tmpl_id': self.product.id,
            'rating': 4.0,
            'author_name': 'Test User',
            'is_published': False,
        })
        
        # Write to is_published
        rating.write({'is_published': True})
        
        # website_published should sync
        self.assertTrue(rating.website_published)
        
        # Write to is_published again
        rating.write({'is_published': False})
        
        # website_published should sync back
        self.assertFalse(rating.website_published)
