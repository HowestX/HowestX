"""
Model(s) for Bookmarks.
"""

from django.contrib.auth.models import User
from django.db import models

from jsonfield.fields import JSONField

from model_utils.models import TimeStampedModel
from xmodule.modulestore.django import modulestore
from xmodule_django.models import CourseKeyField, LocationKeyField


class Bookmark(TimeStampedModel):
    """
    Bookmarks model.
    """
    user = models.ForeignKey(User, db_index=True)
    course_key = CourseKeyField(max_length=255, db_index=True)
    usage_key = LocationKeyField(max_length=255, db_index=True)
    display_name = models.CharField(max_length=255, default="", help_text="Display name of XBlock")
    path = JSONField()  # "JSON, breadcrumbs to the XBlock"

    @classmethod
    def create(cls, bookmarks_data, block=None):
        """
        Create a bookmark object.
        """
        if not block:
            block = modulestore().get_item(bookmarks_data['usage_key'])

        bookmarks_data['display_name'] = block.display_name
        bookmarks_data['path'] = cls.get_path(block)

        bookmark, __ = cls.objects.get_or_create(**bookmarks_data)
        return bookmark

    @staticmethod
    def get_path(block):
        """
        Returns List of dicts containing {"usage_id": "", display_name:""} for the XBlocks
        from the top of the course tree till the parent of the bookmarked XBlock.
        """
        parent = block.get_parent()
        parents_data = []

        while parent is not None and parent.location.block_type not in ['course']:
            if parent.location.block_type not in ['vertical']:  # we already have info for vertical.
                parents_data.append({"display_name": parent.display_name, "usage_id": unicode(parent.location)})
            parent = parent.get_parent()
        parents_data.reverse()
        return parents_data
