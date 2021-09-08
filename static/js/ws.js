let reconnect_delay = 4000
let ws_connected = false

const on_connect = (on_open) => {
    try {
        
        console.log('Connected to websocket server!')
    
        wscb.send({
            cmd: 'token',
            //puid: `#s${Math.random()}`
        }, resp => {
            console.log('Token response:', resp)

            if (on_open !== undefined) {
                on_open();
            }
        });
        // wscb.send({
        //     cmd: 'get_general_data'
        // }, function (resp) {
        //     if (!resp.hasOwnProperty('success') || !resp.success)
        //         console.warn('No success for', resp)
        //     else{
        //         console.log('resp:', resp)
        //     }
        //     if (resp.hasOwnProperty('questions')) {
        //         //questions = resp.surveys_to_take
        //         orgs = resp.orgs
        //         if (typeof questionsTable !== 'undefined' && questionsTable !== null) {
        //             questionsTable.ajax.reload()
        //         }
        //         // questionsTable.responsive.recalc()
        //         // questionsTable.columns.adjust().draw()
        //         // questionsTable.fixedHeader.adjust()
        //         // .rows.add(resp.questions).draw()
        //     }
        //     if (resp.hasOwnProperty('notifications') ) {
        //         let noti_html = ''
        //         noti_cnt = 0
        //         for (let noti of resp.notifications) {
        //             noti_cnt += 1
        //             console.log('Processing notification', noti)
        //             noti_html += `<a class="dropdown-item notify-item" href="${noti.calling_path}">
        //                               <div class="notify-icon bg-primary"><span class="iconify" data-icon="${noti.icon}" data-inline="false"></span></div>
        //                               <p class="notify-details"><b>${noti.title}</b><span class="iconify rm_noti_icon" data-toggle="tooltip" data-placement="top" title="Delete Notification" data-noti="${noti.id}" data-icon="whh:circledelete" data-inline="false"></span><small class="text-muted">${noti.msg}</small></p>
        //                             </a>`
        //         }
        //         if (noti_html !== notifications) {
        //             $('.noti_container').html(noti_html)
        //             $('#notify_cnt').text(noti_cnt)
        //         }
                
        //     }
        //     if (on_open !== undefined) {
        //         on_open(resp)
        //     }
        // })
    } catch {
        setTimeout(on_connect, 100)
    }
    
}

// FIXME: Check connection status before sending message & reconnect if necessary, preempting recon delay
function ws_connect(on_open, is_reconnect=false) {
    wscb = new WebSockets_Callback({
        proto: ws_proto,
        address: location.hostname,
        port: location.port,
        verbose: true,
        asClient: true,
        onOpen: (conn) => {
            if(is_reconnect) {
                reconnect_delay = 4000
                // alertify.success('Successfully connected to Hiyer.')
            }
            on_connect(on_open)
        },
        onError: function (e) {
            console.log('WS connection error:', e)
        },
        onClose: () => {
            ws_connected = false
            reconnect_delay = reconnect_delay < 60000 ? reconnect_delay + 4000 : reconnect_delay
            let reconnect_delay_seconds = reconnect_delay / 1000
            console.warn(`Hiyer connection lost. Reconnecting in ${reconnect_delay_seconds} seconds...`)
            // alertify.error(`Hiyer connection lost. Reconnecting in ${reconnect_delay_seconds} seconds...`)
            setTimeout(() => {
                ws_connect(on_open, is_reconnect=true)
            }, reconnect_delay)
        }
    })
    
    wscb.on('globe:surveys', function (msg) {
        msg.data.forEach((dat, i) => {
            //console.log('dat:', dat)
            $(`#row_${i}`).text(dat)
        })
    })
    
    wscb.on('token', function (msg) {
        if (msg.success) {
            console.log('Got Token:', msg.data)
            $('#jwt_token').val(msg.data)
        }
    })
}


(function ($) {

})(window.jQuery)
