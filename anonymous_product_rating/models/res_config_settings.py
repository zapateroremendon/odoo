# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    anonymous_rating_auto_publish = fields.Boolean(
        string='Auto-publish Anonymous Ratings',
        config_parameter='anonymous_product_rating.auto_publish',
        help='Automatically publish anonymous ratings without moderation'
    )
    anonymous_rating_rate_limit_hours = fields.Integer(
        string='Rate Limit Period (hours)',
        config_parameter='anonymous_product_rating.rate_limit_hours',
        default=24,
        help='Time period for rate limiting (in hours)'
    )
    anonymous_rating_max_per_period = fields.Integer(
        string='Max Ratings per Period',
        config_parameter='anonymous_product_rating.max_ratings_per_period',
        default=3,
        help='Maximum number of ratings allowed per IP in the rate limit period'
    )
    anonymous_rating_recaptcha_min_score = fields.Float(
        string='reCAPTCHA Minimum Score',
        config_parameter='anonymous_product_rating.recaptcha_min_score',
        default=0.5,
        help='Minimum reCAPTCHA score required (0.0 to 1.0)'
    )
    anonymous_rating_enable_moderation = fields.Boolean(
        string='Enable Moderation',
        config_parameter='anonymous_product_rating.enable_moderation',
        help='Enable moderation for anonymous ratings'
    )