"""
Implement CourseTab
"""

from abc import ABCMeta
import logging

from xblock.fields import List
from openedx.core.lib.plugins.api import PluginError

# We should only scrape strings for i18n in this file, since the target language is known only when
# they are rendered in the template.  So ugettext gets called in the template.
_ = lambda text: text

log = logging.getLogger("edx.courseware")


class CourseTab(object):
    """
    The Course Tab class is a data abstraction for all tabs (i.e., course navigation links) within a course.
    It is an abstract class - to be inherited by various tab types.
    Derived classes are expected to override methods as needed.
    When a new tab class is created, it should define the type and add it in this class' factory method.
    """
    __metaclass__ = ABCMeta

    # Class property that specifies the type of the tab.  It is generally a constant value for a
    # subclass, shared by all instances of the subclass.
    type = ''

    # Class property that specifies whether the tab can be hidden for a particular course
    is_hideable = False

    # Class property that specifies whether the tab can be moved within a course's list of tabs
    is_movable = True

    # Class property that specifies whether the tab is a collection of other tabs
    is_collection = False

    def __init__(self, name, tab_id, link_func):
        """
        Initializes class members with values passed in by subclasses.

        Args:
            name: The name of the tab

            tab_id: Intended to be a unique id for this tab, although it is currently not enforced
            within this module.  It is used by the UI to determine which page is active.

            link_func: A function that computes the link for the tab,
            given the course and a reverse-url function as input parameters
        """

        self.name = name

        self.tab_id = tab_id

        self.link_func = link_func

    def is_enabled(self, course, settings, user=None):  # pylint: disable=unused-argument
        """
        Determines whether the tab is enabled for the given course and a particular user.
        This method is to be overridden by subclasses when applicable.  The base class
        implementation always returns True.

        Args:
            course: An xModule CourseDescriptor

            settings: The configuration settings, including values for:
             WIKI_ENABLED
             FEATURES['ENABLE_DISCUSSION_SERVICE']
             FEATURES['ENABLE_EDXNOTES']
             FEATURES['ENABLE_STUDENT_NOTES']
             FEATURES['ENABLE_TEXTBOOK']

            user: An optional user for whom the tab will be displayed. If none,
                then the code should assume a staff user or an author.

        Returns:
            A boolean value to indicate whether this instance of the tab is enabled.
        """
        return True

    def get(self, key, default=None):
        """
        Akin to the get method on Python dictionary objects, gracefully returns the value associated with the
        given key, or the default if key does not exist.
        """
        try:
            return self[key]
        except KeyError:
            return default

    def __getitem__(self, key):
        """
        This method allows callers to access CourseTab members with the d[key] syntax as is done with
        Python dictionary objects.
        """
        if key == 'name':
            return self.name
        elif key == 'type':
            return self.type
        elif key == 'tab_id':
            return self.tab_id
        else:
            raise KeyError('Key {0} not present in tab {1}'.format(key, self.to_json()))

    def __setitem__(self, key, value):
        """
        This method allows callers to change CourseTab members with the d[key]=value syntax as is done with
        Python dictionary objects.  For example: course_tab['name'] = new_name

        Note: the 'type' member can be 'get', but not 'set'.
        """
        if key == 'name':
            self.name = value
        elif key == 'tab_id':
            self.tab_id = value
        else:
            raise KeyError('Key {0} cannot be set in tab {1}'.format(key, self.to_json()))

    def __eq__(self, other):
        """
        Overrides the equal operator to check equality of member variables rather than the object's address.
        Also allows comparison with dict-type tabs (needed to support callers implemented before this class
        was implemented).
        """

        if isinstance(other, dict) and not self.validate(other, raise_error=False):
            # 'other' is a dict-type tab and did not validate
            return False

        # allow tabs without names; if a name is required, its presence was checked in the validator.
        name_is_eq = (other.get('name') is None or self.name == other['name'])

        # only compare the persisted/serialized members: 'type' and 'name'
        return self.type == other.get('type') and name_is_eq

    def __ne__(self, other):
        """
        Overrides the not equal operator as a partner to the equal operator.
        """
        return not (self == other)

    @classmethod
    def validate(cls, tab_dict, raise_error=True):
        """
        Validates the given dict-type tab object to ensure it contains the expected keys.
        This method should be overridden by subclasses that require certain keys to be persisted in the tab.
        """
        return key_checker(['type'])(tab_dict, raise_error)

    def to_json(self):
        """
        Serializes the necessary members of the CourseTab object to a json-serializable representation.
        This method is overridden by subclasses that have more members to serialize.

        Returns:
            a dictionary with keys for the properties of the CourseTab object.
        """
        return {'type': self.type, 'name': self.name}

    @staticmethod
    def from_json(tab_dict):
        """
        Deserializes a CourseTab from a json-like representation.

        The subclass that is instantiated is determined by the value of the 'type' key in the
        given dict-type tab. The given dict-type tab is validated before instantiating the CourseTab object.

        If the tab_type is not recognized, then an exception is logged and None is returned.
        The intention is that the user should still be able to use the course even if a
        particular tab is not found for some reason.

        Args:
            tab: a dictionary with keys for the properties of the tab.

        Raises:
            InvalidTabsException if the given tab doesn't have the right keys.
        """
        # TODO: don't import openedx capabilities from common
        from openedx.core.djangoapps.course_views.course_views import CourseViewType, CourseViewTypeManager
        tab_type_name = tab_dict.get('type')
        try:
            tab_type = CourseViewTypeManager.get_plugin(tab_type_name)
        except PluginError:
            log.exception("Unknown tab type {tab_type_name}. Known types: {tab_types}".format(
                tab_type_name=tab_type_name,
                tab_types=CourseViewTypeManager.get_course_view_types())
            )
            return None
        tab_type.validate(tab_dict)
        if issubclass(tab_type, CourseViewType):
            return CourseViewTab(tab_type, tab_dict=tab_dict)
        else:
            return tab_type(tab_dict=tab_dict)


class CourseViewTab(CourseTab):
    """
    A tab that renders a course view.
    """

    def __init__(self, course_view_type, tab_dict=None):
        super(CourseViewTab, self).__init__(
            name=tab_dict.get('name', course_view_type.title) if tab_dict else course_view_type.title,
            tab_id=course_view_type.name,
            link_func=link_reverse_func(course_view_type.view_name),
        )
        self.type = course_view_type.name
        self.course_view_type = course_view_type
        self.is_hideable = course_view_type.is_hideable
        self.is_hidden = tab_dict.get('is_hidden', False) if tab_dict else False
        self.is_collection = course_view_type.is_collection if hasattr(course_view_type, 'is_collection') else False

    def is_enabled(self, course, settings, user=None):
        if not super(CourseViewTab, self).is_enabled(course, settings, user=user):
            return False
        return self.course_view_type.is_enabled(course, settings, user=user)

    def __getitem__(self, key):
        if key == 'is_hidden':
            return self.is_hidden
        else:
            return super(CourseViewTab, self).__getitem__(key)

    def __setitem__(self, key, value):
        if key == 'is_hidden':
            self.is_hidden = value
        else:
            super(CourseViewTab, self).__setitem__(key, value)

    def to_json(self):
        to_json_val = super(CourseViewTab, self).to_json()
        if self.is_hidden:
            to_json_val.update({'is_hidden': True})
        return to_json_val

    def items(self, course):
        """ If this tab is a collection, this will fetch the items in the collection. """
        for item in self.course_view_type.items(course):
            yield item


class CourseTabList(List):
    """
    An XBlock field class that encapsulates a collection of Tabs in a course.
    It is automatically created and can be retrieved through a CourseDescriptor object: course.tabs
    """

    @staticmethod
    def initialize_default(course):
        """
        An explicit initialize method is used to set the default values, rather than implementing an
        __init__ method.  This is because the default values are dependent on other information from
        within the course.
        """

        course.tabs.extend([
            CourseTab.from_json({'type': 'courseware', 'name': _('Courseware')}),
            CourseTab.from_json({'type': 'course_info', 'name': _('Course Info')})
        ])

        # Presence of syllabus tab is indicated by a course attribute
        if hasattr(course, 'syllabus_present') and course.syllabus_present:
            course.tabs.append(CourseTab.from_json({'type': 'syllabus', 'name': _('Syllabus')}))

        # If the course has a discussion link specified, use that even if we feature
        # flag discussions off. Disabling that is mostly a server safety feature
        # at this point, and we don't need to worry about external sites.
        if course.discussion_link:
            discussion_tab = CourseTab.from_json(
                {'type': 'external_discussion', 'name': _('External Discussion'), 'link': course.discussion_link}
            )
        else:
            discussion_tab = CourseTab.from_json({'type': 'discussion', 'name': _('Discussion')})

        course.tabs.extend([
            CourseTab.from_json({'type': 'textbooks', 'name': _('Textbooks')}),
            discussion_tab,
            CourseTab.from_json({'type': 'wiki', 'name': _('Wiki')}),
            CourseTab.from_json({'type': 'progress', 'name': _('Progress')}),
        ])

    @staticmethod
    def get_discussion(course):
        """
        Returns the discussion tab for the given course.  It can be either of type DiscussionTab
        or ExternalDiscussionTab.  The returned tab object is self-aware of the 'link' that it corresponds to.
        """

        # the discussion_link setting overrides everything else, even if there is a discussion tab in the course tabs
        if course.discussion_link:
            return CourseTab.from_json(
                {'type': 'external_discussion', 'name': _('External Discussion'), 'link': course.discussion_link}
            )

        # find one of the discussion tab types in the course tabs
        for tab in course.tabs:
            if tab.type == 'discussion' or tab.type == 'external_discussion':
                return tab
        return None

    @staticmethod
    def get_tab_by_slug(tab_list, url_slug):
        """
        Look for a tab with the specified 'url_slug'.  Returns the tab or None if not found.
        """
        return next((tab for tab in tab_list if tab.get('url_slug') == url_slug), None)

    @staticmethod
    def get_tab_by_type(tab_list, tab_type):
        """
        Look for a tab with the specified type.  Returns the first matching tab.
        """
        return next((tab for tab in tab_list if tab.type == tab_type), None)

    @staticmethod
    def get_tab_by_id(tab_list, tab_id):
        """
        Look for a tab with the specified tab_id.  Returns the first matching tab.
        """
        return next((tab for tab in tab_list if tab.tab_id == tab_id), None)

    @staticmethod
    def iterate_displayable(course, settings, user=None, inline_collections=True):
        """
        Generator method for iterating through all tabs that can be displayed for the given course and
        the given user with the provided access settings.
        """
        for tab in course.tabs:
            if tab.is_enabled(course, settings, user=user) and (not user or not tab.is_hideable or not tab.is_hidden):
                if tab.is_collection:
                    # If rendering inline that add each item in the collection,
                    # else just show the tab itself as long as it is not empty.
                    if inline_collections:
                        for item in tab.items(course):
                            yield item
                    elif len(list(tab.items(course))) > 0:
                        yield tab
                else:
                    yield tab

    @classmethod
    def validate_tabs(cls, tabs):
        """
        Check that the tabs set for the specified course is valid.  If it
        isn't, raise InvalidTabsException with the complaint.

        Specific rules checked:
        - if no tabs specified, that's fine
        - if tabs specified, first two must have type 'courseware' and 'course_info', in that order.

        """
        if tabs is None or len(tabs) == 0:
            return

        if len(tabs) < 2:
            raise InvalidTabsException("Expected at least two tabs.  tabs: '{0}'".format(tabs))

        if tabs[0].get('type') != 'courseware':
            raise InvalidTabsException(
                "Expected first tab to have type 'courseware'.  tabs: '{0}'".format(tabs))

        if tabs[1].get('type') != 'course_info':
            raise InvalidTabsException(
                "Expected second tab to have type 'course_info'.  tabs: '{0}'".format(tabs))

        # the following tabs should appear only once
        for tab_type in ['courseware', 'course_info', 'notes', 'textbooks', 'pdf_textbooks', 'html_textbooks']:
            cls._validate_num_tabs_of_type(tabs, tab_type, 1)

    @staticmethod
    def _validate_num_tabs_of_type(tabs, tab_type, max_num):
        """
        Check that the number of times that the given 'tab_type' appears in 'tabs' is less than or equal to 'max_num'.
        """
        count = sum(1 for tab in tabs if tab.get('type') == tab_type)
        if count > max_num:
            msg = (
                "Tab of type '{type}' appears {count} time(s). "
                "Expected maximum of {max} time(s)."
            ).format(
                type=tab_type, count=count, max=max_num,
            )
            raise InvalidTabsException(msg)

    def to_json(self, values):
        """
        Overrides the to_json method to serialize all the CourseTab objects to a json-serializable representation.
        """
        json_data = []
        if values:
            for val in values:
                if isinstance(val, CourseTab):
                    json_data.append(val.to_json())
                elif isinstance(val, dict):
                    json_data.append(val)
                else:
                    continue
        return json_data

    def from_json(self, values):
        """
        Overrides the from_json method to de-serialize the CourseTab objects from a json-like representation.
        """
        self.validate_tabs(values)
        tabs = []
        for tab_dict in values:
            tab = CourseTab.from_json(tab_dict)
            if tab:
                tabs.append(tab)
        return tabs


# Validators
#  A validator takes a dict and raises InvalidTabsException if required fields are missing or otherwise wrong.
# (e.g. "is there a 'name' field?).  Validators can assume that the type field is valid.
def key_checker(expected_keys):
    """
    Returns a function that checks that specified keys are present in a dict.
    """

    def check(actual_dict, raise_error=True):
        """
        Function that checks whether all keys in the expected_keys object is in the given actual_dict object.
        """
        missing = set(expected_keys) - set(actual_dict.keys())
        if not missing:
            return True
        if raise_error:
            raise InvalidTabsException(
                "Expected keys '{0}' are not present in the given dict: {1}".format(expected_keys, actual_dict)
            )
        else:
            return False

    return check


def need_name(dictionary, raise_error=True):
    """
    Returns whether the 'name' key exists in the given dictionary.
    """
    return key_checker(['name'])(dictionary, raise_error)


# Link Functions
def link_reverse_func(reverse_name):
    """
    Returns a function that takes in a course and reverse_url_func,
    and calls the reverse_url_func with the given reverse_name and course' ID.
    """
    return lambda course, reverse_url_func: reverse_url_func(reverse_name, args=[course.id.to_deprecated_string()])


def link_value_func(value):
    """
    Returns a function takes in a course and reverse_url_func, and returns the given value.
    """
    return lambda course, reverse_url_func: value


class InvalidTabsException(Exception):
    """
    A complaint about invalid tabs.
    """
    pass


class UnequalTabsException(Exception):
    """
    A complaint about tab lists being unequal
    """
    pass
