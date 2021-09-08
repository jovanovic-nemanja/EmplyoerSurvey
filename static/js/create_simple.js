let iconsIn,
    iconTags,
    qTagsIn,
    qDeptsChosen,
    qTagsChosen,
    qTagsChosen_2,
    tagifyIcon,
    tagifyQtags;
let send_schedule_toggle = true;
let qIconChosen = "icon8:question mark";
var choice_dex = [];

(function ($) {
    
    $('#q_icon').click(function (e) {
        e.preventDefault()
        openSearch()
    })
    
    // initialize Tagify on the above input node reference
    iconsIn = document.querySelector('input[name=iconsIn]')
    let iconChooser = TagChooser(iconsIn,
        {
            maxTags: 1
        },
        loadIcons = true,
        wsSender='',
        function (_tag, _fn) {
            _fn.fillIconBox(_tag, 'q_icon')
            qIconChosen = `${_tag.prefix}:${_tag.slug}`
            console.log('iconCb', qIconChosen)
        }
    )
    tagifyIcon = iconChooser.init(
        tagLimit=true,
        tagType='icon'
    )
    console.log('tagifyIcon', tagifyIcon)
    
    qTagsIn = document.querySelector('input[name=qTags]')
    let qTagsChooser = TagChooser(qTagsIn,
        {
            maxTags: 3
        },
        loadIcons = false,
        wsSender = '',
        function (_tag, _fn) {
            qTagsChosen = _tag
            console.log('onAddCb', qIconChosen)
        }
    )
    tagifyQtags = qTagsChooser.init(
        loadIcons = false,
        tagLimit = false,
        tagType = 'tag'
    )
    const deptsIn = document.querySelector('input[name=qDepts]')
    let deptsChooser = TagChooser(deptsIn,
        {
            maxTags: 3
        },
        loadIcons = false
    )
    tagifyDepts = deptsChooser.init(
        loadIcons = false,
        tagLimit = false,
        tagType = 'tag'
    )
    console.log('tagifyQtags', tagifyQtags)
    
    let questionsTable = $('#table-questions').DataTable({
        lengthChange: false,
        pageLength: 20,
        select: true,
        info: false,
        dataSrc: 'data',
        //buttons: ['copy', 'excel', 'pdf'],
        ajax: function (data, callback, settings) {
            console.log('questionsquestions', questions)
            callback({
                draw: data.draw,
                data: questions
            })
        },
        columns: [
            {
                name: 'icon',
                data: 'icon',
                render: function (icon, type, row, meta) {
                    //console.log('render', icon)
                    //console.log('row', row)
                    return `<span class="iconify" data-icon="${icon.icon}" style="color: ${icon.color}"></span>`
                }
            },
            {
                name: 'question',
                data: 'question'
            },
            {
                name: 'tags',
                render: function(data, type, row, meta) {
                    console.log('tags, type, row, meta', row)
                    let this_row = ''
                    if(row.hasOwnProperty('tag1') && row.tag1 !== null)
                        this_row += `${row.tag1} `
                    if (row.hasOwnProperty('tag2') && row.tag2 !== null)
                        this_row += `${row.tag2} `
                    if (row.hasOwnProperty('tag3') && row.tag3 !== null)
                        this_row += `${row.tag3} `
                    return this_row
                }
            }
        ]
    })
    questionsTable.buttons().container()
        .appendTo('#datatable-buttons_wrapper .col-md-6:eq(0)')
    questionsTable.clear().draw()
    questionsTable.ajax.reload()
    
    setInterval(function () {
        // TODO: Convert this to pubsub
        wscb.send({
            cmd: 'get_general_data'
        }, function (resp) {
            if(!resp.hasOwnProperty('success') ||  !resp.success)
                console.warn('No success for', resp)
            console.log('resp.questions:', resp.questions)
            if (resp.hasOwnProperty('questions')) {
                //console.log(resp.questions)
                questions = resp.questions
                questionsTable.ajax.reload()
                //questionsTable.responsive.recalc()
                //questionsTable.columns.adjust().draw()
                //questionsTable.fixedHeader.adjust()
                // .rows.add(resp.questions).draw()
            }
        })
    }, 5000)
    let qIconRaw = qIconChosen.split(':')
    let qIconPrefix = qIconRaw[0]
    let qIconSlug = qIconRaw[1]
    
    $('#addQuestion').click(function () {
        console.log('qqq', qIconChosen);
        let choices = []
        $('.choice').forEach(function (e) {
            choices.push($(e).val())
        })
        wscb.send({
            cmd: 'add_question',
            question: {
                question: $('#question').val(),
                choices: choices,
                icon_prefix: qIconPrefix,
                icon: qIconChosen,
                icon_color: $(`tag_ico_${qIconSlug}`).css('background-color'),
                tags: $('#qTags').val(),
                departments: $('#qDepts').val()
            },
        }, function (resp) {
            alert(resp.msg)
        })
    })
    var cron = $('.cron')
        .jqCron()
        .jqCronGetInstance()
    $('#schedule_tab').hide()
    $('#q_scheduler_container').hide()
    $("#send_schedule_toggle").click(function () {
        let thetxt
        if (this.checked) {
            thetxt = "Send Now"
            send_schedule_toggle = true
            $('#schedule_tab').hide()
            $('#send_tab').show()
            $('#q_scheduler_container').hide()
        } else {
            thetxt = "Schedule"
            send_schedule_toggle = false
            $('#send_tab').hide()
            $('#schedule_tab').show()
            $('#q_scheduler_container').show()
        }
        $('#send_schedule_txt').text(thetxt)
        
    })
    
    /*$.each(questions, function (i, item) {
        console.log('selectors', item)
        $('#question_selector').append($('<option>', {
            value: item.id,
            text: item.question
        }))
    })*/
    var cron_2 = $('.cron2')
        .jqCron()
        .jqCronGetInstance()
    
    var tagifyDepts_2
    const deptsIn_2 = document.querySelector('input[name=qDepts_2]')
    let deptsChooser_2 = TagChooser(deptsIn_2,
        {
            maxTags: 3
        },
        loadIcons = false
    )
    tagifyDepts_2 = deptsChooser_2.init(
        loadIcons = false,
        tagLimit = false,
        tagType = 'tag'
    )
    
    var qTagsIn_2 = document.querySelector('input[name=qTags_2]')
    let qTagsChooser_2 = TagChooser(qTagsIn_2,
        {
            maxTags: 3
        },
        loadIcons = false,
        wsSender = '',
        function (_tag, _fn) {
            qTagsChosen = _tag
            console.log('onAddCb', qIconChosen)
        }
    )
    var tagifyQtags_2 = qTagsChooser_2.init(
        loadIcons = false,
        tagLimit = false,
        tagType = 'tag'
    )
    
    $('#addSchedule_2').click(function () {
        console.log('cron_2', cron_2.getCron());
        wscb.send({
            cmd: 'add_cron',
            tags: $('#qTags_2').val(),
            departments: $('#qDepts_2').val(),
            when_send: cron_2.getCron()
        }, function (resp) {
            alert(resp.msg)
        })
    })
    

    $('#add-choice').click(function(e){
        let new_choice_num = $("#choices").children().length / 2 + 1
        $('#choices').append(`<span id="rm_choice_${new_choice_num}" class="iconify rm_choice" data-icon="octicon:dash" style="color: red; float: left; font-size: 26px;"></span><input id="choice_${new_choice_num}" class="form-control choice" name="choice_${new_choice_num}" type="text" placeholder="Option #${new_choice_num}">`)
        console.log('n', new_choice_num)
    })
    $('.rm_choice').on('click', function(e){
        console.log('rm choice', e)
    })
    
    ws_connect()
    
    hidden_els = $('.hidden')
    
})(window.jQuery)



/*let hidden_els = $('.hidden')
setInterval(() => {
    let hidden_els_now = $('.hidden')
    if(hidden_els_now !== hidden_els) {
        hidden_els_now.each(el => {
            console.log('Hidden:', el)
        })
    }
    
}, 1000)*/
