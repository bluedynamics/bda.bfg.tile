import os
from webob import Response
from webob.exc import HTTPFound
from zope.interface import (
    Interface, 
    Attribute, 
    implements,
)
from zope.component import (
    queryUtility,
    getMultiAdapter,
    ComponentLookupError,
)
from repoze.bfg.interfaces import (
    IRequest,
    IResponseFactory,
    IAuthenticationPolicy,
    IAuthorizationPolicy,
    IDebugLogger,
)
from repoze.bfg.settings import get_settings
from repoze.bfg.configuration import _secure_view
from repoze.bfg.exceptions import Forbidden
from repoze.bfg.threadlocal import get_current_registry
from repoze.bfg.path import caller_package
from repoze.bfg.renderers import template_renderer_factory
from repoze.bfg.chameleon_zpt import ZPTTemplateRenderer

class ITile(Interface):
    """Renders some HTML snippet."""
    
    def __call__(model, request):
        """Renders the tile.
        
        It's intended to work this way: First it calls its own prepare method, 
        then it checks its own show attribute. If this returns True it renders 
        the template in the context of the ITile implementing class instance.  
        """
        
    def prepare():
        """Prepares the tile.
        
        I.e. fetch data to display ... 
        """
        
    show = Attribute("""Render this tile?""")
    
def _update_kw(**kw):
    if not ('request' in kw and 'model' in kw):
        raise ValueError, "Expected kwargs missing: model, request."
    kw.update({'tile': TileRenderer(kw['model'], kw['request'])})    
    return kw

def _redirect(kw):
    if kw['request'].environ.get('redirect'):
        return True
    return False
    
def render_template(path, **kw):
    kw = _update_kw(**kw)
    if _redirect(kw):
        return u''
    if not (':' in path or os.path.isabs(path)): 
        raise ValueError, 'Relative path not supported: %s' % path
    renderer = template_renderer_factory(path, ZPTTemplateRenderer)
    return renderer(kw, {})    
    
def render_template_to_response(path, **kw):
    kw = _update_kw(**kw)
    kw['request'].environ['redirect'] = None
    renderer = template_renderer_factory(path, ZPTTemplateRenderer)
    result = renderer(kw, {})
    if _redirect(kw):
        return HTTPFound(location=kw['request'].environ['redirect'])
    response_factory = queryUtility(IResponseFactory, default=Response)
    return response_factory(result)
    
class Tile(object):
    implements(ITile)
    
    def __init__(self, path, attribute):
        self.path = path
        self.attribute = attribute

    def __call__(self, model, request):
        self.model = model
        self.request = request
        self.prepare() # TODO: discuss if needed. i think yes (jens)
        if not self.show:
            return u''
        if self.path:
            return render_template(self.path, request=request,
                                       model=model, context=self)
        renderer = getattr(self, self.attribute)
        result = renderer()
        return result
    
    @property
    def show(self): 
        return True
    
    def prepare(self): 
        pass
    
    def render(self):
        return u''
    
    def redirect(self, url):
        # why do we need a redirect in a tile!?
        self.request.environ['redirect'] = url
    
    @property
    def nodeurl(self):
        relpath = [p for p in self.model.path if p is not None]
        return '/'.join([self.request.application_url] + relpath)

class TileRenderer(object):
    
    def __init__(self, model, request):
        self.model, self.request = model, request
    
    def __call__(self, name):
        try:
            tile = getMultiAdapter((self.model, self.request), ITile, name=name)
        except ComponentLookupError, e:
            return u"Tile with name '%s' not found:<br /><pre>%s</pre>" % \
                   (name, e)
        return tile
    
def _consume_unauthorized(tile):
    """wraps tile, consumes Unauthorized and returns empty unicode string. 
    """
    def consumer(context, request):
        try:
            tile(context, request)
        except Forbidden, e:
            settings = get_settings()
            if settings['debug_authorization']:
                logger = IDebugLogger()
                logger.debug(u'Forbidden tile %s called, ' % repr(tile) + 
                             u'Consumed Exception:\n %s' % e)
            return u''
    return consumer

# Registration
def registerTile(name, path=None, attribute='render',
                 interface=Interface, _class=Tile, 
                 permission='view', strict=True):
    """registers a tile.
    
    ``name``
        identifier of the tile it later looked up with.
    
    ``path``
        either relative path to the template or absolute path or path prefixed
        by the absolute package name delimeted by ':'. If ``path`` is used
        ``attribute`` is ignored. 
        
    ``attribute``
        attribute on the given _class to be used to render the tile. Defaults to
        ``render``.
        
    ``interface`` 
        Interface or Class of the bfg model the tile is registered for.
        
    ``_class``
        Class to be used to render the tile. usally ``bda.bfg.tile.Tile`` or a
        subclass of. Promises to implement ``bda.bfg.ITile.
        
    ``permission`` 
        Enables security checking for this tile. Defaults to ``view``. If set to
        ``None`` security checks are disabled.
        
    ``strict``
        Wether to raise ``Forbidden`` or not. Defaults to ``True``. If set to 
        ``False`` the exception is consumed and an empty unicode string is 
        returned. 
    """ 
    if path:
        if not (':' in path or os.path.isabs(path)): 
            caller = caller_package(level=1)
            path = '%s:%s' % (caller.__name__, path)
    view = _class(path, attribute)
    registry = get_current_registry()
    if permission is not None:
        authn_policy = registry.queryUtility(IAuthenticationPolicy)
        authz_policy = registry.queryUtility(IAuthorizationPolicy)    
        view = _secure_view(view, permission, authn_policy, authz_policy)
    if not strict:
        view = _consume_unauthorized(view)
    registry.registerAdapter(view, [interface, IRequest], ITile, name, 
                             event=False)
    
class tile(object):
    """Decorator to register classes and functions as tiles.
    """
    
    def __init__(self, name, path=None, attribute='render',
                 interface=Interface, permission='view', 
                 strict=True, level=2):
        """ see ``registerTile`` for details on the other parameters.
        
        ``level`` 
            is a bit special to make doctests pass the magic path-detection.
            you must never touch it in application code.
        
          
        """
        self.name = name
        self.path = path
        if path:
            if not (':' in path or os.path.isabs(path)): 
                caller = caller_package(level)
                self.path = '%s:%s' % (caller.__name__, path)
        self.attribute = attribute
        self.interface = interface
        self.permission = permission
        self.strict = strict

    def __call__(self, ob):
        registerTile(self.name,
                     self.path,
                     self.attribute,
                     interface=self.interface,
                     _class=ob,
                     permission=self.permission,
                     strict=self.strict)
        return ob