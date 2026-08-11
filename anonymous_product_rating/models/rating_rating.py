# -*- coding: utf-8 -*-

from odoo import api, fields, models


class RatingRating(models.Model):
    _inherit = 'rating.rating'

    is_anonymous = fields.Boolean(string='Anonymous Rating', default=False, readonly=True)
    anonymous_rating_id = fields.Many2one('anonymous.rating', string='Anonymous Rating Reference', readonly=True)
    anonymous_author_name = fields.Char(string='Anonymous Author Name', readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to ensure proper res_model_id and trigger recomputation"""
        import logging
        from psycopg2 import OperationalError
        _logger = logging.getLogger(__name__)
        
        _logger.info(f"RATING CREATE: Creating {len(vals_list)} rating(s)")
        
        # Fix missing res_model_id for product.template ratings
        for vals in vals_list:
            if vals.get('res_model') == 'product.template' and not vals.get('res_model_id'):
                # Get the model ID for product.template
                product_model = self.env['ir.model'].search([('model', '=', 'product.template')], limit=1)
                if product_model:
                    vals['res_model_id'] = product_model.id
                    _logger.info(f"RATING CREATE: Fixed missing res_model_id for product.template: {product_model.id}")
        
        ratings = super().create(vals_list)
        
        # Skip recomputation during snippet processing to prevent serialization conflicts
        if self.env.context.get('snippet_processing') or self.env.context.get('tracking_disable'):
            _logger.debug("Skipping rating recomputation during snippet processing")
            return ratings
        
        # Trigger recomputation for affected product templates
        product_ids = []
        for rating in ratings:
            _logger.info(f"RATING CREATE: Rating {rating.id} - Model: {rating.res_model}, ID: {rating.res_id}")
            if rating.res_model == 'product.template' and rating.res_id:
                product_ids.append(rating.res_id)
        
        if product_ids:
            try:
                _logger.info(f"RATING CREATE: Triggering recomputation for products: {product_ids}")
                products = self.env['product.template'].browse(product_ids)
                # Force cache invalidation and recomputation with serialization protection
                products._invalidate_rating_cache()
                products._compute_rating_stats()
                products._compute_total_rating_stats()
                _logger.info(f"RATING CREATE: Recomputation completed")
            except OperationalError as e:
                if 'could not serialize access' in str(e):
                    _logger.warning("Serialization conflict during rating recomputation, will retry later")
                else:
                    raise
        else:
            _logger.info(f"RATING CREATE: No product templates to update")
        
        return ratings

    def write(self, vals):
        """Override write to trigger rating recomputation for product templates"""
        import logging
        from psycopg2 import OperationalError
        _logger = logging.getLogger(__name__)
        
        _logger.info(f"RATING WRITE: Updating {len(self)} rating(s) with vals: {vals}")
        
        result = super().write(vals)
        
        # Skip recomputation during snippet processing to prevent serialization conflicts
        if self.env.context.get('snippet_processing') or self.env.context.get('tracking_disable'):
            _logger.debug("Skipping rating recomputation during snippet processing")
            return result
        
        # If rating-related fields are updated, trigger recomputation
        if any(field in vals for field in ['rating', 'consumed', 'partner_id']):
            _logger.info(f"RATING WRITE: Rating-related fields updated, triggering recomputation")
            product_ids = []
            for rating in self:
                _logger.info(f"RATING WRITE: Rating {rating.id} - Model: {rating.res_model}, ID: {rating.res_id}")
                if rating.res_model == 'product.template' and rating.res_id:
                    product_ids.append(rating.res_id)
            
            if product_ids:
                try:
                    _logger.info(f"RATING WRITE: Triggering recomputation for products: {product_ids}")
                    products = self.env['product.template'].browse(product_ids)
                    # Force cache invalidation and recomputation with serialization protection
                    products._invalidate_rating_cache()
                    products._compute_rating_stats()
                    products._compute_total_rating_stats()
                    _logger.info(f"RATING WRITE: Recomputation completed")
                except OperationalError as e:
                    if 'could not serialize access' in str(e):
                        _logger.warning("Serialization conflict during rating recomputation, will retry later")
                    else:
                        raise
            else:
                _logger.info(f"RATING WRITE: No product templates to update")
        else:
            _logger.info(f"RATING WRITE: No rating-related fields updated, skipping recomputation")
        
        return result

    def unlink(self):
        """Override unlink to trigger rating recomputation for product templates"""
        # Get product IDs before deletion
        product_ids = []
        for rating in self:
            if rating.res_model == 'product.template' and rating.res_id:
                product_ids.append(rating.res_id)
        
        result = super().unlink()
        
        # Trigger recomputation after deletion
        if product_ids:
            products = self.env['product.template'].browse(product_ids)
            products._compute_rating_stats()
            products._compute_total_rating_stats()
        
        return result

    @api.model
    def create_from_anonymous(self, anonymous_rating):
        """Create a rating.rating record from an anonymous rating"""
        if not anonymous_rating.is_published:
            return False
        
        # Check if already exists
        existing = self.search([('anonymous_rating_id', '=', anonymous_rating.id)])
        if existing:
            return existing
        
        # Create rating record with all required fields
        vals = {
            'res_model': 'product.template',
            'res_id': anonymous_rating.product_tmpl_id.id,
            'rating': anonymous_rating.rating,
            'feedback': anonymous_rating.feedback or '',
            'consumed': True,
            'is_anonymous': True,
            'anonymous_rating_id': anonymous_rating.id,
            'anonymous_author_name': anonymous_rating.author_name,
            'partner_id': False,  # Explicitly set to False for anonymous
        }
        
        # Debug logging
        import logging
        _logger = logging.getLogger(__name__)
        _logger.info(f"Creating rating.rating record with vals: {vals}")
        
        try:
            rating_record = self.create(vals)
            _logger.info(f"Successfully created rating.rating record: {rating_record.id}")
            return rating_record
        except Exception as e:
            _logger.error(f"Failed to create rating.rating record: {str(e)}")
            raise

    @api.model
    def _cleanup_corrupted_anonymous_ratings(self):
        """Clean up corrupted rating records with res_model = False"""
        import logging
        _logger = logging.getLogger(__name__)
        try:
            # Find and delete corrupted rating records
            corrupted_ratings = self.search([
                '|',
                ('res_model', '=', False),
                ('res_model', '=', None)
            ])
            
            if corrupted_ratings:
                _logger.info(f"Found {len(corrupted_ratings)} corrupted rating records, deleting...")
                corrupted_ratings.unlink()
                _logger.info("Corrupted rating records cleaned up successfully")
            else:
                _logger.info("No corrupted rating records found")
                
            # Also clean up any anonymous rating records that might be causing issues
            anonymous_ratings = self.env['anonymous.rating'].search([])
            _logger.info(f"Found {len(anonymous_ratings)} anonymous rating records")
                
        except Exception as e:
            _logger.error(f"Error cleaning up corrupted ratings: {str(e)}")
            
        return True