"""
Embedded File Model
===========

Class for searchable Embedded File objects;
"""

from google.appengine.api import search
import string

import config
import util
import searchable_properties as sndb

from .content import Content


class FileEmbedded(Content):
    """Class for embedded files using TinyMCE, saved in datastore
    on successful file upload/attachment.
    """

    @classmethod
    def convert_uid(klass, short_or_long_uid):
        """Changes long-form uid's to short ones, and vice versa.

        Overrides method provided in Model.

        Long form example: FileEmbedded_Pb4g9gus
        Short form exmaple: Pb4g9gus
        """
        if '_' in short_or_long_uid:
            return ''.join([short_or_long_uid.split('_')[1]])
        else:
            return 'FileEmbedded_{}'.format(short_or_long_uid[:12]);

    @classmethod
    def get_long_uid(klass, short_or_long_uid):
        """Changes short of long-form uid's to long ones.

        Overrides method provided in Model.

        Long form example: FileEmbedded_Pb4g9gus
        Short form exmaple: Pb4g9gusoha4tp8a
        """
        if '.' in short_or_long_uid:  # is long
            return short_or_long_uid
        else:  # is short
            return 'FileEmbedded_{}'.format(short_or_long_uid[:8]);

    def add_file_data(self, file_dicts):
        """Save dictionaries of uploaded file meta data."""
        jp = self.json_properties

        if 'files' not in jp:
            jp['files'] = []
        jp['files'].extend(file_dicts)

        self.json_properties = jp

        self.has_files = len(jp['files']) > 0

    def remove_file_data(self, file_key):
        """Remove file dictionaries from existing json_properties"""
        jp = self.json_properties
        # Find and remove file from 'files' in json_properties
        if 'files' in jp:
            for index, file_dict in enumerate(jp['files']):
                if file_key == file_dict[u'gs_object_name']:
                    jp['files'].pop(index)

        self.json_properties = jp
        self.has_files = len(jp['files']) > 0