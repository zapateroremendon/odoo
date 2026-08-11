# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request


class RatingController(http.Controller):

    @http.route('/shop/product/<int:product_id>/refresh_ratings', type='json', auth='public', methods=['POST'])
    def refresh_product_ratings(self, product_id):
        """Force refresh of product rating counts"""
        try:
            product = request.env['product.template'].sudo().browse(product_id)
            if product.exists():
                success = product.force_rating_recomputation()
                if success:
                    return {
                        'success': True,
                        'rating_count': product.rating_count,
                        'rating_avg': product.rating_avg,
                        'total_rating_count': product.total_rating_count,
                        'total_rating_avg': product.total_rating_avg,
                    }
            return {'success': False, 'error': 'Product not found or recomputation failed'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @http.route('/shop/product/<int:product_id>/combined_rating_stats', type='json', auth='public', methods=['GET', 'POST'])
    def get_combined_rating_stats(self, product_id):
        """Get combined rating statistics (logged + anonymous)"""
        try:
            product = request.env['product.template'].sudo().browse(product_id)
            if not product.exists():
                return {'success': False, 'error': 'Product not found'}
            
            # Force fresh computation to ensure latest values
            product.force_rating_recomputation()
            
            # Get the actual current values
            rating_count = product.rating_count
            rating_avg = product.rating_avg
            
            return {
                'success': True,
                'count': rating_count,
                'avg': rating_avg,
                'rating_count': rating_count,  # For compatibility
                'rating_avg': rating_avg,      # For compatibility
                'total_rating_count': product.total_rating_count,
                'total_rating_avg': product.total_rating_avg,
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}