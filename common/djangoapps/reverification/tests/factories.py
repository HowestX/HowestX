"""
verify_student factories
"""
from reverification.models import MidcourseReverificationWindow
from factory.django import DjangoModelFactory
import pytz
from datetime import timedelta, datetime
from opaque_keys.edx.locations import SlashSeparatedCourseKey
