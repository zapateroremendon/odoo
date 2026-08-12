# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase


class TestWebsitePublishedField(TransactionCase):
    """Test Solution 1: website_published field compatibility"""

    def setUp(self):
        super().setUp()
        self.product = self.env['product.template'].create({
            'name': 'Test Product for website_published',
            'type': 'consu',
            'allow_anonymous_rating': True,
        })

    def test_website_published_field_exists(self):
        """Test that website_published field exists on anonymous.rating model"""
        rating = self.env['anonymous.rating'].create({
            'product_tmpl_id': self.product.id,
            'rating': 4.5,
            'feedback': 'Test feedback',
            'author_name': 'Test User',
        })
        
        # Field should exist
        self.assertTrue(hasattr(rating, 'website_published'))
        
    def test_website_published_syncs_with_is_published(self):
        """Test that website_published syncs with is_published"""
        rating = self.env['anonymous.rating'].create({
            'product_tmpl_id': self.product.id,
            'rating': 5.0,
            'author_name': 'Test User',
            'is_published': False,
        })
        
        # Initially both should be False
        self.assertFalse(rating.is_published)
        self.assertFalse(rating.website_published)
        
        # Change is_published to True
        rating.write({'is_published': True})
        
        # website_published should sync automatically
        self.assertTrue(rating.is_published)
        self.assertTrue(rating.website_published)
        
        # Change is_published to False
        rating.write({'is_published': False})
        
        # website_published should sync back
        self.assertFalse(rating.is_published)
        self.assertFalse(rating.website_published)

    def test_website_published_field_in_fields_registry(self):
        """Test that website_published is in model's field registry"""
        model = self.env['anonymous.rating']
        
        # Check field is in _fields
        self.assertIn('website_published', model._fields)
        
    def test_website_published_filtering(self):
        """Test filtering by website_published works correctly"""
        # Create published rating
        published = self.env['anonymous.rating'].create({
            'product_tmpl_id': self.product.id,
            'rating': 5.0,
            'author_name': 'Published User',
            'is_published': True,
        })
        
        # Create unpublished rating
        unpublished = self.env['anonymous.rating'].create({
            'product_tmpl_id': self.product.id,
            'rating': 3.0,
            'author_name': 'Unpublished User',
            'is_published': False,
        })
        
        # Filter by website_published
        published_ratings = self.env['anonymous.rating'].search([
            ('website_published', '=', True)
        ])
        
        # Should include published rating
        self.assertIn(published, published_ratings)
        self.assertNotIn(unpublished, published_ratings)
        
    def test_website_published_with_lambda_filter(self):
        """Test that lambda filtering with website_published works"""
        # Create ratings
        self.env['anonymous.rating'].create([
            {
                'product_tmpl_id': self.product.id,
                'rating': 5.0,
                'author_name': f'User {i}',
                'is_published': i % 2 == 0,  # Even numbers published
            } for i in range(5)
        ])
        
        # Get all ratings for product
        all_ratings = self.env['anonymous.rating'].search([
            ('product_tmpl_id', '=', self.product.id)
        ])
        
        # Filter using lambda with website_published
        published_ratings = all_ratings.filtered(
            lambda r: r.is_published and r.website_published
        )
        
        # Should have 3 published (0, 2, 4)
        self.assertEqual(len(published_ratings), 3)
        
        # All should be published
        for rating in published_ratings:
            self.assertTrue(rating.is_published)
            self.assertTrue(rating.website_published)
