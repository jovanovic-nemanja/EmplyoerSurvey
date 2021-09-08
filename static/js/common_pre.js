function hide_unhide(){
    if(!$(this).hasClass('hidden') && $(this).hasClass('d-none')){
        $(this).removeClass('d-none')
    }
    if($(this).hasClass('hidden') && !$(this).hasClass('d-none') ){
        $(this).addClass('d-none')
    }
}

function deepEq(object1, object2) {
    const keys1 = Object.keys(object1);
    const keys2 = Object.keys(object2);
    
    if (keys1.length !== keys2.length) {
        return false;
    }
    
    for (const key of keys1) {
        const val1 = object1[key];
        const val2 = object2[key];
        const areObjects = isObject(val1) && isObject(val2);
        if (
            areObjects && !deepEqual(val1, val2) ||
            !areObjects && val1 !== val2
        ) {
            return false;
        }
    }
    
    return true;
}

function isObject(object) {
    return object != null && typeof object === 'object';
}

var hidden_els
let surveys = {};
var browser_is_mobile = false;
var general_data;
let orgs = [];

(function ($) {
    hidden_els = $('.hidden')
})(window.jQuery)
