from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views import View

from .search import unified_search


class GlobalSearchApiView(LoginRequiredMixin, View):
    def get(self, request):
        query = request.GET.get("q", "").strip()
        results, source = unified_search(request.user, query)
        return JsonResponse(
            {
                "query": query,
                "source": source,
                "results": results,
            }
        )
