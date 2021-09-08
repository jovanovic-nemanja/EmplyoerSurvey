let admin_orgs = [];
(function ($) {
    let orgsTable = $('.orgs_table').DataTable({
        lengthChange: false,
        pageLength: 20,
        select: true,
        info: false,
        dataSrc: 'data',
        //buttons: ['copy', 'excel', 'pdf'],
        ajax: function (data, callback, settings) {
            callback({
                draw: data.draw,
                data: admin_orgs
            })
        },
        columns: [
            {
                name: 'org_name',
                data: 'org_name',
                /*render: function (icon, type, row, meta) {
                    let icon_color = '#FFCAB6'
                    if (survey_preset !== null && survey_preset === row.id)
                        icon_color = '#FFFFFF'
                    return `<span class="iconify" data-icon="flat-color-icons:survey" data-inline="false" style="font-size: 50px;"></span>`
                    // return `<span class="iconify answer-icon" data-icon="${icon.icon}" style="color: ${icon_color}; font-size: 50px;"></span>`
                }*/
            },
            {
                name: 'employees',
                data: 'employees',
                render: function (_data, type, row, meta) {
                    return `
                        <h6>${_data}</h6>
                        `
                }
            },
            {
                name: 'score',
                data: 'score',
                render: function (_data, type, row, meta) {
                    return `
                                    <h4>${_data}</h4>
                                    `
                }
            }
        ],
        rowCallback: function (row, data) {
            $(row).addClass('table-row');
            if (survey_preset !== null && survey_preset === data.id) {
                $(row).css('background-color', "#FFCAB6")
                //$(row).addClass('selected')
            }
        },
        /*createdRow: function (row, data, index) {
            if (survey_preset !== null && survey_preset === data.id) {
                $(row).css('background-color', "#FFCAB6")
            }
            
        }*/
    })
    orgsTable.buttons().container()
        .appendTo('#datatable-buttons_wrapper .col-md-6:eq(0)')
    orgsTable.clear().draw()
    orgsTable.ajax.reload()
    
    function update_orgs() {
        wscb.send({
            cmd: 'get_general_data'
        }, function (resp) {
            if (!resp.hasOwnProperty('success') || !resp.success)
                console.warn('No success for', resp)
            if (resp.hasOwnProperty('surveys_to_take')) {
                admin_orgs = resp.admin_orgs
                // for (let org of resp.admin_orgs) {
                // }
                console.log('all orgs', orgs)
                orgsTable.ajax.reload()
            }
        })
    }
    
    // ws_connect(update_orgs)
    ws_connect()
})(window.jQuery)
