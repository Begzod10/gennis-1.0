from flask import current_app
import os
import logging

logger = logging.getLogger(__name__)


def get_media_path(*paths):
    """
    Get absolute path for media files using Flask app root
    Now this will work because ContextTask provides app context
    """
    try:
        base_dir = current_app.root_path
        media_path = os.path.join(base_dir, 'media', *paths)
        logger.info(f"Media path: {media_path}")
        return media_path
    except RuntimeError as e:
        logger.error(f"No Flask app context: {e}")
        # Fallback
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        media_path = os.path.join(base_dir, 'media', *paths)
        logger.warning(f"Using fallback path: {media_path}")
        return media_path
