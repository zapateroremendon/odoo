# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.tools import ormcache


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    anonymous_rating_ids = fields.One2many(
        'anonymous.rating', 'product_tmpl_id', 
        string='Anonymous Ratings',
        domain=[('is_published', '=', True)]
    )
    anonymous_rating_count = fields.Integer(
        string='Anonymous Rating Count',
        compute='_compute_anonymous_rating_stats',
        compute_sudo=True,
        store=False
    )
    anonymous_rating_avg = fields.Float(
        string='Anonymous Rating Average',
        compute='_compute_anonymous_rating_stats',
        compute_sudo=True,
        store=False
    )
    total_rating_count = fields.Integer(
        string='Total Rating Count',
        compute='_compute_total_rating_stats',
        compute_sudo=True,
        store=False  # Don't store to avoid conflicts
    )
    total_rating_avg = fields.Float(
        string='Total Rating Average',
        compute='_compute_total_rating_stats',
        compute_sudo=True,
        store=False  # Don't store to avoid conflicts
    )
    allow_anonymous_rating = fields.Boolean(
        string='Allow Anonymous Rating',
        default=True,
        help='Allow anonymous users to rate this product'
    )

    @api.depends('anonymous_rating_ids.rating', 'anonymous_rating_ids.is_published')
    def _compute_anonymous_rating_stats(self):
        for product in self:
            published_ratings = product.anonymous_rating_ids.filtered('is_published')
            if published_ratings:
                product.anonymous_rating_count = len(published_ratings)
                product.anonymous_rating_avg = sum(published_ratings.mapped('rating')) / len(published_ratings)
            else:
                product.anonymous_rating_count = 0
                product.anonymous_rating_avg = 0.0

    @api.depends('rating_ids', 'anonymous_rating_ids.rating', 'anonymous_rating_ids.is_published')
    def _compute_total_rating_stats(self):
        for product in self:
            regular_ratings = product.rating_ids.filtered(lambda r: r.rating >= 1 and r.consumed and r.partner_id)
            regular_count = len(regular_ratings)
            regular_avg = sum(regular_ratings.mapped('rating')) / regular_count if regular_count > 0 else 0.0

            anonymous_ratings = product.anonymous_rating_ids.filtered('is_published')
            anonymous_count = len(anonymous_ratings)
            anonymous_avg = sum(anonymous_ratings.mapped('rating')) / anonymous_count if anonymous_count > 0 else 0.0

            total_count = regular_count + anonymous_count
            if total_count > 0:
                total_avg = ((regular_count * regular_avg) + (anonymous_count * anonymous_avg)) / total_count
                product.total_rating_count = total_count
                product.total_rating_avg = round(total_avg, 2)
            else:
                product.total_rating_count = 0
                product.total_rating_avg = 0.0

    # Override rating fields to show COMBINED totals (logged + anonymous) for website display
    @api.depends('rating_ids', 'rating_ids.rating', 'rating_ids.consumed', 'rating_ids.partner_id', 
                 'anonymous_rating_ids', 'anonymous_rating_ids.rating', 'anonymous_rating_ids.is_published')
    def _compute_rating_stats(self):
        """Override parent _compute_rating_stats to show combined totals"""
        for product in self:
            logged_ratings = product.rating_ids.filtered(lambda r: r.rating >= 1 and r.consumed and r.partner_id)
            logged_count = len(logged_ratings)

            anonymous_ratings = product.anonymous_rating_ids.filtered('is_published')
            anonymous_count = len(anonymous_ratings)

            total_count = logged_count + anonymous_count

            if total_count > 0:
                logged_total = sum(r.rating for r in logged_ratings)
                anonymous_total = sum(r.rating for r in anonymous_ratings)
                combined_avg = (logged_total + anonymous_total) / total_count

                product.rating_count = total_count
                product.rating_avg = combined_avg
            else:
                product.rating_count = 0
                product.rating_avg = 0.0
    
    def _invalidate_rating_cache(self):
        """Invalidate rating-related recordset cache"""
        self.invalidate_recordset(['rating_count', 'rating_avg',
                                   'anonymous_rating_count', 'anonymous_rating_avg',
                                   'total_rating_count', 'total_rating_avg'])





    def _create_rating_from_anonymous(self, anonymous_rating):
        """Create a rating.rating record from an anonymous rating"""
        try:
            # Create a rating.rating record to integrate with Odoo's core system
            rating_vals = {
                'res_model': 'product.template',
                'res_id': self.id,
                'res_model_id': self.env['ir.model']._get('product.template').id,
                'rating': anonymous_rating.rating,
                'feedback': anonymous_rating.feedback,
                'consumed': True,
                'partner_id': False,  # Anonymous user has no partner
                'create_date': anonymous_rating.create_date,
                'write_date': anonymous_rating.write_date,
            }
            
            # Create the rating record
            rating_record = self.env['rating.rating'].sudo().create(rating_vals)
            
            # Note: Anonymous rating is now integrated via computed fields instead of direct linking
            
            return rating_record
        except Exception as e:
            import logging
            _logger = logging.getLogger(__name__)
            _logger.error(f"Error creating rating from anonymous rating {anonymous_rating.id}: {e}")
            return False

    def sync_anonymous_ratings_to_core(self):
        """Sync anonymous ratings to core rating system - disabled to prevent double counting"""
        # Note: Syncing is disabled to prevent double counting in rating statistics
        # Anonymous ratings are now counted separately and combined in _compute_total_rating_stats
        pass

    @ormcache('self.id')
    def get_combined_rating_count(self):
        """Get combined rating count - cached for performance"""
        try:
            return self.total_rating_count or 0
        except Exception:
            return 0

    @ormcache('self.id')
    def get_combined_rating_avg(self):
        """Get combined rating average - cached for performance"""
        try:
            return self.total_rating_avg or 0.0
        except Exception:
            return 0.0



    def get_combined_rating_stats(self):
        """Get combined rating statistics including anonymous ratings"""
        try:
            product_sudo = self.sudo()
            
            # Get regular ratings (from rating.rating model)
            regular_ratings = product_sudo.rating_ids.filtered(lambda r: r.rating >= 1 and r.consumed)
            regular_count = len(regular_ratings)
            regular_avg = sum(regular_ratings.mapped('rating')) / regular_count if regular_count > 0 else 0.0
            
            # Get anonymous ratings
            anonymous_ratings = product_sudo.anonymous_rating_ids.filtered('is_published')
            anonymous_count = len(anonymous_ratings)
            anonymous_avg = sum(anonymous_ratings.mapped('rating')) / anonymous_count if anonymous_count > 0 else 0.0
            
            # Calculate combined values
            total_count = regular_count + anonymous_count
            if total_count > 0:
                # Weighted average calculation
                combined_avg = ((regular_count * regular_avg) + (anonymous_count * anonymous_avg)) / total_count
                return {
                    'count': total_count,
                    'avg': combined_avg,
                    'regular_count': regular_count,
                    'regular_avg': regular_avg,
                    'anonymous_count': anonymous_count,
                    'anonymous_avg': anonymous_avg
                }
            else:
                return {
                    'count': 0,
                    'avg': 0.0,
                    'regular_count': 0,
                    'regular_avg': 0.0,
                    'anonymous_count': 0,
                    'anonymous_avg': 0.0
                }
                
        except Exception as e:
            # Log error but don't break the computation
            import logging
            _logger = logging.getLogger(__name__)
            _logger.warning(f"Error computing combined rating stats for product {self.id}: {e}")
            return {
                'count': 0,
                'avg': 0.0,
                'regular_count': 0,
                'regular_avg': 0.0,
                'anonymous_count': 0,
                'anonymous_avg': 0.0
            }

    def get_safe_rating_avg(self):
        """Safe method to get rating average for templates"""
        try:
            # During snippet processing, return safe default
            if self.env.context.get('snippet_processing') or self.env.context.get('tracking_disable'):
                return 0.0
            # Force recomputation to ensure we have the latest values
            self._compute_total_rating_stats()
            return self.sudo().total_rating_avg or 0.0
        except:
            return 0.0
    
    def get_safe_rating_count(self):
        """Safe method to get rating count for templates"""
        try:
            # During snippet processing, return safe default
            if self.env.context.get('snippet_processing') or self.env.context.get('tracking_disable'):
                return 0
            # Force recomputation to ensure fresh values
            self._compute_rating_stats()
            return self.sudo().rating_count or 0
        except:
            return 0

    @property
    def safe_rating_avg(self):
        """Property to safely access rating_avg during snippet processing"""
        try:
            if self.env.context.get('snippet_processing') or self.env.context.get('tracking_disable'):
                return 0.0
            return self.rating_avg or 0.0
        except:
            return 0.0

    @property  
    def safe_rating_count(self):
        """Property to safely access rating_count during snippet processing"""
        try:
            if self.env.context.get('snippet_processing') or self.env.context.get('tracking_disable'):
                return 0
            return self.rating_count or 0
        except:
            return 0
    
    @api.model
    def refresh_all_rating_counts(self):
        """Refresh rating counts for all products - can be called by cron"""
        try:
            products = self.search([('rating_ids', '!=', False)])
            for product in products:
                product.force_rating_recomputation()
            return len(products)
        except Exception as e:
            import logging
            _logger = logging.getLogger(__name__)
            _logger.error(f"Error in refresh_all_rating_counts: {e}")
            return 0
    
    def force_rating_recomputation(self):
        """Force recomputation of all rating fields - can be called from website"""
        try:
            # Directly call compute methods instead of invalidating cache
            # This is more reliable and avoids issues with non-stored fields
            self._compute_rating_stats()
            self._compute_total_rating_stats()
            return True
        except Exception as e:
            import logging
            _logger = logging.getLogger(__name__)
            _logger.error(f"Error in force_rating_recomputation: {e}")
            return False
    
    @api.model
    def _rating_apply_get_default_subtype_id(self):
        """Override to trigger recomputation after rating application"""
        result = super()._rating_apply_get_default_subtype_id()
        # Force recomputation after rating is applied
        self.force_rating_recomputation()
        return result