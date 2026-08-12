# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)


class AnonymousRatingPerformanceMonitor(models.TransientModel):
    _name = 'anonymous.rating.performance.monitor'
    _description = 'Anonymous Rating Performance Monitor'

    # Statistics fields
    total_ratings = fields.Integer(string='Total Ratings', readonly=True)
    published_ratings = fields.Integer(string='Published Ratings', readonly=True)
    pending_moderation = fields.Integer(string='Pending Moderation', readonly=True)
    spam_ratings = fields.Integer(string='High Spam Score Ratings', readonly=True)
    
    # Performance metrics
    avg_response_time = fields.Float(string='Average Response Time (ms)', readonly=True)
    cache_hit_ratio = fields.Float(string='Cache Hit Ratio (%)', readonly=True)
    db_query_count = fields.Integer(string='Database Queries (last hour)', readonly=True)
    
    # Maintenance options
    cleanup_days = fields.Integer(string='Cleanup Old Ratings (days)', default=365)
    spam_threshold = fields.Float(string='Auto-moderate Spam Threshold', default=0.7)
    
    @api.model
    def default_get(self, fields_list):
        """Load current statistics"""
        res = super().default_get(fields_list)
        
        # Get rating statistics
        AnonymousRating = self.env['anonymous.rating']
        res.update({
            'total_ratings': AnonymousRating.search_count([]),
            'published_ratings': AnonymousRating.search_count([('is_published', '=', True)]),
            'pending_moderation': AnonymousRating.search_count([
                ('is_moderated', '=', False),
                ('is_published', '=', False)
            ]),
            'spam_ratings': AnonymousRating.search_count([('spam_score', '>=', 0.7)]),
        })
        
        return res

    def action_cleanup_old_ratings(self):
        """Clean up old unpublished ratings"""
        if self.cleanup_days <= 0:
            raise UserError(_('Cleanup days must be greater than 0'))
        
        AnonymousRating = self.env['anonymous.rating']
        cleaned_count = AnonymousRating.cleanup_old_ratings(self.cleanup_days)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Cleanup Complete'),
                'message': _('Cleaned up %d old ratings') % cleaned_count,
                'type': 'success',
            }
        }

    def action_auto_moderate_spam(self):
        """Auto-moderate ratings with high spam scores"""
        if not (0 <= self.spam_threshold <= 1):
            raise UserError(_('Spam threshold must be between 0 and 1'))
        
        AnonymousRating = self.env['anonymous.rating']
        moderated_count = AnonymousRating.auto_moderate_by_spam_score(self.spam_threshold)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Auto-moderation Complete'),
                'message': _('Auto-moderated %d spam ratings') % moderated_count,
                'type': 'success',
            }
        }

    def action_clear_caches(self):
        """Clear all rating-related caches"""
        self.env.registry.clear_cache()
        
        # Also invalidate product rating fields
        products = self.env['product.template'].search([])
        products.invalidate_recordset(['anonymous_rating_count', 'anonymous_rating_avg', 
                                     'total_rating_count', 'total_rating_avg'])
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Cache Cleared'),
                'message': _('All rating caches have been cleared'),
                'type': 'success',
            }
        }

    def action_recompute_statistics(self):
        """Recompute all rating statistics"""
        # Force recomputation of all product rating statistics
        products = self.env['product.template'].search([])
        products._compute_anonymous_rating_stats()
        products._compute_total_rating_stats()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Statistics Recomputed'),
                'message': _('All rating statistics have been recomputed'),
                'type': 'success',
            }
        }

    def action_generate_performance_report(self):
        """Generate a detailed performance report"""
        report_data = self._generate_performance_data()
        
        # Create a temporary report record
        report = self.env['anonymous.rating.performance.report'].create(report_data)
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Performance Report'),
            'res_model': 'anonymous.rating.performance.report',
            'res_id': report.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def _generate_performance_data(self):
        """Generate performance analysis data"""
        AnonymousRating = self.env['anonymous.rating']
        
        # Database performance metrics
        self.env.cr.execute("""
            SELECT 
                COUNT(*) as total_ratings,
                COUNT(CASE WHEN is_published THEN 1 END) as published_ratings,
                COUNT(CASE WHEN spam_score >= 0.7 THEN 1 END) as high_spam_ratings,
                AVG(spam_score) as avg_spam_score,
                COUNT(CASE WHEN create_date >= %s THEN 1 END) as recent_ratings
            FROM anonymous_rating
        """, (datetime.now() - timedelta(days=7),))
        
        stats = self.env.cr.dictfetchone()
        
        # Top products by rating count
        self.env.cr.execute("""
            SELECT 
                pt.name as product_name,
                COUNT(ar.id) as rating_count,
                AVG(ar.rating) as avg_rating
            FROM anonymous_rating ar
            JOIN product_template pt ON ar.product_tmpl_id = pt.id
            WHERE ar.is_published = true
            GROUP BY pt.id, pt.name
            ORDER BY rating_count DESC
            LIMIT 10
        """)
        
        top_products = self.env.cr.dictfetchall()
        
        return {
            'total_ratings': stats['total_ratings'],
            'published_ratings': stats['published_ratings'],
            'high_spam_ratings': stats['high_spam_ratings'],
            'avg_spam_score': stats['avg_spam_score'] or 0.0,
            'recent_ratings': stats['recent_ratings'],
            'top_products_data': str(top_products),  # Store as text for simplicity
            'report_date': fields.Datetime.now(),
        }


class AnonymousRatingPerformanceReport(models.TransientModel):
    _name = 'anonymous.rating.performance.report'
    _description = 'Anonymous Rating Performance Report'

    report_date = fields.Datetime(string='Report Date', readonly=True)
    total_ratings = fields.Integer(string='Total Ratings', readonly=True)
    published_ratings = fields.Integer(string='Published Ratings', readonly=True)
    high_spam_ratings = fields.Integer(string='High Spam Score Ratings', readonly=True)
    avg_spam_score = fields.Float(string='Average Spam Score', readonly=True)
    recent_ratings = fields.Integer(string='Recent Ratings (7 days)', readonly=True)
    top_products_data = fields.Text(string='Top Products Data', readonly=True)
    
    # Computed fields for better display
    publication_rate = fields.Float(string='Publication Rate (%)', compute='_compute_rates', readonly=True)
    spam_rate = fields.Float(string='Spam Rate (%)', compute='_compute_rates', readonly=True)
    
    @api.depends('total_ratings', 'published_ratings', 'high_spam_ratings')
    def _compute_rates(self):
        for record in self:
            if record.total_ratings > 0:
                record.publication_rate = (record.published_ratings / record.total_ratings) * 100
                record.spam_rate = (record.high_spam_ratings / record.total_ratings) * 100
            else:
                record.publication_rate = 0.0
                record.spam_rate = 0.0