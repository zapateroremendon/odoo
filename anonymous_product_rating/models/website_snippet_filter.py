# -*- coding: utf-8 -*-

import logging
from odoo import models, api

_logger = logging.getLogger(__name__)


class BaseModel(models.AbstractModel):
    _inherit = 'base'

    def _write(self, vals):
        """Prevention of serialization conflicts during snippet processing"""
        # Protect product models from serialization conflicts
        if self._name in ('product.template', 'product.product'):
            # Check both context and thread-local flag for snippet processing
            import threading
            thread_processing = getattr(threading.current_thread(), 'snippet_processing', False)
            context_processing = self.env.context.get('snippet_processing')
            
            # Check if this is just a write_date/write_uid update (primary cause of serialization conflicts)
            if vals and set(vals.keys()) <= {'write_date', 'write_uid'}:
                _logger.warning(f"[ANONYMOUS_RATING] Preventing serialization conflict: skipping write_date update on {len(self)} {self._name} records")
                return True
            
            # Skip all write operations during snippet processing to prevent conflicts
            if context_processing or thread_processing:
                _logger.warning(f"[ANONYMOUS_RATING] Preventing serialization conflict: skipping write operation on {len(self)} {self._name} records during snippet processing")
                return True
        
        return super()._write(vals)


class WebsiteSnippetFilter(models.Model):
    _inherit = 'website.snippet.filter'

    @api.model
    def _filter_records_to_values(self, records, is_sample=False):
        """Override to prevent rating computations during snippet processing"""
        if is_sample:
            return super()._filter_records_to_values(records, is_sample)
            
        # Set snippet processing context
        context = dict(self.env.context, snippet_processing=True)
        self = self.with_context(context)
        
        # Apply context to records
        if hasattr(records, 'with_context'):
            records = records.with_context(context)
        
        try:
            return super()._filter_records_to_values(records, is_sample)
        except (ValueError, TypeError) as e:
            _logger.error(f"Data validation error in snippet filter: {e}")
            return []
        except Exception as e:
            if 'could not serialize access' in str(e):
                _logger.warning(f"Serialization error in snippet filter, returning empty result: {e}")
                return []
            else:
                _logger.error(f"Unexpected error in snippet filter: {e}")
                raise


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def _get_combination_info_variant(self, **kwargs):
        """Override to prevent rating updates during snippet processing"""
        try:
            if self.env.context.get('snippet_processing'):
                # Use minimal context to prevent rating computations
                minimal_context = dict(self.env.context, tracking_disable=True)
                return super(ProductTemplate, self.with_context(minimal_context))._get_combination_info_variant(**kwargs)
            
            return super()._get_combination_info_variant(**kwargs)
        except Exception as e:
            _logger.error(f"Error in _get_combination_info_variant: {e}")
            raise