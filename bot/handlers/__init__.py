from aiogram import Router


def get_handlers_router() -> Router:
    from . import ai, delete_stuff, help, models, moods, persona, ping, settings, start

    router = Router()
    router.include_router(ai.router)
    router.include_router(delete_stuff.router)
    router.include_router(help.router)
    router.include_router(models.router)
    router.include_router(moods.router)
    router.include_router(persona.router)
    router.include_router(ping.router)
    router.include_router(settings.router)
    router.include_router(start.router)

    return router