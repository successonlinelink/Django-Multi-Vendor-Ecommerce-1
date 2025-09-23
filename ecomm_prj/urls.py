from django.contrib import admin
from django.urls import path, include

from django.conf import settings
from django.conf.urls.static import static

# from django.contrib.admin.views.decorators import staff_member_required
# from django.contrib.auth import views as auth_views


urlpatterns = [
    path('admin/', admin.site.urls),

    # used apps
    
    path('', include("store.urls")),
    path('auth/', include("userauths.urls")),
    path('customer/', include("customer.urls")),
    path('vendor/', include("vendor.urls")),
    # path('blog/', include("blog.urls")),

    path('ckeditor5/', include('django_ckeditor_5.urls')),
]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
