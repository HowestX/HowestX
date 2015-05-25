"""
HTTP end-points for the Bookmarks API.

For more information, see:
https://openedx.atlassian.net/wiki/display/TNL/Bookmarks+API
"""
import logging

from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.utils.translation import ugettext as _

from rest_framework import status
from rest_framework import permissions
from rest_framework.authentication import OAuth2Authentication, SessionAuthentication
from rest_framework.generics import ListCreateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import CourseKey, UsageKey

from openedx.core.lib.api.serializers import PaginationSerializer
from openedx.core.lib.api.permissions import IsUserInUrl

from xmodule.modulestore.exceptions import ItemNotFoundError
from xmodule.modulestore.django import modulestore

from bookmarks import DEFAULT_FIELDS, OPTIONAL_FIELDS
from .api import get_bookmark
from .models import Bookmark
from .serializers import BookmarkSerializer

log = logging.getLogger(__name__)


class BookmarksViewMixin(object):
    """
    Shared code for bookmarks views.
    """

    def parse_optional_field_params(self, request):
        """
        Parse and returns the fields list.
        """
        optional_fields_param = request.QUERY_PARAMS.get('fields', [])
        optional_fields = optional_fields_param.split(',') if optional_fields_param else []
        return DEFAULT_FIELDS + [field for field in optional_fields if field in OPTIONAL_FIELDS]


class BookmarksView(ListCreateAPIView, BookmarksViewMixin):
    """
    **Use Case**

        Get a paginated list of bookmarks, across all the courses, ordered by creation time.
        You can also filter the bookmarks by course_id.

        Each page in the list can contain up to 30 bookmarks by default.

        Create/Post a new bookmark for particular Xblock.

    **Example Requests**

          GET /api/bookmarks/v1/bookmarks/?course_id={course_id1}&fields=display_name,path

          POST /api/bookmarks/v1/bookmarks/
          Request data: {"usage_id": "i4x://RiceX/BIOC300.1x/openassessment/cf4c1de230af407fa214905b90aace57"}

    **Response Values**

        * count: The number of bookmarks in a course.

        * next: The URI to the next page of bookmarks.

        * previous: The URI to the previous page of bookmarks.

        * num_pages: The number of pages listing bookmarks.

        * results:  A list of bookmarks returned. Each collection in the list
          contains these fields.

            * id: String. The identifier string for the bookmark: {user_id},{usage_id}.

            * course_id: String. The identifier string of the bookmark's course.

            * usage_id: String. The identifier string of the bookmark's XBlock.

            * display_name: (optional) String. Display name of the XBlock.

            * path: (optional) List. List of dicts containing {"usage_id": "", display_name:""} for the XBlocks
                from the top of the course tree till the parent of the bookmarked XBlock.

            * created: ISO 8601 String. The timestamp of bookmark's creation.

    """
    authentication_classes = (OAuth2Authentication, SessionAuthentication)
    permission_classes = (permissions.IsAuthenticated,)

    paginate_by = 30
    max_paginate_by = 500
    paginate_by_param = 'page_size'
    pagination_serializer_class = PaginationSerializer
    serializer_class = BookmarkSerializer

    def get_serializer_context(self):
        """
        Return the context for the serializer.
        """
        context = super(BookmarksView, self).get_serializer_context()
        if self.request.method == 'POST':
            return context
        context['fields'] = self.parse_optional_field_params(self.request)
        return context

    def get_queryset(self):
        course_id = self.request.QUERY_PARAMS.get('course_id', None)

        bookmarks_queryset = Bookmark.objects.filter(user=self.request.user)

        if not course_id:
            return bookmarks_queryset.order_by('-created')
        try:
            course_key = CourseKey.from_string(course_id)
        except InvalidKeyError:
            log.error("Invalid course id '{course_id}'")
            return []

        return bookmarks_queryset.filter(course_key=course_key).order_by('-created')

    def post(self, request):
        """
        POST /api/bookmarks/v1/bookmarks/
        Request data: {"usage_id": "i4x://RiceX/BIOC300.1x/openassessment/cf4c1de230af407fa214905b90aace57"}
        """
        if not request.DATA:
            return Response(
                {
                    "developer_message": u"request data is missing",
                    "user_message": _(u"request data is missing")
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        usage_id = request.DATA.get('usage_id', None)
        if not usage_id:
            return Response(
                {
                    "developer_message": u"'usage_id' key is missing",
                    "user_message": _(u"'usage_id' key is missing")
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            usage_key = UsageKey.from_string(usage_id)
            # course_key may have an empty run property.
            usage_key = usage_key.replace(course_key=modulestore().fill_in_run(usage_key.course_key))
            course_key = usage_key.course_key

        except InvalidKeyError as exception:
            log.error(exception.message)
            return Response(
                {
                    "developer_message": exception.message,
                    "user_message": _(u"Invalid usage id: '{usage_id}'").format(usage_id=usage_id)
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        bookmarks_data = {
            "usage_key": usage_key,
            "course_key": course_key,
            "user": request.user
        }

        try:
            bookmark = Bookmark.create(bookmarks_data)
        except ItemNotFoundError as exception:
            log.error(exception.message)
            return Response(
                {
                    "developer_message": u"Block with usage_id not found.",
                    "user_message": _(u"Invalid usage id: '{usage_id}'").format(usage_id=usage_id)
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response(
            BookmarkSerializer(bookmark, context={"fields": DEFAULT_FIELDS + OPTIONAL_FIELDS}).data,
            status=status.HTTP_201_CREATED
        )


class BookmarksDetailView(APIView, BookmarksViewMixin):
    """
    **Use Cases**

        Get or Delete a specific bookmark.

    **Example Requests**:

        GET /api/bookmarks/v1/bookmarks/{username},{usage_id}/?fields=display_name,path

        DELETE /api/bookmarks/v1/bookmarks/{username},{usage_id}/

    **Response for GET**
        Users can only get their own bookmarks

        * id: String. The identifier string for the bookmark: {user_id},{usage_id}.

        * course_id: String. The identifier string of the bookmark's course.

        * usage_id: String. The identifier string of the bookmark's XBlock.

        * display_name: (optional) String. Display name of the XBlock.

        * path: (optional) List of dicts containing {"usage_id": "", display_name:""} for the XBlocks
            from the top of the course tree till the parent of the bookmarked XBlock.

        * created: ISO 8601 String. The timestamp of bookmark's creation.

    **Response for DELETE**
        Users can only delete their own bookmarks

        A successful delete returns a 204 and no content.

        Users can only delete their own bookmarks. If the requesting user
        does not have username "username", this method will return with a
        status of 404, Thee same is true in case if a bookmark does not exist.

    """
    authentication_classes = (OAuth2Authentication, SessionAuthentication)
    permission_classes = (permissions.IsAuthenticated, IsUserInUrl)

    serializer_class = BookmarkSerializer

    # pylint: disable=unused-argument
    def get(self, request, username=None, usage_id=None):
        """
        GET /api/bookmarks/v1/bookmarks/{username},{usage_id}?fields=display_name,path
        """
        try:
            usage_key = UsageKey.from_string(usage_id)
        except InvalidKeyError as exception:
            log.error(exception.message)
            return Response(
                {
                    "developer_message": exception.message,
                    "user_message": _(u"Invalid usage id: '{usage_id}'").format(usage_id=usage_id)
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            bookmark_data = get_bookmark(
                request.user,
                usage_key,
                fields=self.parse_optional_field_params(self.request),
                serialized=True
            )
        except (ObjectDoesNotExist, MultipleObjectsReturned) as exception:
            log.error(exception.message)
            return Response(
                {
                    "developer_message": exception.message,
                    "user_message": _(u"The bookmark does not exist.")
                },
                status=status.HTTP_404_NOT_FOUND
            )

        return Response(bookmark_data)

    # pylint: disable=unused-argument
    def delete(self, request, username=None, usage_id=None):
        """
        DELETE /api/bookmarks/v1/bookmarks/{username},{usage_id}
        """
        try:
            usage_key = UsageKey.from_string(usage_id)
        except InvalidKeyError as exception:
            log.error(exception.message)
            return Response(
                {
                    "developer_message": exception.message,
                    "user_message": _(u"Invalid usage id: '{usage_id}'").format(usage_id=usage_id)
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            bookmark = get_bookmark(request.user, usage_key)
        except (ObjectDoesNotExist, MultipleObjectsReturned) as exception:
            log.error(exception.message)
            return Response(
                {
                    "developer_message": exception.message,
                    "user_message": _(u"The bookmark does not exist.")
                },
                status=status.HTTP_404_NOT_FOUND
            )

        bookmark.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)
