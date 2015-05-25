"""
Tests for bookmarks/models.py
"""

from opaque_keys.edx.keys import UsageKey

from bookmarks.models import Bookmark
from student.tests.factories import UserFactory

from xmodule.modulestore.exceptions import ItemNotFoundError
from xmodule.modulestore.tests.factories import CourseFactory, ItemFactory
from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase


class BookmarkModelsTest(ModuleStoreTestCase):
    """
    Test the Bookmark model.
    """
    def setUp(self):
        super(BookmarkModelsTest, self).setUp()

        self.user = UserFactory.create(password="test")

        self.course = CourseFactory.create(display_name='An Introduction to API Testing')
        self.course_id = unicode(self.course.id)

        self.chapter = ItemFactory.create(
            parent_location=self.course.location, category='chapter', display_name="Week 1"
        )
        self.sequential = ItemFactory.create(
            parent_location=self.chapter.location, category='sequential', display_name="Lesson 1"
        )
        self.vertical = ItemFactory.create(
            parent_location=self.sequential.location, category='vertical', display_name='Subsection 1'
        )
        self.vertical_2 = ItemFactory.create(
            parent_location=self.sequential.location, category='vertical', display_name='Subsection 2'
        )
        # This list shows the path, that we store in db.
        self.breadcrumb = [
            {"display_name": self.chapter.display_name, "usage_id": unicode(self.chapter.location)},
            {"display_name": self.sequential.display_name, "usage_id": unicode(self.sequential.location)}
        ]

    def get_bookmark_data(self, vertical):
        """
        Returns bookmark data for testing.
        """
        return {
            "usage_key": vertical.location,
            "course_key": self.course.id,
            "user": self.user
        }

    def assert_valid_bookmark(self, bookmark_object, bookmark_data, block=None):
        """
        Determines if the given data matches the specified bookmark.
        """
        self.assertEqual(bookmark_object.usage_key, bookmark_data['usage_key'])
        self.assertEqual(bookmark_object.course_key, bookmark_data['course_key'])
        self.assertIsNotNone(bookmark_object.created)
        self.assertEqual(bookmark_object.user, self.user)

        self.assertEqual(bookmark_object.path, self.breadcrumb)
        self.assertEqual(bookmark_object.display_name, block.display_name)

    def test_create_bookmark_successfully(self):
        """
        Tests creation of bookmark.
        """
        bookmark_data = self.get_bookmark_data(self.vertical)
        bookmark_object = Bookmark.create(bookmarks_data=bookmark_data)
        self.assertIsNotNone(bookmark_object)
        self.assert_valid_bookmark(bookmark_object, bookmark_data, block=self.vertical)

    def test_create_raises_exception_for_unreachable_block(self):
        """
        Tests creation of bookmark for unreachable block.
        """
        temp_data = self.get_bookmark_data(self.vertical)
        temp_data['usage_key'] = UsageKey.from_string('i4x://arbi/100/html/340ef1771a0940')
        with self.assertRaises(ItemNotFoundError):
            Bookmark.create(bookmarks_data=temp_data)

    def test_create_bookmark_with_given_block(self):
        """
        Tests creation of bookmark with block given.
        """
        bookmark_data = self.get_bookmark_data(self.vertical_2)
        bookmark_object = Bookmark.create(bookmarks_data=bookmark_data, block=self.vertical_2)
        self.assertIsNotNone(bookmark_object)
        self.assert_valid_bookmark(bookmark_object, bookmark_data, block=self.vertical_2)

    def test_get_path_with_given_vertical_block(self):
        """
        Tests creation of path with given block.
        """
        path_object = Bookmark.get_path(block=self.vertical)
        self.assertIsNotNone(path_object)
        self.assertEqual(len(path_object), 2)
        self.assertEqual(path_object[0], self.breadcrumb[0])
        self.assertEqual(path_object[1], self.breadcrumb[1])

    def test_get_path_with_given_chapter_block(self):
        """
        Tests creation of path with given chapter level block.
        """
        path_object = Bookmark.get_path(block=self.chapter)
        self.assertEqual(len(path_object), 0)

    def test_get_path_with_given_sequential_block(self):
        """
        Tests creation of path with given chapter level block.
        """
        path_object = Bookmark.get_path(block=self.sequential)
        self.assertEqual(len(path_object), 1)
        self.assertEqual(path_object[0], self.breadcrumb[0])

    def test_get_path_returns_empty_list_for_unreachable_parent(self):
        """
        Tests get_path returns empty list for unreachable parent.
        """
        path = Bookmark.get_path(block=self.course)
        self.assertEqual(path, [])
