(function ($) {
    var has_updated = undefined
    const cron_humanizer = window.cronstrue
    let scheduled_surveys
    let saved_surveys_cache = ''
    let depts_html_cache = ''
    let cats_html_cache = ''
    let questions_tagify
    
    // ws_connect(update_bank)
    ws_connect()
    
    
    function load_creator_cache(_resp) {
        console.log('load_creator_cache', _resp)
        if (_resp.hasOwnProperty('saved_surveys') && _resp.saved_surveys !== null && _resp.saved_surveys.length > 0) {
            $('.saved_surveys_container').show()
            $('#no_surveys_container').hide()
            let saved_surveys_parts = ''
            let option_els = []
            for (let [key, value] of Object.entries(_resp.saved_surveys)) {
                for (let [k, v] of Object.entries(value)) {
                    console.log('v', v)
                    saved_surveys_parts = `${saved_surveys_parts}${v.id}`.trim()
                    surveys[v.id] = {
                        id: v.id,
                        title: v.title,
                        json: v.json
                    }
                    option_els.push(`<option value="${v.id}" class="survey_load_item">${v.title}</option>`)
                }
            }
            if (saved_surveys_parts !== saved_surveys_cache) {
                saved_surveys_cache = saved_surveys_parts
                option_els.forEach(function (e) {
                    $('#saved_surveys').append(e)
                })
                $('#saved_surveys').selectpicker('refresh')
            }
            console.log(surveys)
        } else {
            console.log('no surveys to add')
            $('.saved_surveys_container').hide()
            $('#no_surveys_container').show()
        }
        
    }
    
    $("#start-date").AnyPicker({
        mode: "datetime",
        
        showComponentLabel: true,
        
        dateTimeFormat: "MMM dd,yyyy hh:mm AA",
        
        onChange: function (iRow, iComp, oSelectedValues) {
            console.log("Changed Value : " + iRow + " " + iComp + " " + oSelectedValues);
        }
    });
    
    $("#end-date").AnyPicker({
        mode: "datetime",
        
        showComponentLabel: true,
        
        dateTimeFormat: "MMM dd,yyyy hh:mm AA",
        
        onChange: function (iRow, iComp, oSelectedValues) {
            console.log("Changed Value : " + iRow + " " + iComp + " " + oSelectedValues);
        }
    });
    
    $('#cron-click').click(function (e) {
        $('#cron_modal').modal('show')
    })
    
    // const cronstrue = window.cronstrue;
    let first_cron = true
    $('#cron-picker').cronPicker({
        // time format, either 12 hours or 24 hours (default)
        format: '24',
        
        // available formatters:
        //   - StandardCronFormatter (crontab specification)
        //   - QuartzCronFormatter (quartz.net specification)
        cronFormatter: QuartzCronFormatter,
        
        // callback function called each time cron expression is updated
        onCronChanged: function (cron) {
            cron = cron.replaceAll('undefined', '*')
            console.log(cron);
            let cron_human = fmt_cron(cron_humanizer.toString(cron))
            console.log(cron_human)
            if (!first_cron) {
                $('#cron_schedule').val(cron)
                $('#cron-modal-human').text(cron_humanizer.toString(cron))
                $('#cron-click').val(cron_human)
            }
            if (first_cron)
                first_cron = false
        }
    });
    
    $('#no_surveys_container').hide()
    $('#no_depts_container').hide()
    $('#no_cats_container').hide()
    $('#no_questions_container').hide()
    $('#schedule_survey_btn').click(() => {
        let category = $('#cats').val()
        category = (category !== '') ? parseInt(category) : 0
        let _tags = $('#tags').val()
        _tags = (_tags !== '') ? JSON.parse(_tags) : []
        wscb.send({
            cmd: 'add_schedule_lite',
            title: $('#survey_title').val(),
            depts: $('#depts').val(),
            cron_schedule: $('#cron_schedule').val(),
            use_random: $('#use_random').val(),
            surveys: $('#saved_surveys').val(),
            start_date: $('#start-date').val(),
            end_date: $('#end-date').val(),
            tags: _tags,
            cat: category,
            questions: $('#questions_dropdown').val()
        }, function (resp) {
            console.log('resp', resp)
            log_resp(resp)
            update_bank()
        })
    })
    
    $('#copy_btn').click(() => {
        let cron_schedule = $('#cron_schedule').val()
        const survey_schedule = {
            title: $('#survey_title').val(),
            departments: $('#depts').val(),
            cron_schedule: (cron_schedule !== '0' && cron_schedule !== '') ? fmt_cron(cron_humanizer.toString($('#cron_schedule').val())) : 'Not set.',
            use_random: $('#use_random').val(),
            surveys: $('#saved_surveys').val(),
            start_date: $('#start-date').val(),
            end_date: $('#end-date').val()
        }
        let survey_schedule_txt = ''
        let tmpval
        for (const [key, value] of Object.entries(survey_schedule)) {
            tmpval = value
            if (value === 'False')
                tmpval = 'No'
            if (value === 'True')
                tmpval = 'Yes'
            if (value === '')
                tmpval = 'Not set'
            survey_schedule_txt += `${key}: ${tmpval}\r\n`
        }
        console.log(survey_schedule_txt)
        $('#clipboard_holder').val(survey_schedule_txt)
        copyToClipboard('#clipboard_holder')
        alertify
            .log('Survey data copied to clipboard.');
    })
    
    function update_bank() {
        
        wscb.send({
            cmd: 'get_general_data'
        }, function (resp) {
            console.log('RESP', resp)
            if (resp.hasOwnProperty('crons')) {
                load_creator_cache(resp)
                if (scheduled_surveys !== resp.crons) {
                    scheduled_surveys = resp.crons
                    console.log('sched', scheduled_surveys)
                    let cron_html = ''
                    scheduled_surveys.forEach(cron => {
                        console.log('cron', cron)
                        const now = new Date();
                        const start_date = new Date(cron.start_date);
                        let diffTime,
                            days_active
                        if (start_date > now) {
                            diffTime = Math.abs(start_date - now);
                            days_active = 0
                        } else {
                            diffTime = Math.abs(now - start_date);
                            days_active = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
                        }
                        let this_surveys = cron.surveys
                        //console.log('this_surveys', this_surveys)
                        let survey_cnt = cron.surveys_cnt
                        let this_questions = cron.questions
                        let questions_cnt = cron.questions_cnt
                        let cat_bgcolor = cat_colors[cron.cat]
                        let cat_color = lightOrDark(cat_bgcolor) ? 'black' : 'white';
                        console.log('cron2', cron)
                        cron_html += `
<div class="row">
  <div class="col-lg-12 col-sm-12">

    <div class="card m-b-30">
      <div class="card-body table-responsive">

        <div class="row">
          <div class="col-lg-2 col-md-4" style="margin-left: auto; margin-right: auto; text-align: center">
            <h5 class="font-weight-bold darkblue-h">${cron.title}</h5>
            <BR>
            <a href="/stats" class="button btn btn-primary btn-sm font-weight-b" style="background-color: ${cat_bgcolor} !important; border-color: ${cat_bgcolor} !important; color: ${cat_color}"><span class="mockup text-uppercase">${cron.cat_name}</span></a>
          </div>
          <div class="col-lg-2 col-md-4" style="text-align: center">
            <span style="font-size: 50px; font-weight: bold; color: #FE6E41">${questions_cnt}</span>
            <hr>
            <h5>Survey Questions</h5>
          </div>
          <div class="col-lg-2 col-md-4" style="text-align: center">
            <span style="font-size: 50px; font-weight: bold; color: #FE6E41">${cron.response_rate}</span>
            <hr>
            <h5>Response Rate</h5>
          </div>
          <div class="col-lg-2 col-md-6" style="text-align: center">
            <span style="font-size: 50px; font-weight: bold; color: #FE6E41">${days_active}</span>
            <hr>
            <h5>Days Active</h5>
          </div>
          <div class="col-lg-4 col-md-6" style="text-align: center; margin-top: auto; margin-bottom: auto;">
            <a href="/c/${this_surveys[0]}" class="button btn btn-primary btn-lg h62 mockup"
                    style="background-color: #15224F !important; border-color: #15224F !important; width: 100%"><span class="mockup">Edit Survey</span></a>
            <BR>
            <a href="/stats" class="button btn btn-primary btn-lg h62 mockup" style="width: 100%"><span class="mockup">View Analytics</span></a>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>
                        `
                        $('.surveys_lite').html(cron_html)
                    })
                }
            }
            if (resp.hasOwnProperty('depts')) {
                let all_depts = []
                let depts_html = ''
                let this_depts = resp.depts
                if (this_depts.length > 0) {
                    this_depts.forEach(dept => {
                        all_depts.push(dept)
                        depts_html += `<option value="${dept.slug}" class="dept_sel_item">${dept.name}</option>`
                    })
                }
                if (all_depts.length > 0) {
                    if (depts_html !== depts_html_cache) {
                        depts_html_cache = depts_html
                        $('#depts').html(depts_html)
                        $('#depts').selectpicker('refresh')
                    }
                    $('#depts_container').show()
                    $('#no_depts_container').hide()
                } else {
                    $('#depts_container').hide()
                    $('#no_depts_container').show()
                }
            }
            
            if (resp.hasOwnProperty('cats') && resp.cats.length > 0) { // TODO: Refactor select creations to function.
                let cats_html = ''
                resp.cats.forEach(cat => {
                    console.log("CAT", cat)
                    cats_html += `<option value="${cat.id}" class="cat_sel_item">${cat.cat_name}</option>`
                })
                if (cats_html !== cats_html_cache) {
                    cats_html_cache = cats_html
                    $('#cats').html(cats_html)
                    $('#cats').selectpicker('refresh')
                }
                $('#no_cats_container').hide()
                $('#cats_container').show()
            } else {
                $('#cats_container').hide()
                $('#no_cats_container').show()
            }
            
            if (has_updated === undefined || !has_updated) {
                console.log("Init questions", resp.questions)
                
                
                // FIXME: Tag inputs which should horiz scroll need: flex-wrap: nowrap;
                
                
                let questionsIn = document.querySelector('#questions_dropdown');
                questions_tagify = new Tagify(questionsIn, {
                    tagTextProp: 'name', // very important since a custom template is used with this property as text
                    enforceWhitelist: true,
                    skipInvalid: true, // do not remporarily add invalid tags
                    whitelist: resp.questions,
                    dropdown: {
                        closeOnSelect: false,
                        enabled: 0,
                        classname: 'questions',
                        searchKeys: ['name', 'qnum', 'qnum_txt']  // very important to set by which keys to search for suggesttions when typing
                    },
                    templates: {
                        //tag: tagTemplate,
                        //dropdownItem: suggestionItemTemplate
                        dropdownItem: function (tagData) {
                            try {
                                return `<div class='tagify__dropdown__item ${tagData.class ? tagData.class : ""}' tagifySuggestionIdx="${tagData.tagifySuggestionIdx}">
                                                        <span>${tagData.name}</span>
                                                    </div>`
                            } catch (err) {
                            }
                        }
                    },
                    
                    /*placeholder: 'Saved questions',
                    tagTextProp: 'name', // very important since a custom template is used with this property as text
                    enforceWhitelist: true,
                    dropdown: {
                        position: "input",
                        enabled: 1, // always opens dropdown when input gets focus
                        whitelist: resp.questions,
                        closeOnSelect: true,
                        searchKeys: ['name']
                    }*/
                });
                questions_tagify.on('dropdown:show dropdown:updated', onDropdownShow)
                questions_tagify.on('dropdown:select', onSelectSuggestion)
                var addAllSuggestionsElm;
                
                function onDragEnd(elm) {
                    questions_tagify.updateValueByDOMTags()
                }
                
                function onDropdownShow(e) {
                    var dropdownContentElm = e.detail.tagify.DOM.dropdown.content;
                    
                    if (questions_tagify.suggestedListItems.length > 1) {
                        //addAllSuggestionsElm = getAddAllSuggestionsElm();
                        
                        // insert "addAllSuggestionsElm" as the first element in the suggestions list
                        //dropdownContentElm.insertBefore(addAllSuggestionsElm, dropdownContentElm.firstChild)
                    }
                }
                
                function onSelectSuggestion(e) {
                    if (e.detail.elm == addAllSuggestionsElm)
                        questions_tagify.dropdown.selectAll.call(questions_tagify);
                }
                
                function getAddAllSuggestionsElm() {
                    // suggestions items should be based on "dropdownItem" template
                    return questions_tagify.parseTemplate('dropdownItem', [{
                            class: "addAll",
                            name: "Add all",
                            question_id: questions_tagify.settings.whitelist.reduce(function (remainingSuggestions, item) {
                                return questions_tagify.isTagDuplicate(item.value) ? remainingSuggestions : remainingSuggestions + 1
                            }, 0) + " Questions"
                        }]
                    )
                }
                
                function tagTemplate(tagData) {
                    return `${tagData.name}`
                }
                
                function suggestionItemTemplate(tagData) {
                    return `${tagData.name}<BR>`
                }
                
                // using 3-party script "dragsort"
                // https://github.com/yairEO/dragsort
                let dragsort = new DragSort(questions_tagify.DOM.scope, {
                    selector: '.' + questions_tagify.settings.classNames.tag,
                    callbacks: {
                        dragEnd: onDragEnd
                    }
                })
                
                
            }
            
            if (has_updated === undefined) {
                setInterval(update_bank, 60000)
                has_updated = true
            }
            
            if(!resp.hasOwnProperty('questions') || resp.questions.length === 0) {
                $('.questions_container').hide()
                $('#no_questions_container').show()
            }else {
                $('.questions_container').show()
                $('#no_questions_container').hide()
            }
        })
    }
    
    $('#trash_btn').click(function () {
        $('#survey_title').val('')
        $('#end_date').val('')
        $('#cron-click').val('')
        $('#cron_schedule').val('')
        if (questions_tagify !== undefined)
            questions_tagify.removeAllTags()
    })
    
    $.fn.selectpicker.Constructor.BootstrapVersion = '4';
    $('#saved_surveys .selectpicker').selectpicker({
        actionsBox: false,
        liveSearch: true,
        liveSearchPlaceholder: 'Search',
        liveSearchStyle: 'contains',
        mobile: false,
        noneSelectedText: 'Select Survey(s)',
        noneResultsText: 'No survey matched {0}',
        selectAllText: 'All',
        // selectOnTab: true,
        showContent: false,
        showIcon: false,
        showSubtext: false,
        showTick: true,
        size: 'auto',
        styleBase: 'form-control',
        style: 'style form-control full-w full btn btn-lg button',
        title: 'Surveys',
        virtualScroll: 200,
        width: 'fit',
        /*sanitizeFn: function(e){
            console.log('Survey multi', e)
        }*/
    });
    $('#depts .selectpicker').selectpicker({
        noneSelectedText: 'Select Surveys',
        actionsBox: false,
        liveSearch: true,
        liveSearchPlaceholder: 'Search',
        liveSearchStyle: 'contains',
        mobile: false,
        noneResultsText: 'No department matched {0}',
        selectAllText: 'All',
        // selectOnTab: true,
        showContent: false,
        showIcon: false,
        showSubtext: false,
        showTick: true,
        size: 'fit',
        styleBase: 'form-control',
        style: 'style form-control full-w full btn btn-lg button',
        title: 'Departments',
        virtualScroll: 200,
        width: 'fit',
        /*sanitizeFn: function(e){
            console.log('Survey multi', e)
        }*/
    });
    $('#cats .selectpicker').selectpicker({
        noneSelectedText: 'Categories',
        actionsBox: false,
        liveSearch: false,
        liveSearchPlaceholder: 'Search',
        liveSearchStyle: 'contains',
        mobile: false,
        noneResultsText: 'No categories matched {0}',
        selectAllText: 'All',
        // selectOnTab: true,
        showContent: false,
        showIcon: false,
        showSubtext: false,
        showTick: true,
        size: 'fit',
        styleBase: 'form-control',
        style: 'style form-control full-w full btn btn-lg button ',
        title: 'Categories',
        virtualScroll: 200,
        width: 'fit',
        /*sanitizeFn: function(e){
            console.log('Survey multi', e)
        }*/
    });
    
    //let tagsEl = document.querySelector('.bank_tags');
    
    
})(window.jQuery)
