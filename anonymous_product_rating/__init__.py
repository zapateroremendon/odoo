# -*- coding: utf-8 -*-

from . import models
from . import controllers


def post_init_hook(env):
    """Post-installation hook to enable serialization recovery cron job"""
    try:
        cron_job = env.ref('anonymous_product_rating.cron_serialization_recovery', raise_if_not_found=False)
        if cron_job:
            cron_job.active = True
    except Exception as e:
        import logging
        _logger = logging.getLogger(__name__)
        _logger.warning(f"Post-install hook failed: {e}")