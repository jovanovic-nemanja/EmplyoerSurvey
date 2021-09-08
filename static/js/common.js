$.fn.selectpicker.Constructor.BootstrapVersion = '4';

const capFirst = (s) => {
    if (typeof s !== 'string') return ''
    return s.charAt(0).toUpperCase() + s.slice(1)
}


function require_js(url) {
    if (url.toLowerCase().substr(-3) !== '.js') url += '.js'; // to allow loading without js suffix;
    if (!require.cache) require.cache = []; //init cache
    var exports = require.cache[url]; //get from cache
    if (!exports) { //not cached
        try {
            exports = {};
            var X = new XMLHttpRequest();
            X.open("GET", url, 0); // sync
            X.send();
            if (X.status && X.status !== 200) throw new Error(X.statusText);
            var source = X.responseText;
            // fix (if saved form for Chrome Dev Tools)
            if (source.substr(0, 10) === "(function(") {
                var moduleStart = source.indexOf('{');
                var moduleEnd = source.lastIndexOf('})');
                var CDTcomment = source.indexOf('//@ ');
                if (CDTcomment > -1 && CDTcomment < moduleStart + 6) moduleStart = source.indexOf('\n', CDTcomment);
                source = source.slice(moduleStart + 1, moduleEnd - 1);
            }
            // fix, add comment to show source on Chrome Dev Tools
            source = "//@ sourceURL=" + window.location.origin + url + "\n" + source;
            //------
            var module = { id: url, uri: url, exports: exports }; //according to node.js modules
            var anonFn = new Function("require", "exports", "module", source); //create a Fn with module code, and 3 params: require, exports & module
            anonFn(require, exports, module); // call the Fn, Execute the module
            require.cache[url] = exports = module.exports; //cache obj exported by module
        } catch (err) {
            throw new Error("Error loading module " + url + ": " + err);
        }
    }
    return exports; //require returns object exported by module
}


function copyToClipboard(element) {
    var $temp = $("<textarea>");
    $("body").append($temp);
    $temp.val($(element).val()).select();
    document.execCommand("copy");
    $temp.remove();
}

function fmt_cron(cron_txt) {
    cron_txt = cron_txt.replaceAll('* minutes', 'minute')
    cron_txt = cron_txt.replaceAll('* hours', 'hour')
    cron_txt = cron_txt.replaceAll('* days', 'day')
    cron_txt = cron_txt.replaceAll('* weeks', 'week')
    cron_txt = cron_txt.replaceAll('* months', 'month')
    return cron_txt.toLowerCase()
}


function log_resp(resp, style = null) {
    if (resp.hasOwnProperty('success') && resp.success) {
        return alertify.success(`${resp.msg}`)
    } else if (resp.hasOwnProperty('success') && !resp.success) {
        return alertify.error(`Error: ${resp.msg}`)
    } else {
        if (alert_style === 'log')
            return alertify.log(resp)
        if (alert_style === 'success' || alert_style === 'info')
            return alertify.success(resp)
        if (alert_style === 'error')
            return alertify.error(resp)
    }

    // if(style !== undefined && style !== null) {
    //
    // }
    //
}

function backend_alert(msg, _alert_style = 'log') {
    if (_alert_style === 'log')
        return alertify.log(msg)
    if (_alert_style === 'success' || _alert_style === 'info')
        return alertify.success(msg)
    if (_alert_style === 'error' || _alert_style === 'danger')
        return alertify.error(msg)
    return alertify.log(msg)
}

function update_notify(notifications = []) {
    let noti_html = ''
    notifications.forEach(noti => {
        noti_html += `
        <a class="dropdown-item notify-item" href="javascript:void(0);">
            <div class="notify-icon bg-primary"><i class="fa fa-sticky-note"></i></div>
            <p class="notify-details"><b>${noti.title}</b><small class="text-muted">You were
              matched to a new survey.</small></p>
        </a>
        `
    })
}


(function ($) {

    $("#ytModal iframe").attr("src", $("#ytModal iframe").attr("src"));  // TODO: Use this for each page individually
    $("#ytModal").on('hidden.bs.modal', function (e) {
    });

    $('.modal-content').resizable({
        //alsoResize: ".modal-dialog",
        //minHeight: 150
    });
    $('.modal-dialog').draggable();

    $('#yt-player').on('show.bs.modal', function () {
        $(this).find('.modal-body').css({
            'max-height': '100%'
        });
    });

    if (alert_msg !== undefined && alert_msg !== 'None' && alert_msg !== 'undefined' && alert_msg !== '' && alert_msg !== null) {
        console.log('ALERT', alert_msg)
        console.log(alert_style)
        backend_alert(alert_msg, alert_style)
    }
})(window.jQuery)


function notify_user(title, msg, type, icon,) {

}

function uuidv4() {
    return ([1e7] + -1e3 + -4e3 + -8e3 + -1e11).replace(/[018]/g, c =>
        (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16)
    );
}

function rand_color() {
    return tag_colors[Math.floor(Math.random() * tag_colors.length)]
}

const email_validator = /^(([^<>()\[\]\\.,;:\s@"]+(\.[^<>()\[\]\\.,;:\s@"]+)*)|(".+"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/
const phone_validator = /^\+(?:[0-9] ?){6,14}[0-9]$/;
