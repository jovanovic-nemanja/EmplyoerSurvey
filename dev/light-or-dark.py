__all__ = ['light-or-dark']

# Don't look below, you will not understand this Python code :) I don't.

from js2py.pyjs import *
# setting scope
var = Scope( JS_BUILTINS )
set_global_object(var)

# Code follows:
var.registers(['lightOrDark'])
@Js
def PyJsHoisted_lightOrDark_(color, this, arguments, var=var):
    var = Scope({'color':color, 'this':this, 'arguments':arguments}, var)
    var.registers(['threshold', 'r', 'b', 'hsp', 'color', 'g'])
    pass
    var.put('threshold', Js(127.5))
    if var.get('color').callprop('match', JsRegExp('/^rgb/')):
        var.put('color', var.get('color').callprop('match', JsRegExp('/^rgba?\\((\\d+),\\s*(\\d+),\\s*(\\d+)(?:,\\s*(\\d+(?:\\.\\d+)?))?\\)$/')))
        var.put('r', var.get('color').get('1'))
        var.put('g', var.get('color').get('2'))
        var.put('b', var.get('color').get('3'))
    else:
        var.put('color', (+(Js('0x')+var.get('color').callprop('slice', Js(1.0)).callprop('replace', ((var.get('color').get('length')<Js(5.0)) and JsRegExp('/./g')), Js('$&$&')))))
        var.put('r', (var.get('color')>>Js(16.0)))
        var.put('g', ((var.get('color')>>Js(8.0))&Js(255.0)))
        var.put('b', (var.get('color')&Js(255.0)))
    var.put('hsp', var.get('Math').callprop('sqrt', (((Js(0.299)*(var.get('r')*var.get('r')))+(Js(0.587)*(var.get('g')*var.get('g'))))+(Js(0.114)*(var.get('b')*var.get('b'))))))
    return (var.get('hsp')>var.get('threshold'))
PyJsHoisted_lightOrDark_.func_name = 'lightOrDark'
var.put('lightOrDark', PyJsHoisted_lightOrDark_)
pass
pass


# Add lib to the module scope
light-or-dark = var.to_python()
