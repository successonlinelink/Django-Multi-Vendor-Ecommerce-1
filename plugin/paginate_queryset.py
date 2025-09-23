from django.core.paginator import Paginator

def paginate_queryset(request, queryset, per_page):
    paginator = Paginator(queryset, per_page) # splits your queryset into pages
    page_number = request.GET.get('page') # fetches the current page number from the query string
    # returns a Page object (handles invalid page numbers automatically by returning the first/last page)
    return paginator.get_page(page_number)
