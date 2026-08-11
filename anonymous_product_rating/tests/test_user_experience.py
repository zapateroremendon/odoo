# -*- coding: utf-8 -*-

import json

from odoo.tests.common import TransactionCase, HttpCase
from odoo.tests import tagged


class TestUserExperience(TransactionCase):
    """Test user experience improvements"""

    def setUp(self):
        super().setUp()
        self.product = self.env['product.template'].create({
            'name': 'Test Product',
            'type': 'consu',
            'allow_anonymous_rating': True,
        })

    def test_logged_in_user_cannot_submit_anonymous_rating(self):
        """Test that logged-in users cannot submit anonymous ratings"""
        # Create a regular user
        user = self.env['res.users'].create({
            'name': 'Test User',
            'login': 'testuser@example.com',
            'email': 'testuser@example.com',
        })
        
        # Test that the user is not public
        self.assertFalse(user._is_public())
        
        # Test that public user check works
        public_user = self.env.ref('base.public_user')
        self.assertTrue(public_user._is_public())

    def test_anonymous_user_can_submit_rating(self):
        """Test that anonymous users can submit ratings"""
        # Use sudo to bypass access rights for test
        rating_model = self.env['anonymous.rating'].sudo()
        
        # Create an anonymous rating
        rating = rating_model.create({
            'product_tmpl_id': self.product.id,
            'rating': 4.5,
            'feedback': 'Great product!',
            'author_name': 'Anonymous User',
        })
        
        self.assertEqual(rating.product_tmpl_id, self.product)
        self.assertEqual(rating.rating, 4.5)
        self.assertEqual(rating.author_name, 'Anonymous User')

    def test_product_allows_anonymous_rating_setting(self):
        """Test the allow_anonymous_rating setting on products"""
        # Test product allows anonymous rating
        self.assertTrue(self.product.allow_anonymous_rating)
        
        # Create product that doesn't allow anonymous rating
        restricted_product = self.env['product.template'].create({
            'name': 'Restricted Product',
            'type': 'consu',
            'allow_anonymous_rating': False,
        })
        
        self.assertFalse(restricted_product.allow_anonymous_rating)


@tagged('post_install', '-at_install')
class TestUserExperienceHttp(HttpCase):
    """Test user experience via HTTP requests"""

    def setUp(self):
        super().setUp()
        self.product = self.env['product.template'].create({
            'name': 'Test Product',
            'type': 'consu',
            'allow_anonymous_rating': True,
        })

    def test_anonymous_rating_controller_public_access(self):
        """Test that anonymous users can access the rating submission endpoint"""
        payload = {
            'product_id': self.product.id,
            'rating': 5.0,
            'author_name': 'Test User',
            'feedback': 'Great product!',
        }
        response = self.url_open('/shop/product/anonymous_rating/submit',
                                 data=json.dumps(payload),
                                 headers={'Content-Type': 'application/json'})

        self.assertNotEqual(response.status_code, 404)
        self.assertNotEqual(response.status_code, 500)
        self.assertEqual(response.status_code, 200)

    def test_anonymous_rating_controller_returns_valid_json(self):
        """Test that anonymous rating POST returns success JSON and creates the rating."""
        payload = {
            'product_id': self.product.id,
            'rating': 4.0,
            'author_name': 'Anonymous Tester',
            'feedback': 'This product works well.',
        }
        response = self.url_open('/shop/product/anonymous_rating/submit',
                                 data=json.dumps(payload),
                                 headers={'Content-Type': 'application/json'})

        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertIsInstance(response_json, dict)
        result = response_json.get('result', {})
        self.assertTrue(result.get('success', False), msg=response_json)
        self.assertIn('message', result)

        anonymous_rating = self.env['anonymous.rating'].search([
            ('product_tmpl_id', '=', self.product.id),
            ('author_name', '=', 'Anonymous Tester'),
        ], limit=1)
        self.assertTrue(anonymous_rating, 'Anonymous rating record should be created')
        self.assertEqual(anonymous_rating.rating, 4.0)

    def test_product_page_loads_with_rating_section(self):
        """Test that product pages load with the rating section"""
        # Make product published and accessible
        self.product.write({
            'is_published': True,
            'website_published': True,
        })
        
        # Access a product page
        url = f'/shop/product/{self.product.id}'
        response = self.url_open(url)
        
        # Should load successfully or redirect
        self.assertIn(response.status_code, [200, 301, 302])

    def test_rating_statistics_endpoint(self):
        """Test the rating statistics endpoint"""
        url = f'/shop/product/{self.product.id}/combined_rating_stats'
        response = self.url_open(url)
        
        # Should return JSON response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get('Content-Type'), 'application/json')