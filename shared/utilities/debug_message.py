


from project import settings


def DEBUG_MESSAGE(message):
    if settings.DEBUG==True:
        print(message)
        