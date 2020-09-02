from django.conf import settings


def features(request):
    return {
        'CWR2_AVAILABLE': settings.CWR2_AVAILABLE,
        'CWR3_AVAILABLE': settings.CWR3_AVAILABLE,
    }
