
from flask import current_app

from alerta.exceptions import ApiError


class Page(object):

    def __init__(self, page=1, page_size=None, items=0):

        self.page = page
        self.page_size = page_size or current_app.config['DEFAULT_PAGE_SIZE']
        self.items = items

        if items and self.page > self.pages or self.page < 1:
            raise ApiError("page out of range: 1-%s" % self.pages, 416)

    @staticmethod
    def from_params(params, items):
        # page, page-size, limit (deprecated)
        page = params.get('page', 1, int)
        limit = params.get('limit', 0, int)
        page_size = params.get('page-size', limit, int)

        return Page(page, page_size, items)

    @property
    def pages(self):
        return ((self.items - 1) // self.page_size) + 1

    @property
    def has_more(self):
        return self.page < self.pages
