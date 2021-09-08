$('#save_btn').click(() => {
    const password = $('#password').val()
    const password_repeat = $('#password_repeat').val()
    if(password !== password_repeat)
        return alertify.error("Passwords don't match.")
    wscb.send({
        cmd: 'update_settings',
        data: {
            mobile_number: $('#mobile_number').val(),
            email_address: $('#email_address').val(),
            password: password,
            password_repeat: password_repeat,
            current_password: $('#current_password').val()
        }
    }, function (resp) {
        //console.log('resp', resp)
        log_resp(resp)
    })
})
