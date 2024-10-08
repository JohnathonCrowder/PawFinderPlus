from . import main, auth, dog, litter, user, message, vet, admin
from . import main
from . import auth
from . import dog
from . import litter
from . import user
from . import message
from . import vet
from . import blog
from . import dashboard

def init_app(app):
    app.register_blueprint(main.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(dog.bp)
    app.register_blueprint(litter.bp)
    app.register_blueprint(user.bp)
    app.register_blueprint(message.bp)
    app.register_blueprint(vet.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(blog.bp)
    app.register_blueprint(dashboard.bp)

    