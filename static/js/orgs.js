let depts_chosen = [];
let depts_on_page = [];
let depts_cache = [];
let depts_for_sel = [];
let invite_dept_sel;
let ws_has_init = false;

(function ($) {
    ws_connect();
    // ws_connect(function (_resp) {
    //     let deptContainer = ''
    //     /*let all_depts = []
    //     if (_resp.hasOwnProperty('depts') && _resp.depts !== null && _resp.depts.length > 0) {
    //         all_depts = _resp.depts
    //     }*/
    //     if (_resp.hasOwnProperty('depts') && _resp.depts.length > 0) {
    //         let depts_html = ''
    //         console.log('depts resp', _resp.depts)
    //         //_resp.depts = JSON.parse(_resp.depts)
    //         depts_cache = _resp.depts
    //         _resp.depts.forEach(dept => {
    //             console.log('adding', dept)
    //             if (!depts_on_page.includes(dept.slug)) {
    //                 //depts_html += `<option value="${dept.slug}">${dept.name}</option>`
    //                 $('#invite_dept').html(depts_html)
    //                 addDeptCard(dept)
    //                 depts_on_page.push(dept.slug)
    //                 depts_for_sel.push({
    //                     id: dept.id,
    //                     text: dept.name,
    //                     slug: dept.slug
    //                 })
    //             }
    //         })
    //         if (!ws_has_init) {
    //             depts_for_sel.unshift({
    //                 id: 0,
    //                 text: 'Select department'
    //             })
    //             invite_dept_sel = $('#invite_dept').select2({
    //                 debug: !in_production,
    //                 data: depts_for_sel,
    //                 placeholder: {
    //                     id: '0', // the value of the option
    //                     text: 'Select a department'
    //                 },
    //                 templateSelection: function (data) {
    //                     if (data.id === '0') {
    //                         return 'Select a department';
    //                     }
    //                     return data.text;
    //                 }
    //             });
    //         }
    //     }
    //     if (_resp.hasOwnProperty('orgs') && _resp.orgs !== null && _resp.orgs.length > 0) {
    //         _resp.orgs.forEach(org => {
    //             console.log('ORG', org)
    //             org_name_cache = org.org_name
    //             $('#org_name').val(org.org_name)
    //             let this_depts_html = ''
    //             for (let this_dept of org.departments) {
    //                 console.log('org dept:', this_dept)
    //                 this_depts_html += `<span class="badge badge-secondary">${this_dept.name}</span>&nbsp;`
    //             }
    //             deptContainer += `<tr class="table-primary">
    //                       <th scope="row">${org.org_name}</th>
    //                       <td class="depts">
    //                         ${this_depts_html}
    //                       </td>
    //                     </tr>`
    //         })
    //         $('#orgs_body').html(deptContainer)
    //     }
        
    //     ws_has_init = true;
    // })

    for (department of departments) {
      addDeptCard(department);
    }
        
    $('#org_name').blur(function(){
        let this_org_name = $('#org_name').val()
        if (this_org_name !== org_name_cache) {
            wscb.send({
                'cmd': 'set_org_name',
                'org_name': this_org_name
            }, function(resp){
                log_resp(resp)
                org_name_cache = this_org_name
            })
        }
    })
    
    // initialize Tagify on the above input node reference
    deptsIn = document.querySelector('input[name=deptsIn]')
    let tagChooser = TagChooser(
        deptsIn,
        tagifyOpts={},
        loadIcons=false,
        wsSender='add_dept'
    )
    tagifyDepts = tagChooser.init(tagType='tags')
    invitesEl = document.querySelector('.invites_email')
    tagifyInv = new Tagify(invitesEl, {
        // email address validation (https://stackoverflow.com/a/46181/104380)
        //pattern: email_validator,
        validate: function(this_tag) {
            const emailOrPhone = this_tag.value
            return (phone_validator.test(emailOrPhone) || email_validator.test(emailOrPhone))
        },
        whitelist: [],
        callbacks: {
            "invalid": onInvalidTag,
            "add": e => {
                $('#invitesMsg').html(``)
            }
        },
        dropdown: {
            position: 'text',
            enabled: 1 // show suggestions dropdown after 1 typed character
        },
        placeholder: 'email1@example.com, +15554445555, etc...'
    });
    addInvBtn = invitesEl.nextElementSibling;  // "add new tag" action-button
    
    $('form input[type="checkbox"]').click(function (e) {
        let label = $('label[for="' + $(this).attr('id') + '"]')
        console.log('clicked', e)
    })
    
    $('#add').click(function (e) {
        e.preventDefault()
        openSearch()
    })
    $('#phone_tab').hide()
    $("#mail_phone").click(function () {
        let thetxt
        if (this.checked) {
            thetxt = "Email Address"
            mail_phone_toggle = true
            $('#phone_tab').hide()
            $('#mail_tab').show()
        } else {
            thetxt = "Phone Number"
            mail_phone_toggle = false
            $('#mail_tab').hide()
            $('#phone_tab').show()
        }
        $('#mail_phone_txt').text(thetxt)
    })
    
    $(".depts").each(function () {
        let this_dept = $(this).text()
        //$(this).text(this_dept.replaceAll('[', '').replaceAll('"', '').replaceAll(']', ''))
    })
    
    // $('#send_invites').click(function() {
    //     let recipJ = $('#invites_email').val()
    //     tagifyInv.removeAllTags()
    //     let recipients = JSON.parse(recipJ)
    //     let mobile_numbers = []
    //     let emails = []
    //     recipients.forEach(recip => { //|| email_validator.test(emailOrPhone))
    //         recip = recip.value
    //         if (phone_validator.test(recip))
    //             return mobile_numbers.push(recip)
    //         if (email_validator.test(recip))
    //             emails.push(recip)
    //     })
    //     wscb.send({
    //         cmd: 'send_invites',
    //         dept: $('#invite_dept').val(),
    //         mobile_numbers: mobile_numbers,
    //         invite_emails: emails
    //     }, function (resp) {
    //         log_resp(resp)
    //     })
    // })
    
    
})(window.jQuery)

function addDeptCard(_dept) {
    let bgcolor = rand_color();
    let color = lightOrDark(bgcolor) ? 'black' : 'white';
    $('#departments').prepend(`<div class="orgcard-container" style="background-color: ${bgcolor}; color: ${color}" data-dept-id="${_dept.id}" data-name="${_dept.dept_name}">${_dept.dept_name}</div>`)
}
