"""
Theme Model
===========

Course content themes
"""

import config
import util
import searchable_properties as sndb

from .contentOld import Content


class Theme(Content):

    topics = sndb.StringProperty(repeated=True)  # ordered children
    color = sndb.StringProperty(default='#666666')
    estimated_duration = sndb.IntegerProperty(default=0)
    lesson_count = sndb.IntegerProperty(default=0)
    target_audience = sndb.StringProperty(default=None)
    popular_lessons = sndb.StringProperty(repeated=True)  # ordered children
    locale = sndb.StringProperty(default='en')

    def associate_topics(self, topics):
        """Takes a list of topic objects and adds them to the course
        as an array of children 'course.topics_list' if they are a child

        Creates an empty array if none are children of this course
        """
        self.topics_list = []
        for topic_uid in self.topics:
            for topic in topics:
                # Breaks after match to prevent repeats
                if topic.uid == topic_uid:
                    self.topics_list.append(topic)
                    break
