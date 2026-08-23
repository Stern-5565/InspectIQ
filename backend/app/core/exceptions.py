"""
Domain exceptions and their HTTP status mapping. Services/repositories raise these; routes
never construct HTTPException themselves for business-rule failures - that would put
knowledge of HTTP status codes into the business logic layer, backwards from the intended
direction (PROJECT_PLAN.md §5: "API routes must not contain complicated business logic").

Handlers are registered in app/main.py. The catch-all handler for unrecognized exceptions
never returns the real exception message to the client - only logs it server-side - matching
the "error responses never leak internals" rule carried over from PropertyManager.
"""


class AppError(Exception):
    status_code = 500
    detail = "An unexpected error occurred."

    def __init__(self, detail: str | None = None) -> None:
        if detail is not None:
            self.detail = detail
        super().__init__(self.detail)


class NotFoundError(AppError):
    status_code = 404
    detail = "Resource not found."


class ValidationError(AppError):
    status_code = 422
    detail = "Validation failed."


class UnauthorizedError(AppError):
    status_code = 401
    detail = "Authentication required."


class ForbiddenError(AppError):
    status_code = 403
    detail = "You do not have permission to perform this action."


class ConflictError(AppError):
    status_code = 409
    detail = "The request conflicts with the current state of the resource."
