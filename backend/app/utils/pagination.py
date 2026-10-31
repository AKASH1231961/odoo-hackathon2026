from fastapi import Query, Response

MAX_PAGE_SIZE = 200


class Page:
    def __init__(self, response: Response, skip: int, limit: int):
        self.response = response
        self.skip = skip
        self.limit = limit

    def apply(self, query, order_by):
        """Return one page; the full count goes in the X-Total-Count header."""
        self.response.headers["X-Total-Count"] = str(query.order_by(None).count())
        return query.order_by(order_by).offset(self.skip).limit(self.limit).all()


def paged(default: int = 25):
    """Dependency for skip/limit query parameters with validated bounds."""
    def dependency(
        response: Response,
        skip: int = Query(0, ge=0),
        limit: int = Query(default, ge=1, le=MAX_PAGE_SIZE),
    ) -> Page:
        return Page(response, skip, limit)
    return dependency
