# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


class TestAnonymousRating(TransactionCase):

    def setUp(self):
        super().setUp()
        self.product = self.env['product.template'].create({
            'name': 'Test Product',
            'type': 'consu',
            'allow_anonymous_rating': True,
        })

    def test_create_anonymous_rating(self):
        """Test creating an anonymous rating"""
        rating = self.env['anonymous.rating'].create({
            'product_tmpl_id': self.product.id,
            'rating': 4.5,
            'feedback': 'Great product!',
            'author_name': 'Test User',
            'author_email': 'test@example.com',
        })
        
        self.assertEqual(rating.product_tmpl_id, self.product)
        self.assertEqual(rating.rating, 4.5)
        self.assertEqual(rating.author_name, 'Test User')
        self.assertTrue(rating.rating_hash)
        self.assertGreaterEqual(rating.spam_score, 0.0)
        self.assertLessEqual(rating.spam_score, 1.0)

    def test_spam_score_calculation(self):
        """Test spam score calculation"""
        # Low spam score rating
        good_rating = self.env['anonymous.rating'].create({
            'product_tmpl_id': self.product.id,
            'rating': 5.0,
            'feedback': 'Excellent quality product, very satisfied!',
            'author_name': 'John Doe',
        })
        self.assertLess(good_rating.spam_score, 0.3)
        
        # High spam score rating
        spam_rating = self.env['anonymous.rating'].create({
            'product_tmpl_id': self.product.id,
            'rating': 5.0,
            'feedback': 'BUY NOW!!! CHEAP DISCOUNT SALE!!! Visit www.spam.com',
            'author_name': 'Spammer',
        })
        self.assertGreaterEqual(spam_rating.spam_score, 0.5)

    def test_email_validation(self):
        """Test email validation"""
        # Valid email
        rating = self.env['anonymous.rating'].create({
            'product_tmpl_id': self.product.id,
            'rating': 4.0,
            'author_name': 'Test User',
            'author_email': 'valid@example.com',
        })
        self.assertEqual(rating.author_email, 'valid@example.com')
        
        # Invalid email should raise ValidationError
        with self.assertRaises(ValidationError):
            self.env['anonymous.rating'].create({
                'product_tmpl_id': self.product.id,
                'rating': 4.0,
                'author_name': 'Test User',
                'author_email': 'invalid-email',
            })

    def test_bulk_operations(self):
        """Test bulk operations"""
        # Create multiple ratings
        ratings = self.env['anonymous.rating'].create([
            {
                'product_tmpl_id': self.product.id,
                'rating': 4.0,
                'author_name': f'User {i}',
                'feedback': f'Review {i}',
            } for i in range(5)
        ])
        
        self.assertEqual(len(ratings), 5)
        
        # Test bulk publish
        ratings.action_bulk_publish()
        self.assertTrue(all(r.is_published for r in ratings))
        self.assertTrue(all(r.is_moderated for r in ratings))

    def test_performance_methods(self):
        """Test performance-related methods"""
        # Test cleanup method
        old_count = self.env['anonymous.rating'].cleanup_old_ratings(days=0)
        self.assertGreaterEqual(old_count, 0)
        
        # Test auto-moderation
        moderated_count = self.env['anonymous.rating'].auto_moderate_by_spam_score(threshold=0.9)
        self.assertGreaterEqual(moderated_count, 0)
        
        # Test cache clearing
        result = self.env['anonymous.rating'].cron_clear_caches()
        self.assertTrue(result)

    def test_rating_statistics(self):
        """Test rating statistics calculation"""
        # Create some ratings
        self.env['anonymous.rating'].create([
            {
                'product_tmpl_id': self.product.id,
                'rating': 5.0,
                'author_name': 'User 1',
                'is_published': True,
            },
            {
                'product_tmpl_id': self.product.id,
                'rating': 4.0,
                'author_name': 'User 2',
                'is_published': True,
            },
        ])
        
        # Test statistics method
        stats = self.env['anonymous.rating'].get_rating_statistics([self.product.id])
        self.assertIn(self.product.id, stats)
        self.assertEqual(stats[self.product.id]['count'], 2)
        self.assertEqual(stats[self.product.id]['avg_rating'], 4.5)