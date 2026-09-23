from fastapi import Query
from fastapi.responses import JSONResponse


class PaginationSchema:

    def __init__(
        self,
        page: int = Query(1),
        pageSize: int = Query(10),
        search: str = Query("")
    ):

        self.page = page
        self.pageSize = pageSize
        self.search = search


# =========================================
# SUCCESS RESPONSE
# =========================================

def api_response_success(
    data=None,
    message: str = "Success",
    status_code: int = 200,
    pagination=None
):

    return JSONResponse(
        status_code=status_code,
        content={
            "data": data,
            "success": True,
            "status_code": status_code,
            "message": message,
            "pagination": pagination
        }
    )


# =========================================
# ERROR RESPONSE
# =========================================

def api_response_error(
    message: str = "Something went wrong",
    status_code: int = 500,
    data=None
):

    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "status_code": status_code,
            "message": message,
            "data": data,
        }
    )