export type SearchResult = {
  category: string;
  title: string;
  subtitle: string;
  url: string;
  meta?: string;
};

export type GlobalSearchResponse = {
  query: string;
  source: string;
  results: SearchResult[];
};

export async function fetchGlobalSearch(query: string): Promise<GlobalSearchResponse> {
  const response = await fetch(`/api/search/?q=${encodeURIComponent(query)}`, {
    credentials: "include",
    headers: {
      "X-Requested-With": "XMLHttpRequest",
    },
  });

  if (!response.ok) {
    throw new Error(`Search request failed with ${response.status}`);
  }

  return response.json() as Promise<GlobalSearchResponse>;
}
