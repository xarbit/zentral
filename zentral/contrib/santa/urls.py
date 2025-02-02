from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from . import views

app_name = "santa"
urlpatterns = [
    # index
    path('', views.IndexView.as_view(), name="index"),

    # configuration / enrollment
    path('configurations/',
         views.ConfigurationListView.as_view(),
         name='configuration_list'),
    path('configurations/create/',
         views.CreateConfigurationView.as_view(),
         name='create_configuration'),
    path('configurations/<int:pk>/',
         views.ConfigurationView.as_view(),
         name='configuration'),
    path('configurations/<int:pk>/events/',
         views.ConfigurationEventsView.as_view(),
         name='configuration_events'),
    path('configurations/<int:pk>/events/fetch/',
         views.FetchConfigurationEventsView.as_view(),
         name='fetch_configuration_events'),
    path('configurations/<int:pk>/events/store_redirect/',
         views.ConfigurationEventsStoreRedirectView.as_view(),
         name='configuration_events_store_redirect'),
    path('configurations/<int:pk>/update/',
         views.UpdateConfigurationView.as_view(),
         name='update_configuration'),
    path('configurations/<int:pk>/enrollments/create/',
         views.CreateEnrollmentView.as_view(),
         name='create_enrollment'),

    # rules
    path('configurations/<int:configuration_pk>/rules/',
         views.ConfigurationRulesView.as_view(),
         name='configuration_rules'),
    path('configurations/<int:configuration_pk>/rules/create/',
         views.CreateConfigurationRuleView.as_view(),
         name='create_configuration_rule'),
    path('configurations/<int:configuration_pk>/rules/<int:pk>/update/',
         views.UpdateConfigurationRuleView.as_view(),
         name='update_configuration_rule'),
    path('configurations/<int:configuration_pk>/rules/<int:pk>/delete/',
         views.DeleteConfigurationRuleView.as_view(),
         name='delete_configuration_rule'),
    path('configurations/<int:configuration_pk>/rules/pick_binary/',
         views.PickRuleBinaryView.as_view(),
         name='pick_rule_binary'),
    path('configurations/<int:configuration_pk>/rules/pick_bundle/',
         views.PickRuleBundleView.as_view(),
         name='pick_rule_bundle'),
    path('configurations/<int:configuration_pk>/rules/pick_certificate/',
         views.PickRuleCertificateView.as_view(),
         name='pick_rule_certificate'),
    path('configurations/<int:configuration_pk>/rules/pick_team_id/',
         views.PickRuleTeamIDView.as_view(),
         name='pick_rule_team_id'),

    # targets
    path('targets/', views.TargetsView.as_view(), name="targets"),
    path('targets/binaries/<str:identifier>/', views.BinaryView.as_view(), name="binary"),
    path('targets/binaries/<str:identifier>/events/',
         views.BinaryEventsView.as_view(), name="binary_events"),
    path('targets/binaries/<str:identifier>/events/fetch/',
         views.FetchBinaryEventsView.as_view(), name="fetch_binary_events"),
    path('targets/binaries/<str:identifier>/events/store_redirect/',
         views.BinaryEventsStoreRedirectView.as_view(), name="binary_events_store_redirect"),
    path('targets/bundles/<str:identifier>/', views.BundleView.as_view(), name="bundle"),
    path('targets/bundles/<str:identifier>/events/',
         views.BundleEventsView.as_view(), name="bundle_events"),
    path('targets/bundles/<str:identifier>/events/fetch/',
         views.FetchBundleEventsView.as_view(), name="fetch_bundle_events"),
    path('targets/bundles/<str:identifier>/events/store_redirect/',
         views.BundleEventsStoreRedirectView.as_view(), name="bundle_events_store_redirect"),
    path('targets/certificates/<str:identifier>/', views.CertificateView.as_view(), name="certificate"),
    path('targets/certificates/<str:identifier>/events/',
         views.CertificateEventsView.as_view(), name="certificate_events"),
    path('targets/certificates/<str:identifier>/events/fetch/',
         views.FetchCertificateEventsView.as_view(), name="fetch_certificate_events"),
    path('targets/certificates/<str:identifier>/events/store_redirect/',
         views.CertificateEventsStoreRedirectView.as_view(), name="certificate_events_store_redirect"),
    path('targets/teamids/<str:identifier>/', views.TeamIDView.as_view(), name="teamid"),
    path('targets/teamids/<str:identifier>/events/',
         views.TeamIDEventsView.as_view(), name="teamid_events"),
    path('targets/teamids/<str:identifier>/events/fetch/',
         views.FetchTeamIDEventsView.as_view(), name="fetch_teamid_events"),
    path('targets/teamids/<str:identifier>/events/store_redirect/',
         views.TeamIDEventsStoreRedirectView.as_view(), name="teamid_events_store_redirect"),

    # API
    path('sync/<str:enrollment_secret>/preflight/<str:machine_id>',
         csrf_exempt(views.PreflightView.as_view()), name='preflight'),
    path('sync/<str:enrollment_secret>/ruledownload/<str:machine_id>',
         csrf_exempt(views.RuleDownloadView.as_view()), name='ruledownload'),
    path('sync/<str:enrollment_secret>/eventupload/<str:machine_id>',
         csrf_exempt(views.EventUploadView.as_view()), name='eventupload'),
    path('sync/<str:enrollment_secret>/postflight/<str:machine_id>',
         csrf_exempt(views.PostflightView.as_view()), name='postflight'),
]


setup_menu_cfg = {
    'items': (
        ('index', 'Overview', False, ('santa',)),
        ('configuration_list', 'Configurations', False, ('santa.view_configuration',)),
        ('targets', 'Targets', False, ('santa.view_target',)),
    )
}
