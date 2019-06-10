import importlib


def get_current_config(env):
    # Return the appropriate config depending on env variable
    if env == 'testing':
        name = 'TestingConfig'
    elif env == 'development':
        name = 'DevelopmentConfig'
    elif env == 'production':
        name = 'ProductionConfig'
    else:
        raise Exception('Unknown environment type provided {}. Please set environment '
                        'to one of testing, development, production'.format(env))

    mod = importlib.__import__('core.config.{}'.format(env), fromlist=[name])
    return getattr(mod, name)
