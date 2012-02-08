from django.conf.urls.defaults import *
import django.views.generic.simple
import settings

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns("",
    # Uncomment the admin/doc line below and add "django.contrib.admindocs"
    # to INSTALLED_APPS to enable admin documentation:
    (r"^admin/doc/", include("django.contrib.admindocs.urls")),

    # Uncomment the next line to enable the admin:
    (r"^admin/nystatus/zopeinstance/check/(?P<id>\d+)/$", "nystatus.views.admin_trigger"),
    (r"^admin/nystatus/product/check/(?P<id>\d+)/$", "nystatus.views.admin_product_trigger"),
    (r"^admin/", include(admin.site.urls)),
    (r"^media/(.*)", "django.views.static.serve", {"document_root": settings.MEDIA_ROOT}),
    (r"^$", "nystatus.views.index")
)

