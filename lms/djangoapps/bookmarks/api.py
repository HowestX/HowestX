"""
Bookmarks api methods.
"""

from bookmarks.serializers import BookmarkSerializer
from bookmarks.models import Bookmark


def get_bookmark(user, usage_key, fields=None, serialized=False):
    """
    Return bookmark model or data.

    Args:
        user (User): The user requesting the bookmark.
        usage_key (UsageKey): The usage id of an Xblock.
        fields (list): (optional) List of fields to return for a bookmark.
        serialized (Bool): (optional) Returns JSON serialized version of bookmark if its True
            otherwise it returns bookmark object (default is False).

    Returns:
         A JSON serialized dict or object containing bookmark data.

    Raises:
         ObjectDoesNotExit: If Bookmark object does not exist.
    """
    bookmark = Bookmark.objects.get(usage_key=usage_key, user=user)

    return BookmarkSerializer(bookmark, context={"fields": fields}).data if serialized else bookmark
