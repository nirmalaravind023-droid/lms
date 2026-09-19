from __future__ import annotations

from django.core.paginator import Paginator


def build_pagination_context(request, page_obj, *, page_param: str = "page") -> dict:
    query = request.GET.copy()
    query.pop(page_param, None)
    return {
        "page_obj": page_obj,
        "page_param": page_param,
        "page_numbers": list(page_obj.paginator.get_elided_page_range(page_obj.number)),
        "pagination_query": query.urlencode(),
    }


def paginate_items(request, items, *, per_page: int = 10, page_param: str = "page") -> dict:
    paginator = Paginator(items, per_page)
    page_obj = paginator.get_page(request.GET.get(page_param) or 1)
    context = build_pagination_context(request, page_obj, page_param=page_param)
    context["items"] = page_obj.object_list
    return context
