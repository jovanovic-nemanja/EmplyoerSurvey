
(function ($) {
    
    let surveys_updating = false
    let surveysTable = $('#table-surveys').DataTable({
        lengthChange: false,
        pageLength: 20,
        select: true,
        info: false,
        dataSrc: 'data',
        //buttons: ['copy', 'excel', 'pdf'],
        ajax: function (data, callback, settings) {
            callback({
                draw: data.draw,
                data: surveys
            })
        },
        columns: [
            {
                name: 'title',
                data: 'title',
                render: function(_data, type, row, meta){
                    return `
                    <h5>${_data}</h5>
                    `
                }
            },
            {
                name: 'depts',
                data: 'depts',
                render: function (_depts, type, row, meta) {
                    let deptsHtml = ""
                    
                    if(typeof _depts == 'string'){
                        //console.log('DEPLOAD', row)
                        _depts = JSON.parse(_depts)
                    }
                    for (let _dept of _depts) {
                        console.log('dept Loop', _dept, row)
                        deptsHtml += `<button id="s_${row.id}" type="button" class="btn btn-raised btn-secondary">` + _dept + `</button>`
                    }
                    
                    return deptsHtml
                }
            },
            {
                name: 'actions',
                render: function(data, type, row, meta){
                    return `
                    <a href="/s/${row.survey_uuid}" id="answer_btn_${row.id}" class="btn btn-primary" value="${row.survey_uuid}">Take This Survey</a>
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
        createdRow: function (row, data, index) {
            if (survey_preset !== null && survey_preset === data.id) {
                $(row).css('background-color', "#FFCAB6")
            }
            
        }
    })
    surveysTable.buttons().container()
        .appendTo('#datatable-buttons_wrapper .col-md-6:eq(0)')
    surveysTable.clear().draw()
    surveysTable.ajax.reload()
    
    function update_surveys() {
        /*if(!surveys_updating) {
            setInterval(function () {
                update_surveys()
            }, 5000)
            surveys_updating = true
        }*/
        // TODO: Convert this to pubsub
        wscb.send({
            cmd: 'get_general_data'
        }, function (resp) {
            if (!resp.hasOwnProperty('success') || !resp.success)
                console.warn('No success for', resp)
            if (resp.hasOwnProperty('surveys_to_take')) {
                for(let cron of resp.surveys_to_take){
                    console.log('cronloop', cron)
                    for(let survey_uuid of JSON.parse(cron.surveys)) {
                        console.log('uuid', survey_uuid)
                        let survey_item = cron
                        survey_item.survey_uuid = survey_uuid
                        surveys.push(survey_item)
                    }
                }
                console.log('all surveys', surveys)
                surveysTable.ajax.reload()
            }
        })
    }
    
    // ws_connect(update_surveys)
    ws_connect()
    
    $(document).on("click", `.answer_btn`, function () {
        const _qid = $(this).val()
        const _ans = $(`#qa_${_qid}`).val()
        console.log('Submitting answer: ' ,_ans, 'for survey:', _qid)
        wscb.send({
            cmd: 'submit_answer',
            qid: _qid,
            answer: _ans
        }, function (resp) {
            if (!resp.hasOwnProperty('success') || !resp.success) {
                alertify.error(`Couldn't submit answer. Refresh page or check connection.`)
                console.warn('Could not submit answer.')
            } else {
                update_surveys()
                alertify.success('Answer submitted.')
                console.log('Answer submitted.')
            }
        })
    })
    
})(window.jQuery)

