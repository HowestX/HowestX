"""
sudo.utils
"""
import django.contrib.sessions.middleware
import sudo.middleware


def region_name(region):
    """
    Replace special character's from region to make it valid for cookie name.

    region must be string or unicode.
    """
    char_to_be_replaced = [':', '/', '+']

    if region is not None:
        for char in char_to_be_replaced:
            region = region.replace(char, '-')

        region = region.encode('utf-8', 'ignore')

    return region


def sudo_middleware_process_request(request):
    """
    Initialize the session and is_sudo on request object.
    """
    session_middleware = django.contrib.sessions.middleware.SessionMiddleware()
    session_middleware.process_request(request)
    sudo_middleware = sudo.middleware.SudoMiddleware()
    sudo_middleware.process_request(request)
