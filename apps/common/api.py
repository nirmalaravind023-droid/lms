from django.http import JsonResponse


def api_success(data=None, *, meta=None, status: int = 200) -> JsonResponse:
    return JsonResponse(
        {
            "ok": True,
            "data": data or {},
            "meta": meta or {},
            "errors": [],
        },
        status=status,
    )


def api_error(message: str, *, code: str = "error", status: int = 400, meta=None) -> JsonResponse:
    return JsonResponse(
        {
            "ok": False,
            "data": {},
            "meta": meta or {},
            "errors": [{"code": code, "message": message}],
        },
        status=status,
    )
